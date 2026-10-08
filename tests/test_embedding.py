import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Importation du package src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recherche_fichiers.ollama_client.base import OllamaResponseError
from recherche_fichiers.ollama_client.embedding import (
    EmbeddingClient,
    EmbeddingError,
    get_embedding,
    get_embeddings,
)


class EmbeddingClientTests(unittest.IsolatedAsyncioTestCase):
    """
    Tests unitaires du client d'embeddings Ollama.

    Les réponses du serveur sont simulées, aucun modèle n'est chargé.
    """

    def setUp(self) -> None:
        self.client = EmbeddingClient(
            default_model="modele-test",
            expected_dim=3,
        )

    async def test_get_embeddings_sends_payload_and_returns_vectors(self) -> None:
        """
        Vérifie l'appel au nouvel endpoint /api/embed
        avec le modèle par défaut.
        """

        expected = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"embeddings": expected},
        ) as post:
            result = await self.client.get_embeddings(["texte 1", "texte 2"])

        self.assertEqual(result, expected)
        post.assert_awaited_once_with(
            "/api/embed",
            json_data={
                "model": "modele-test",
                "input": ["texte 1", "texte 2"],
            },
        )

    async def test_get_embeddings_uses_custom_model_and_truncates_vectors(
        self,
    ) -> None:
        """
        Vérifie qu'un modèle peut être remplacé et que les
        vecteurs sont tronqués à la dimension demandée.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"embeddings": [[0.1, 0.2, 0.3, 0.4]]},
        ) as post:
            result = await self.client.get_embeddings(
                ["texte"],
                model="autre-modele",
                truncate_dim=2,
            )

        self.assertEqual(result, [[0.1, 0.2]])
        post.assert_awaited_once_with(
            "/api/embed",
            json_data={
                "model": "autre-modele",
                "input": ["texte"],
            },
        )

    async def test_get_embeddings_returns_empty_list_without_request(self) -> None:
        """
        Vérifie qu'une liste de textes vide ne déclenche
        aucune requête au serveur.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
        ) as post:
            result = await self.client.get_embeddings([])

        self.assertEqual(result, [])
        post.assert_not_awaited()

    async def test_get_embeddings_accepts_legacy_single_embedding_response(
        self,
    ) -> None:
        """
        Vérifie la compatibilité avec l'ancien format de réponse
        qui utilise la clé embedding au singulier.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"embedding": [0.1, 0.2, 0.3]},
        ):
            result = await self.client.get_embeddings(["texte"])

        self.assertEqual(result, [[0.1, 0.2, 0.3]])

    async def test_get_embeddings_uses_legacy_endpoint_after_404(self) -> None:
        """
        Vérifie le repli vers /api/embeddings lorsque l'ancien
        serveur ne connaît pas /api/embed.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            side_effect=[
                OllamaResponseError(404, "not found"),
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ],
        ) as post:
            result = await self.client.get_embeddings(["un", "deux"])

        self.assertEqual(
            result,
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        )
        self.assertEqual(
            [call.args[0] for call in post.await_args_list],
            ["/api/embed", "/api/embeddings", "/api/embeddings"],
        )

    async def test_get_embeddings_wraps_non_404_api_error(self) -> None:
        """
        Vérifie qu'une erreur HTTP autre que 404 est convertie
        en EmbeddingError sans activer le fallback.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            side_effect=OllamaResponseError(500, "erreur serveur"),
        ) as post:
            with self.assertRaisesRegex(EmbeddingError, "Erreur API"):
                await self.client.get_embeddings(["texte"])

        post.assert_awaited_once()

    async def test_legacy_fallback_rejects_empty_embedding(self) -> None:
        """
        Vérifie qu'un vecteur vide reçu de l'ancien endpoint
        est signalé comme une erreur.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            side_effect=[
                OllamaResponseError(404, "not found"),
                {"embedding": []},
            ],
        ):
            with self.assertRaisesRegex(EmbeddingError, "Embedding vide"):
                await self.client.get_embeddings(["texte"])

    async def test_get_embeddings_rejects_invalid_response(self) -> None:
        """
        Vérifie qu'une réponse sans vecteur est signalée
        comme une erreur d'embedding.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"unexpected": []},
        ):
            with self.assertRaisesRegex(EmbeddingError, "Réponse invalide"):
                await self.client.get_embeddings(["texte"])

    def test_validate_embedding_rejects_empty_vector(self) -> None:
        """
        Vérifie qu'un vecteur vide est refusé.
        """

        with self.assertRaisesRegex(EmbeddingError, "vide"):
            self.client.validate_embedding([])

    def test_validate_embedding_warns_but_accepts_other_dimension(self) -> None:
        """
        Vérifie qu'une dimension inattendue génère un avertissement,
        sans rejeter le vecteur.
        """

        with self.assertLogs(
            "recherche_fichiers.ollama_client.embedding",
            level="WARNING",
        ):
            result = self.client.validate_embedding([0.1, 0.2])

        self.assertTrue(result)

    async def test_get_embedding_returns_single_vector(self) -> None:
        """
        Vérifie que get_embedding() retourne le vecteur unique.
        """

        with patch.object(
            self.client,
            "get_embeddings",
            new_callable=AsyncMock,
            return_value=[[0.1, 0.2]],
        ) as get_embeddings_mock:
            result = await self.client.get_embedding(
                "texte",
                model="modele-personnalise",
                truncate_dim=2,
            )

        self.assertEqual(result, [0.1, 0.2])
        get_embeddings_mock.assert_awaited_once_with(
            texts=["texte"],
            model="modele-personnalise",
            truncate_dim=2,
        )

    async def test_get_embedding_raises_when_no_embeddings_returned(self) -> None:
        """
        Vérifie que get_embedding lève une EmbeddingError si
        get_embeddings ne retourne aucun vecteur.
        """

        with patch.object(
            self.client,
            "get_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with self.assertRaisesRegex(EmbeddingError, "Aucun embedding retourné"):
                await self.client.get_embedding("texte")

    async def test_embed_query_and_documents_delegate_to_embedding_methods(
        self,
    ) -> None:
        """
        Vérifie que les alias de pipeline (embed_query et embed_documents)
        délèguent aux méthodes de génération d'embeddings correspondantes.
        """

        with (
            patch.object(
                self.client,
                "get_embedding",
                new_callable=AsyncMock,
                return_value=[0.1, 0.2, 0.3],
            ) as get_embedding_mock,
            patch.object(
                self.client,
                "get_embeddings",
                new_callable=AsyncMock,
                return_value=[[0.4, 0.5, 0.6]],
            ) as get_embeddings_mock,
        ):
            query_result = await self.client.embed_query("question")
            document_result = await self.client.embed_documents(["document"])

        self.assertEqual(query_result, [0.1, 0.2, 0.3])
        self.assertEqual(document_result, [[0.4, 0.5, 0.6]])
        get_embedding_mock.assert_awaited_once_with("question")
        get_embeddings_mock.assert_awaited_once_with(["document"])

    async def test_standalone_embedding_functions_close_the_client(self) -> None:
        """
        Vérifie que les fonctions utilitaires créent puis ferment
        leur client même après le calcul des embeddings.
        """

        single_client = Mock()
        single_client.get_embedding = AsyncMock(return_value=[0.1])
        single_client.close = AsyncMock()

        multiple_client = Mock()
        multiple_client.get_embeddings = AsyncMock(return_value=[[0.2]])
        multiple_client.close = AsyncMock()

        with patch(
            "recherche_fichiers.ollama_client.embedding.EmbeddingClient",
            side_effect=[single_client, multiple_client],
        ) as client_factory:
            single = await get_embedding(
                "texte",
                host="http://ollama",
                model="modele",
            )
            multiple = await get_embeddings(
                ["texte"],
                host="http://ollama",
                model="modele",
            )

        self.assertEqual(single, [0.1])
        self.assertEqual(multiple, [[0.2]])
        self.assertEqual(client_factory.call_count, 2)
        single_client.close.assert_awaited_once()
        multiple_client.close.assert_awaited_once()


# Lancement des tests
if __name__ == "__main__":
    unittest.main()
