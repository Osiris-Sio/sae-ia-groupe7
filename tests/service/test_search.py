"""
tests/service/test_search.py

Tests de validation pour la recherche lexicale, vectorielle et hybride.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Ajout du dossier 'src' au chemin de recherche Python
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from recherche_fichiers.service import core
from recherche_fichiers.storage.base import LexicalStore, VectorStore


class SearchIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """
    Tests de recherche couvrant le store lexical, le store vectoriel et la fusion hybride.
    """

    def setUp(self):
        """Initialise un environnement temporaire avec des stores dédiés."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_lexical.db"
        self.chroma_path = str(Path(self.temp_dir.name) / "chroma")

        self.lexical_store = LexicalStore(persist_path=str(self.db_path))
        self.vector_store = VectorStore(
            persist_path=self.chroma_path, collection_name="test_col"
        )

        # Remplacement des stores globaux par les stores de test
        core._lexical_store = self.lexical_store
        core._vector_store = self.vector_store

    def tearDown(self):
        """Nettoie les ressources et bases temporaires."""
        self.lexical_store.close()
        core._lexical_store = None
        core._vector_store = None
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_lexical_search_returns_coherent_results(self):
        """
        LexicalStore.search() retourne des résultats cohérents
        sur une requête test avec le classement BM25.
        """
        ids = ["doc_1", "doc_2", "doc_3"]
        docs = [
            "Le tri à bulles est un algorithme de tri simple.",
            "La récursion est une méthode fondamentale en informatique.",
            "Le tri par fusion utilise le principe diviser pour régner.",
        ]
        metadatas = [
            {"source_path": "tri.txt", "chunk_index": 0},
            {"source_path": "recursion.txt", "chunk_index": 0},
            {"source_path": "fusion.txt", "chunk_index": 0},
        ]

        self.lexical_store.add_documents(ids=ids, documents=docs, metadatas=metadatas)

        # Recherche du mot exact "algorithme"
        results = self.lexical_store.search("algorithme", k=2)

        self.assertEqual(len(results["ids"][0]), 1)
        self.assertEqual(results["ids"][0][0], "doc_1")
        self.assertIn("tri à bulles", results["documents"][0][0])

    async def test_chunk_id_identical_between_sqlite_and_chromadb(self):
        """
        Vérifie que le chunk_id est rigoureusement identique
        entre ChromaDB et SQLite lors de l'indexation.
        """
        file_path = Path(self.temp_dir.name) / "test_doc.txt"
        file_path.write_text(
            "Premier paragraphe.\nDeuxième paragraphe.", encoding="utf-8"
        )

        fake_embedding = [0.1] * 768
        with patch(
            "recherche_fichiers.service.core.get_embedding",
            new_callable=AsyncMock,
            return_value=fake_embedding,
        ):
            nb_chunks = await core._index_file(file_path)

        self.assertGreater(nb_chunks, 0)

        # Vérification des IDs enregistrés dans SQLite
        sqlite_rows = self.lexical_store.connection.execute(
            "SELECT id FROM documents ORDER BY id"
        ).fetchall()
        sqlite_ids = [r[0] for r in sqlite_rows]

        # Vérification des IDs enregistrés dans ChromaDB
        chroma_res = self.vector_store.collection.get()
        chroma_ids = sorted(chroma_res["ids"])

        self.assertEqual(sqlite_ids, chroma_ids)
        self.assertIn("test_doc_txt", sqlite_ids[0])
        self.assertTrue(sqlite_ids[0].endswith("_0"))

    async def test_search_mixed_three_modes(self):
        """
        Les 3 modes de search_mixed() (vectorial, lexical, hybrid)
        fonctionnent et sont testés.
        """
        ids = ["c_0", "c_1"]
        docs = [
            "Introduction aux réseaux informatiques et routage IP.",
            "Gestion des bases de données relationnelles SQL.",
        ]
        metadatas = [
            {"source_path": "reseau.txt", "chunk_index": 0},
            {"source_path": "bdd.txt", "chunk_index": 0},
        ]
        embeddings = [[0.1] * 768, [0.9] * 768]

        self.vector_store.add_documents(
            ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas
        )
        self.lexical_store.add_documents(ids=ids, documents=docs, metadatas=metadatas)

        fake_query_embedding = [0.1] * 768

        # 1. Mode vectoriel pur
        with patch(
            "recherche_fichiers.service.core.get_embedding",
            new_callable=AsyncMock,
            return_value=fake_query_embedding,
        ):
            vec_res = await core.search_mixed("réseaux", mode="vectorial", k=2)
        self.assertGreaterEqual(len(vec_res), 1)

        # 2. Mode lexical pur
        lex_res = await core.search_mixed("SQL", mode="lexical", k=2)
        self.assertEqual(len(lex_res), 1)
        self.assertIn("SQL", lex_res[0]["content"])

        # 3. Mode hybride
        with patch(
            "recherche_fichiers.service.core.get_embedding",
            new_callable=AsyncMock,
            return_value=fake_query_embedding,
        ):
            hybrid_res = await core.search_mixed("réseaux", mode="hybrid", k=2)
        self.assertGreaterEqual(len(hybrid_res), 1)


if __name__ == "__main__":
    unittest.main()
