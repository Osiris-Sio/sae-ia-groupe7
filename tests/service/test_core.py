# --------------- #
# --- Modules --- #
# --------------- #

import sys
import tempfile
import unittest
from pathlib import Path

# Ajout du dossier 'src' au chemin de recherche Python pour permettre l'import du package du projet
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from unittest.mock import AsyncMock, MagicMock, patch
from recherche_fichiers.service import core
from recherche_fichiers.ollama_client import OllamaConnectionError

# ------------- #
# --- Tests --- #
# ------------- #


class TestCore(unittest.IsolatedAsyncioTestCase):
    """
    Tests d'intégration et unitaires du service principal (core.py) avec isolation des dépendances
    externes (Ollama, VectorStore & LexicalStore) à l'aide de mocks.
    """

    def setUp(self):
        """Réinitialise les singletons des stores et prépare un dossier temporaire avant chaque test."""
        core._vector_store = None
        core._lexical_store = None
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.demo_dir = Path(self.test_dir_obj.name)

    def tearDown(self):
        """Nettoie et supprime le répertoire temporaire après l'exécution de chaque test."""
        self.test_dir_obj.cleanup()

    async def test_index_directory_invalid_path(self):
        """Vérifie qu'une exception NotADirectoryError est bien levée si le dossier source n'existe pas."""
        with self.assertRaises(NotADirectoryError):
            await core.index_directory("chemin/inexistant/impossible")

    @patch("recherche_fichiers.service.core._index_file", new_callable=AsyncMock)
    @patch("recherche_fichiers.service.utils.list_files_by_format")
    async def test_index_directory_success(self, mock_list_files, mock_index_file):
        """Vérifie le parcours, le filtrage par format et le comptage cumulé des morceaux lors de l'indexation d'un dossier."""
        # Simulation de la découverte de deux fichiers valides
        file1 = self.demo_dir / "note1.txt"
        file2 = self.demo_dir / "note2.md"
        mock_list_files.return_value = [file1, file2]

        # Simulation du nombre de chunks renvoyés par fichier indexé (2 pour le premier, 3 pour le second)
        mock_index_file.side_effect = [2, 3]

        # Exécution de la fonction d'indexation du répertoire
        total_chunks = await core.index_directory(str(self.demo_dir))

        # Vérifications : le total doit être de 5 chunks et _index_file doit avoir été appelé 2 fois
        self.assertEqual(total_chunks, 5)
        self.assertEqual(mock_index_file.call_count, 2)

    @patch("recherche_fichiers.service.core._get_lexical_store")
    @patch("recherche_fichiers.service.core._get_vector_store")
    @patch("recherche_fichiers.service.core.get_embedding", new_callable=AsyncMock)
    @patch("recherche_fichiers.service.utils.load_file_content")
    async def test_index_file_success(
        self,
        mock_load,
        mock_get_embedding,
        mock_get_vector_store,
        mock_get_lexical_store,
    ):
        """
        Vérifie la chaîne complète d'indexation d'un fichier :
        Chargement multi-format -> Découpage -> Vectorisation -> Enregistrement dans les stores vectoriel et lexical.
        """
        file_path = self.demo_dir / "note.pdf"
        mock_load.return_value = "Ceci est un test de contenu PDF."
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Mocks des stores de stockage pour intercepter les appels d'écriture
        mock_vec_store = MagicMock()
        mock_get_vector_store.return_value = mock_vec_store

        mock_lex_store = MagicMock()
        mock_get_lexical_store.return_value = mock_lex_store

        # Lancement de l'indexation unitaire du fichier
        chunks_indexed = await core._index_file(file_path)

        # Vérification que le chunk unique a bien été vectorisé et enregistré dans les deux stores
        self.assertEqual(chunks_indexed, 1)
        mock_get_embedding.assert_awaited_once_with("Ceci est un test de contenu PDF.")
        mock_vec_store.add_documents.assert_called_once()
        mock_lex_store.add_documents.assert_called_once()

    @patch("recherche_fichiers.service.utils.load_file_content")
    async def test_index_file_read_error(self, mock_load):
        """Vérifie qu'une erreur de lecture de fichier (ex: corruption) est interceptée sans bloquer le processus."""
        file_path = self.demo_dir / "error.docx"
        mock_load.side_effect = Exception("Erreur d'accès fichier")

        chunks_indexed = await core._index_file(file_path)

        # Aucun chunk ne doit être indexé et la fonction doit renvoyer 0 proprement
        self.assertEqual(chunks_indexed, 0)

    @patch("recherche_fichiers.service.utils.load_file_content")
    async def test_index_file_empty_content(self, mock_load):
        """Vérifie qu'un fichier dont le contenu est vide ou constitué uniquement d'espaces/retours à la ligne est ignoré."""
        file_path = self.demo_dir / "empty.txt"
        mock_load.return_value = "   \n  "

        chunks_indexed = await core._index_file(file_path)

        # Le fichier vide ne génère aucun chunk
        self.assertEqual(chunks_indexed, 0)

    @patch("recherche_fichiers.service.core._get_lexical_store")
    @patch("recherche_fichiers.service.core._get_vector_store")
    @patch("recherche_fichiers.service.core.get_embedding", new_callable=AsyncMock)
    @patch("recherche_fichiers.service.utils.load_file_content")
    async def test_index_file_embedding_error(
        self,
        mock_load,
        mock_get_embedding,
        mock_get_vector_store,
        mock_get_lexical_store,
    ):
        """Vérifie qu'un échec d'embedding sur un chunk spécifique est géré (le chunk est ignoré mais l'indexation continue)."""
        file_path = self.demo_dir / "multi.csv"
        mock_load.return_value = "Ligne une\nLigne deux"

        # Simulation : échec sur le premier chunk (Ollama down), succès sur le second
        mock_get_embedding.side_effect = [
            Exception("Ollama indisponible"),
            [0.4, 0.5, 0.6],
        ]

        mock_vec_store = MagicMock()
        mock_get_vector_store.return_value = mock_vec_store
        mock_lex_store = MagicMock()
        mock_get_lexical_store.return_value = mock_lex_store

        # Forçage du découpage en 2 chunks distincts pour tester la tolérance aux pannes partielles
        with patch(
            "recherche_fichiers.service.utils.chunk_text",
            return_value=["Chunk 1", "Chunk 2"],
        ):
            chunks_indexed = await core._index_file(file_path)

        # Seul le second chunk a pu être indexé (1 succès sur 2)
        self.assertEqual(chunks_indexed, 1)
        mock_vec_store.add_documents.assert_called_once()
        mock_lex_store.add_documents.assert_called_once()

    async def test_search_mixed_invalid_mode(self):
        """Vérifie qu'une exception ValueError est levée si l'utilisateur spécifie un mode de recherche inconnu."""
        with self.assertRaises(ValueError):
            await core.search_mixed("test", mode="inconnu")

    async def test_search_mixed_empty_query(self):
        """Vérifie qu'une requête de recherche vide ou constituée d'espaces renvoie immédiatement une liste vide."""
        results = await core.search_mixed("")
        self.assertEqual(results, [])

    @patch("recherche_fichiers.service.core._get_vector_store")
    @patch("recherche_fichiers.service.core.get_embedding", new_callable=AsyncMock)
    async def test_search_mixed_vectorial(
        self, mock_get_embedding, mock_get_vector_store
    ):
        """Vérifie le bon fonctionnement de la recherche en mode vectoriel pur."""
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]
        mock_store = MagicMock()
        mock_store.search.return_value = {
            "documents": [["Résultat vectoriel"]],
            "metadatas": [[{"source_path": "data/demo/note.txt", "chunk_index": 0}]],
            "scores": [[0.05]],
        }
        mock_get_vector_store.return_value = mock_store

        results = await core.search_mixed("exercice", mode="vectorial", k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Résultat vectoriel")
        mock_get_embedding.assert_awaited_once_with("exercice")
        mock_store.search.assert_called_once_with(embedding=[0.1, 0.2, 0.3], k=1)

    async def test_search_mixed_propagates_ollama_error(self):
        """Les erreurs typées Ollama doivent rester visibles pour l'interface."""
        for mode in ("vectorial", "hybrid"):
            with patch.object(
                core,
                "get_embedding",
                new_callable=AsyncMock,
                side_effect=OllamaConnectionError("serveur indisponible"),
            ):
                with self.assertRaises(OllamaConnectionError):
                    await core.search_mixed("exercice", mode=mode)

    @patch("recherche_fichiers.service.core._get_lexical_store")
    async def test_search_mixed_lexical(self, mock_get_lexical_store):
        """Vérifie le bon fonctionnement de la recherche en mode lexical pur (BM25)."""
        mock_store = MagicMock()
        mock_store.search.return_value = {
            "documents": [["Résultat lexical"]],
            "metadatas": [[{"source_path": "data/demo/note.txt", "chunk_index": 1}]],
            "scores": [[1.5]],
        }
        mock_get_lexical_store.return_value = mock_store

        results = await core.search_mixed("exercice", mode="lexical", k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Résultat lexical")
        mock_store.search.assert_called_once_with(query="exercice", k=1)

    @patch("recherche_fichiers.service.core._get_lexical_store")
    @patch("recherche_fichiers.service.core._get_vector_store")
    @patch("recherche_fichiers.service.core.get_embedding", new_callable=AsyncMock)
    async def test_search_mixed_hybrid(
        self, mock_get_embedding, mock_get_vector_store, mock_get_lexical_store
    ):
        """Vérifie le mode hybride combinant sémantique et lexical via RRF."""
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        mock_vec_store = MagicMock()
        mock_vec_store.search.return_value = {
            "documents": [["Doc commun", "Doc vecteur"]],
            "metadatas": [
                [
                    {"source_path": "a.txt", "chunk_index": 0},
                    {"source_path": "b.txt", "chunk_index": 0},
                ]
            ],
            "scores": [[0.1, 0.2]],
        }
        mock_get_vector_store.return_value = mock_vec_store

        mock_lex_store = MagicMock()
        mock_lex_store.search.return_value = {
            "documents": [["Doc commun", "Doc lexical"]],
            "metadatas": [
                [
                    {"source_path": "a.txt", "chunk_index": 0},
                    {"source_path": "c.txt", "chunk_index": 0},
                ]
            ],
            "scores": [[1.0, 0.5]],
        }
        mock_get_lexical_store.return_value = mock_lex_store

        results = await core.search_mixed("test", mode="hybrid", k=2)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["source_path"], "a.txt")

    @patch("recherche_fichiers.service.core.search_mixed", new_callable=AsyncMock)
    async def test_deprecated_search_wrapper(self, mock_search_mixed):
        """Vérifie que l'ancienne fonction `search` émet un avertissement et redirige vers `search_mixed`."""
        mock_search_mixed.return_value = [{"content": "test"}]

        with self.assertWarns(DeprecationWarning):
            results = await core.search("requête", k=3)

        self.assertEqual(len(results), 1)
        mock_search_mixed.assert_awaited_once_with(
            query="requête", mode="vectorial", k=3
        )

    # -------------------------------------------------------------------------
    # Tests mis à jour pour la fonction `synthesize` (basée sur `summarize_documents`)
    # -------------------------------------------------------------------------

    @patch("recherche_fichiers.service.core.summarize_documents", new_callable=AsyncMock)
    async def test_synthesize_success(self, mock_summarize):
        """Vérifie le bon fonctionnement de la synthèse avec des chunks valides et un appel réussi au service de résumé."""
        mock_summarize.return_value = "Voici la synthèse basée sur les sources."
        chunks = [
            {
                "source_path": "data/demo/note.txt",
                "chunk_index": 0,
                "content": "Ceci est un contenu de test pour la synthèse.",
            }
        ]

        result = await core.synthesize("Quelle est la question ?", chunks)

        self.assertIn("synthèse", result)
        mock_summarize.assert_awaited_once()
        
        # Vérification que summarize_documents a bien reçu les bons arguments (contents et query)
        _, kwargs = mock_summarize.call_args
        self.assertEqual(kwargs.get("query"), "Quelle est la question ?")
        contents_passed = kwargs.get("contents", [])
        self.assertTrue(any("data/demo/note.txt" in c for c in contents_passed))
        self.assertTrue(any("Ceci est un contenu de test" in c for c in contents_passed))

    async def test_synthesize_empty_query(self):
        """Vérifie qu'une requête vide ou constituée d'espaces renvoie le message par défaut sans appeler le service LLM."""
        chunks = [{"source_path": "a.txt", "chunk_index": 0, "content": "test"}]
        
        result = await core.synthesize("   ", chunks)
        
        self.assertEqual(result, "Aucun contenu pertinent n'a été trouvé pour générer une synthèse.")

    async def test_synthesize_empty_chunks(self):
        """Vérifie qu'une liste de chunks vide renvoie le message par défaut sans appeler le service LLM."""
        result = await core.synthesize("Quelle est la question ?", [])
        
        self.assertEqual(result, "Aucun contenu pertinent n'a été trouvé pour générer une synthèse.")

    @patch("recherche_fichiers.service.core.summarize_documents", new_callable=AsyncMock)
    async def test_synthesize_generation_error(self, mock_summarize):
        """Vérifie la gestion des erreurs en cas d'échec du service de résumé (ex: Ollama indisponible)."""
        mock_summarize.side_effect = Exception("Ollama hors ligne")
        chunks = [{"source_path": "a.txt", "chunk_index": 0, "content": "test"}]

        result = await core.synthesize("Quelle est la question ?", chunks)

        self.assertIn("Erreur lors de la génération de la synthèse", result)
        self.assertIn("Ollama hors ligne", result)


if __name__ == "__main__":
    unittest.main()