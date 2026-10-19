import sys
import unittest
from pathlib import Path

# Permet d'importer le package situé dans le dossier src/
# lorsque les tests sont lancés depuis la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recherche_fichiers.storage.base import LexicalStore


class LexicalStoreTests(unittest.TestCase):
    """
    Tests unitaires de la classe LexicalStore.

    Les tests utilisent une base SQLite en mémoire afin
    de tester réellement SQLite et FTS5 sans créer de fichier.
    """

    def setUp(self) -> None:
        # Création d'une base SQLite temporaire en mémoire.
        self.store = LexicalStore(persist_path=":memory:")

    def tearDown(self) -> None:
        # Ferme la connexion SQLite après chaque test.
        self.store.close()

    def test_initializes_database_and_tables(self) -> None:
        """
        Vérifie que les tables documents et chunks_fts
        sont correctement créées.
        """

        tables = self.store.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE name IN ('documents', 'chunks_fts')
            ORDER BY name
            """
        ).fetchall()

        self.assertEqual(
            [row[0] for row in tables],
            ["chunks_fts", "documents"],
        )

    def test_add_documents_stores_documents(self) -> None:
        """
        Vérifie que les documents sont correctement
        enregistrés dans SQLite.
        """

        self.store.add_documents(
            ids=["doc-1", "doc-2"],
            documents=[
                "Les examens ont lieu en juin.",
                "Les absences doivent être justifiées.",
            ],
        )

        rows = self.store.connection.execute(
            "SELECT id, content FROM documents ORDER BY id"
        ).fetchall()

        self.assertEqual(
            rows,
            [
                ("doc-1", "Les examens ont lieu en juin."),
                ("doc-2", "Les absences doivent être justifiées."),
            ],
        )

    def test_add_documents_stores_metadata(self) -> None:
        """
        Vérifie que les métadonnées sont correctement
        enregistrées dans SQLite.
        """

        metadatas = [
            {
                "document_id": "doc-1",
                "source_path": "data/demo/examens.txt",
                "format": "txt",
                "chunk_index": 0,
            }
        ]

        self.store.add_documents(
            ids=["doc-1"],
            documents=["Les examens ont lieu en juin."],
            metadatas=metadatas,
        )

        result = self.store.search("examens")

        self.assertEqual(
            result["metadatas"][0][0],
            metadatas[0],
        )

    def test_add_documents_accepts_no_metadata(self) -> None:
        """
        Vérifie que les métadonnées sont facultatives.
        """

        self.store.add_documents(
            ids=["doc-1"],
            documents=["Les examens ont lieu en juin."],
        )

        row = self.store.connection.execute(
            "SELECT metadata FROM documents WHERE id = ?",
            ("doc-1",),
        ).fetchone()

        self.assertIsNone(row[0])

    def test_add_documents_does_nothing_when_ids_are_empty(self) -> None:
        """
        Vérifie qu'aucun document n'est ajouté lorsque
        la liste des IDs est vide.
        """

        self.store.add_documents(
            ids=[],
            documents=[],
        )

        count = self.store.connection.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_add_documents_rejects_different_data_lengths(self) -> None:
        """
        Vérifie que la méthode refuse des listes
        de tailles différentes entre IDs et documents.
        """

        with self.assertRaisesRegex(
            ValueError,
            "ids et documents doivent avoir la même longueur",
        ):
            self.store.add_documents(
                ids=["doc-1"],
                documents=[],
            )

    def test_add_documents_rejects_different_metadata_length(self) -> None:
        """
        Vérifie que le nombre de métadonnées correspond
        au nombre de documents.
        """

        with self.assertRaisesRegex(
            ValueError,
            "metadatas doit avoir la même longueur que ids",
        ):
            self.store.add_documents(
                ids=["doc-1", "doc-2"],
                documents=["first", "second"],
                metadatas=[{"source": "a"}],
            )

    def test_search_returns_matching_documents(self) -> None:
        """
        Vérifie que la recherche FTS5 retrouve les documents
        contenant le terme recherché.
        """

        self.store.add_documents(
            ids=["doc-1", "doc-2"],
            documents=[
                "Les examens ont lieu en juin.",
                "Les absences doivent être justifiées.",
            ],
        )

        result = self.store.search("examens")

        self.assertEqual(
            result["ids"][0],
            ["doc-1"],
        )

        self.assertEqual(
            result["documents"][0],
            ["Les examens ont lieu en juin."],
        )

    def test_search_returns_scores(self) -> None:
        """
        Vérifie que la recherche retourne un score BM25.
        """

        self.store.add_documents(
            ids=["doc-1"],
            documents=["Les examens ont lieu en juin."],
        )

        result = self.store.search("examens")

        self.assertEqual(len(result["scores"][0]), 1)
        self.assertIsInstance(result["scores"][0][0], float)

    def test_search_rejects_non_positive_result_count(self) -> None:
        """
        Vérifie que le nombre de résultats demandé (k)
        doit être strictement supérieur à 0.
        """

        for count in (0, -1):
            with self.subTest(count=count):
                with self.assertRaisesRegex(
                    ValueError,
                    "k doit être supérieur",
                ):
                    self.store.search(
                        query="examens",
                        k=count,
                    )

    def test_close_closes_connection(self) -> None:
        """
        Vérifie que la connexion SQLite peut être fermée.
        """

        self.store.close()

        with self.assertRaisesRegex(
            Exception,
            "closed",
        ):
            self.store.connection.execute(
                "SELECT 1"
            )


if __name__ == "__main__":
    unittest.main()