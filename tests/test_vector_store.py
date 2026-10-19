import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


# Permet d'importer le package situé dans le dossier src/
# lorsque les tests sont lancés depuis la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recherche_fichiers.storage.base import VectorStore


class VectorStoreTests(unittest.TestCase):
    """
    Tests unitaires de la classe VectorStore.

    Les tests utilisent des mocks afin de tester VectorStore
    sans réellement utiliser ChromaDB.
    """

    def setUp(self) -> None:
        # Création d'un faux objet collection ChromaDB.
        # Il permet de vérifier les appels effectués par VectorStore.
        self.collection = Mock()

        # Création d'un faux client ChromaDB.
        self.client = Mock()

        # Lorsque get_or_create_collection() est appelé,
        # il retournera notre fausse collection.
        self.client.get_or_create_collection.return_value = self.collection

        # Remplacement temporaire de chromadb.PersistentClient
        # par notre faux client.
        self.client_factory = patch(
            "recherche_fichiers.storage.base.chromadb.PersistentClient",
            return_value=self.client,
        )

        # Activation du mock.
        self.persistent_client = self.client_factory.start()

        # Restauration automatique du vrai PersistentClient
        # à la fin de chaque test.
        self.addCleanup(self.client_factory.stop)

        # Création du VectorStore qui utilisera notre faux client.
        self.store = VectorStore()

    def test_initializes_persistent_client_and_collection(self) -> None:
        """
        Vérifie que VectorStore initialise correctement
        le client ChromaDB et la collection par défaut.
        """

        # Vérifie que PersistentClient est appelé avec
        # le chemin de stockage par défaut.
        self.persistent_client.assert_called_once_with(
            path="data/chroma"
        )

        # Vérifie que la collection "documents" est créée ou récupérée.
        self.client.get_or_create_collection.assert_called_once_with(
            name="documents"
        )

        # Vérifie que VectorStore utilise bien la collection créée.
        self.assertIs(self.store.collection, self.collection)

    def test_initializes_with_custom_path_and_collection(self) -> None:
        """
        Vérifie qu'il est possible de personnaliser
        le chemin de stockage et le nom de la collection.
        """

        VectorStore(
            persist_path="custom/path",
            collection_name="custom"
        )

        # Vérifie que le chemin personnalisé est utilisé.
        self.persistent_client.assert_called_with(
            path="custom/path"
        )

        # Vérifie que le nom de collection personnalisé est utilisé.
        self.client.get_or_create_collection.assert_called_with(
            name="custom"
        )

    def test_add_documents_passes_data_and_metadata_to_collection(self) -> None:
        """
        Vérifie que add_documents() transmet correctement
        les IDs, documents, embeddings et métadonnées
        à la collection ChromaDB.
        """

        ids = ["doc-1", "doc-2"]
        documents = ["first", "second"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"source": "a"}, {"source": "b"}]

        # Appel de la méthode à tester.
        self.store.add_documents(
            ids,
            documents,
            embeddings,
            metadatas
        )

        # Vérifie que collection.add() reçoit exactement
        # les données fournies.
        self.collection.add.assert_called_once_with(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def test_add_documents_passes_none_when_metadata_is_omitted(self) -> None:
        """
        Vérifie que les métadonnées sont optionnelles.
        """

        self.store.add_documents(
            ["doc-1"],
            ["text"],
            [[0.1]]
        )

        # Lorsque les métadonnées ne sont pas fournies,
        # None doit être transmis à ChromaDB.
        self.collection.add.assert_called_once_with(
            ids=["doc-1"],
            documents=["text"],
            embeddings=[[0.1]],
            metadatas=None,
        )

    def test_add_documents_does_nothing_when_ids_are_empty(self) -> None:
        """
        Vérifie qu'aucun document n'est ajouté lorsque
        la liste des IDs est vide.
        """

        self.store.add_documents(
            [],
            ["unused"],
            [],
            [{"unused": True}]
        )

        # ChromaDB ne doit pas être appelé.
        self.collection.add.assert_not_called()

    def test_add_documents_rejects_different_data_lengths(self) -> None:
        """
        Vérifie que la méthode refuse des listes
        de tailles différentes entre IDs, documents et embeddings.
        """

        with self.assertRaisesRegex(
            ValueError,
            "ids, documents et embeddings"
        ):
            self.store.add_documents(
                ["doc-1"],
                [],
                [[0.1]]
            )

        # Comme les données sont invalides,
        # aucun ajout ne doit être effectué.
        self.collection.add.assert_not_called()

    def test_add_documents_rejects_different_metadata_length(self) -> None:
        """
        Vérifie que le nombre de métadonnées correspond
        au nombre de documents.
        """

        with self.assertRaisesRegex(
            ValueError,
            "metadatas"
        ):
            self.store.add_documents(
                ["doc-1", "doc-2"],
                ["first", "second"],
                [[0.1], [0.2]],
                [{"source": "a"}],
            )

        # ChromaDB ne doit pas être appelé si les métadonnées
        # ne correspondent pas au nombre de documents.
        self.collection.add.assert_not_called()

    def test_search_uses_query_embedding_and_returns_collection_result(
        self
    ) -> None:
        """
        Vérifie que search() utilise correctement l'embedding
        de la requête et retourne le résultat de ChromaDB.
        """

        # Résultat simulé que ChromaDB doit retourner.
        expected = {"documents": [["result"]]}

        self.collection.query.return_value = expected

        # Recherche avec un embedding.
        result = self.store.search(
            query_embedding=[0.1, 0.2],
            k=3
        )

        # Vérifie que le résultat de ChromaDB est bien retourné.
        self.assertIs(result, expected)

        # Vérifie que query() est appelé avec le bon embedding
        # et le nombre de résultats demandé.
        self.collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2]],
            n_results=3,
        )

    def test_search_accepts_embedding_alias(self) -> None:
        """
        Vérifie que le paramètre embedding peut également
        être utilisé pour effectuer une recherche.
        """

        self.store.search(
            embedding=[0.4, 0.5]
        )

        # Vérifie que l'embedding est bien transmis à ChromaDB.
        # k vaut 5 par défaut.
        self.collection.query.assert_called_once_with(
            query_embeddings=[[0.4, 0.5]],
            n_results=5,
        )

    def test_search_prefers_query_embedding_when_both_are_provided(
        self
    ) -> None:
        """
        Vérifie que query_embedding est prioritaire
        lorsque query_embedding et embedding sont fournis.
        """

        self.store.search(
            query_embedding=[0.1],
            embedding=[0.9]
        )

        # L'embedding [0.1] doit être utilisé,
        # et non [0.9].
        self.collection.query.assert_called_once_with(
            query_embeddings=[[0.1]],
            n_results=5,
        )

    def test_search_requires_an_embedding(self) -> None:
        """
        Vérifie qu'une erreur est générée lorsqu'aucun
        embedding n'est fourni pour effectuer une recherche.
        """

        with self.assertRaisesRegex(
            ValueError,
            "embedding doit être fourni"
        ):
            self.store.search()

        # Aucune requête ne doit être envoyée à ChromaDB.
        self.collection.query.assert_not_called()

    def test_search_rejects_non_positive_result_count(self) -> None:
        """
        Vérifie que le nombre de résultats demandé (k)
        doit être strictement supérieur à 0.
        """

        # Teste plusieurs valeurs invalides.
        for count in (0, -1):

            # subTest permet d'identifier quelle valeur
            # a provoqué un éventuel échec.
            with self.subTest(count=count):

                with self.assertRaisesRegex(
                    ValueError,
                    "k doit être supérieur"
                ):
                    self.store.search(
                        query_embedding=[0.1],
                        k=count
                    )

        # Aucune recherche ne doit être effectuée
        # avec un nombre de résultats invalide.
        self.collection.query.assert_not_called()


# Lancement des tests
if __name__ == "__main__":
    unittest.main()