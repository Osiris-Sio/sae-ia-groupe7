import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Importation du package src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from recherche_fichiers.ollama_client.base import (
    OllamaClient,
    OllamaConnectionError,
    OllamaResponseError,
    is_server_running,
)


class OllamaClientTests(unittest.IsolatedAsyncioTestCase):
    """
    Tests unitaires du client Ollama de base.

    Les requêtes HTTP sont simulées afin de ne pas dépendre
    d'un serveur Ollama réellement démarré.
    """

    def setUp(self) -> None:
        # Le client simulé permet de vérifier les requêtes HTTP envoyées.
        self.http_client = Mock()
        self.http_client.get = AsyncMock()
        self.http_client.post = AsyncMock()
        self.http_client.aclose = AsyncMock()
        self.http_client.is_closed = False

        self.client = OllamaClient(
            host="http://localhost:11434/",
            timeout=12,
        )
        self.client._client = self.http_client

    def test_initializes_with_normalized_host_and_timeout(self) -> None:
        """
        Vérifie que l'URL de base est normalisée et que
        le délai d'attente personnalisé est conservé.
        """
        self.assertEqual(self.client.host, "http://localhost:11434")
        self.assertEqual(self.client.timeout, 12)

    async def test_get_client_creates_http_client_when_missing(self) -> None:
        """
        Vérifie que le client HTTP est créé à la première requête
        avec l'hôte et le délai d'attente configurés.
        """

        # Crée un nouveau client avec un hôte et un délai d'attente différents
        new_client = OllamaClient(
            host="http://ollama:11434",
            timeout=7,
        )
        http_client = Mock()

        # Patch la création du client HTTP et vérifie qu'elle est correctement configurée.
        with patch(
            "recherche_fichiers.ollama_client.base.httpx.AsyncClient",
            return_value=http_client,
        ) as client_factory:
            result = await new_client._get_client()

        # Vérifie que le client HTTP est créé correctement.
        self.assertIs(result, http_client)
        client_factory.assert_called_once()
        self.assertEqual(
            client_factory.call_args.kwargs["base_url"],
            "http://ollama:11434",
        )

        # Vérifie que le délai d'attente est correctement configuré.
        self.assertEqual(
            client_factory.call_args.kwargs["timeout"].read,
            7,
        )

    async def test_get_client_recreates_closed_http_client(self) -> None:
        """
        Vérifie qu'une session HTTP fermée est remplacée
        par une nouvelle instance.
        """
        # Crée un nouveau client avec une session HTTP fermée.
        new_client = OllamaClient()
        new_client._client = Mock(is_closed=True)
        replacement = Mock()

        # Patch la création du client HTTP et vérifie qu'elle est correctement configurée.
        with patch(
            "recherche_fichiers.ollama_client.base.httpx.AsyncClient",
            return_value=replacement,
        ) as client_factory:
            result = await new_client._get_client()

        # Vérifie que le client HTTP est recrée.
        self.assertIs(result, replacement)
        client_factory.assert_called_once()

    async def test_get_normalizes_endpoint_and_returns_json(self) -> None:
        """
        Vérifie que GET normalise le chemin de l'endpoint
        et retourne le JSON reçu.
        """
        # Crée une réponse mockée.
        response = Mock(status_code=200)
        response.json.return_value = {"models": []}
        self.http_client.get.return_value = response

        # Test la méthode GET avec un endpoint et des paramètres custom.
        result = await self.client.get(
            "api/tags",
            params={"format": "json"},
        )

        # Vérifie que GET normalise le chemin de l'endpoint.
        self.assertEqual(result, {"models": []})
        self.http_client.get.assert_awaited_once_with(
            "/api/tags",
            params={"format": "json"},
        )

    async def test_post_sends_json_and_returns_json(self) -> None:
        """
        Vérifie que POST transmet le corps JSON et retourne
        la réponse décodée.
        """
        # Crée une réponse mockée.
        response = Mock(status_code=200)
        response.json.return_value = {"response": "ok"}
        self.http_client.post.return_value = response

        # Test la méthode POST avec un endpoint et un corps JSON custom.
        result = await self.client.post(
            "/api/generate",
            json_data={"prompt": "bonjour"},
        )

        # Vérifie que POST transmet le corps JSON et retourne la réponse décodée.
        self.assertEqual(result, {"response": "ok"})
        self.http_client.post.assert_awaited_once_with(
            "/api/generate",
            json={"prompt": "bonjour"},
        )

    async def test_http_error_raises_response_error(self) -> None:
        """
        Vérifie qu'une réponse HTTP en erreur est convertie
        en exception dédiée contenant le statut et le message.
        """
        # Crée une réponse mockée en erreur.
        response = Mock(status_code=404, text="endpoint absent")
        self.http_client.get.return_value = response

        # Test qu'une réponse HTTP en erreur est convertie en OllamaResponseError.
        with self.assertRaises(OllamaResponseError) as context:
            await self.client.get("/api/tags")

        # Vérifie que l'exception contient le statut et le message.
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, "endpoint absent")

    async def test_request_error_raises_connection_error(self) -> None:
        """
        Vérifie qu'une erreur réseau est convertie en
        OllamaConnectionError.
        """
        self.http_client.post.side_effect = httpx.ConnectError("offline")
        # Vérifie que l'exception est de type OllamaConnectionError.
        with self.assertRaises(OllamaConnectionError):
            await self.client.post("/api/generate")

    async def test_get_request_error_raises_connection_error(self) -> None:
        """
        Vérifie que les erreurs réseau d'une requête GET
        sont converties en OllamaConnectionError.
        """
        self.http_client.get.side_effect = httpx.ConnectError("offline")

        # Vérifie que l'exception est de type OllamaConnectionError.
        with self.assertRaises(OllamaConnectionError):
            await self.client.get("/api/tags")

    async def test_is_server_running_checks_http_status(self) -> None:
        """
        Vérifie que la disponibilité du serveur dépend
        d'une réponse HTTP 200.
        """
        self.http_client.get.return_value = Mock(status_code=200)
        self.assertTrue(await self.client.is_server_running())
        self.http_client.get.assert_awaited_once_with("/")

        # Test que la disponibilité du serveur dépend d'une réponse HTTP 503.
        self.http_client.get.reset_mock()
        self.http_client.get.return_value = Mock(status_code=503)
        self.assertFalse(await self.client.is_server_running())

    async def test_is_server_running_returns_false_on_network_error(self) -> None:
        """
        Vérifie qu'une erreur réseau indique que le serveur
        n'est pas disponible, sans la propager.
        """
        self.http_client.get.side_effect = httpx.ConnectError("offline")

        # Vérifie que le serveur n'est pas disponible.
        self.assertFalse(await self.client.is_server_running())

    async def test_close_closes_an_open_http_client(self) -> None:
        """
        Vérifie que close() ferme la session HTTP active
        puis libère sa référence.
        """
        self.http_client.is_closed = False

        # Libère la session HTTP
        await self.client.close()

        # Vérifie que close() ferme la session HTTP active.
        self.http_client.aclose.assert_awaited_once()
        self.assertIsNone(self.client._client)

    async def test_list_models_returns_model_names(self) -> None:
        """
        Vérifie que list_models() extrait les noms de modèles
        présents dans la réponse de l'API.
        """
        with patch.object(
            self.client,
            "get",
            new_callable=AsyncMock,
            return_value={
                "models": [
                    {"name": "embeddinggemma:latest"},
                    {"name": "gemma4:12b"},
                    {"digest": "sans-nom"},
                ]
            },
        ) as get:
            models = await self.client.list_models()

        # Vérifie que list_models() retourne les noms de modèles.
        self.assertEqual(models, ["embeddinggemma:latest", "gemma4:12b"])
        get.assert_awaited_once_with("/api/tags")

    async def test_has_model_accepts_name_without_tag(self) -> None:
        """
        Vérifie qu'un modèle est reconnu avec ou sans son tag.
        """
        with patch.object(
            self.client,
            "list_models",
            new_callable=AsyncMock,
            return_value=["EmbeddingGemma:latest", "gemma4:12b"],
        ):
            self.assertTrue(await self.client.has_model(" embeddinggemma "))
            self.assertTrue(await self.client.has_model("GEMMA4:12b"))
            self.assertFalse(await self.client.has_model("llama3"))

    async def test_async_context_manager_closes_http_client(self) -> None:
        """
        Vérifie que la sortie d'un gestionnaire de contexte
        ferme la session HTTP.
        """

        self.http_client.is_closed = False
        with patch.object(self.client, "_get_client", new_callable=AsyncMock):
            async with self.client:
                pass

        self.http_client.aclose.assert_awaited_once()

    async def test_standalone_health_check_closes_client(self) -> None:
        """
        Vérifie que la fonction utilitaire ferme le client
        après avoir contrôlé l'état du serveur.
        """

        client = Mock()
        client.is_server_running = AsyncMock(return_value=True)
        client.close = AsyncMock()

        with patch(
            "recherche_fichiers.ollama_client.base.OllamaClient",
            return_value=client,
        ) as client_factory:
            result = await is_server_running(
                host="http://ollama:11434",
                timeout=3,
            )

        self.assertTrue(result)
        client_factory.assert_called_once_with(
            host="http://ollama:11434",
            timeout=3,
        )
        client.close.assert_awaited_once()


# Lancement des tests
if __name__ == "__main__":
    unittest.main()
