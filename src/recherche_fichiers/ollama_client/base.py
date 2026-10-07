"""Connecteur générique asynchrone pour la communication avec le serveur Ollama.

Fournit le client de base `OllamaClient`, les exceptions dédiées,
ainsi que la vérification de disponibilité du serveur (`is_server_running`).
"""

from __future__ import annotations

import logging
import os
from typing import Any
import httpx

# Configuration du logger
logger = logging.getLogger(__name__)

# Tentative de récupération des configurations globales si disponibles
try:
    from recherche_fichiers.config import OLLAMA_URL  # type: ignore
except (ImportError, AttributeError):
    OLLAMA_URL = None

# Défaut si aucune configuration n'est trouvée
DEFAULT_OLLAMA_HOST = (
    OLLAMA_URL
    or os.getenv("OLLAMA_HOST")
    or os.getenv("OLLAMA_URL")
    or "http://localhost:11434"
)
DEFAULT_TIMEOUT = 60.0


# =====================================================================
# Exceptions (Erreur étiqueter pour la gestion des erreurs)
# =====================================================================


class OllamaError(Exception):
    """Exception de base pour toutes les erreurs liées au client Ollama."""

    pass


class OllamaConnectionError(OllamaError):
    """Levée lorsque le serveur Ollama est inaccessible ou injoignable."""

    pass


class OllamaResponseError(OllamaError):
    """Levée lorsque le serveur Ollama retourne une erreur HTTP ou un JSON d'erreur."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Erreur Ollama HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class OllamaModelNotFoundError(OllamaError):
    """Levée lorsqu'un modèle demandé n'est pas disponible sur le serveur."""

    pass


# =====================================================================
# Client Asynchrone de Base
# =====================================================================


class OllamaClient:
    """Client asynchrone générique pour interagir avec l'API REST d'Ollama."""

    def __init__(
        self,
        host: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise le client Ollama.

        Args:
            host: URL de base du serveur Ollama (ex: 'http://localhost:11434').
                  Si non renseigné, utilise la valeur configurée dans `config.py`
                  ou la variable d'environnement OLLAMA_HOST / OLLAMA_URL.
            timeout: Délai d'attente maximal en secondes pour les requêtes.
        """
        raw_host = host or DEFAULT_OLLAMA_HOST
        self.host = raw_host.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retourne ou initialise l'instance httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.host,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def __aenter__(self) -> OllamaClient:
        """Entre dans le gestionnaire de contexte asynchrone."""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ferme la session HTTP à la sortie du contexte asynchrone."""
        await self.close()

    async def close(self) -> None:
        """Ferme la session httpx sous-jacente si elle est ouverte."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def is_server_running(self) -> bool:
        """Vérifie si le serveur Ollama est actif et répond aux requêtes.

        Returns:
            bool: True si le serveur répond avec un code HTTP 200, False sinon.
        """
        try:
            client = await self._get_client()
            response = await client.get("/")
            return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException, OSError):
            return False

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Exécute une requête GET asynchrone vers un endpoint d'Ollama.

        Args:
            endpoint: Chemin de l'endpoint (ex: '/api/tags').
            params: Paramètres d'URL optionnels.

        Returns:
            dict[str, Any]: Réponse JSON décodée.

        Raises:
            OllamaConnectionError: Si le serveur est injoignable.
            OllamaResponseError: Si l'API renvoie un code de statut HTTP >= 400.
        """
        endpoint = "/" + endpoint.lstrip("/")
        client = await self._get_client()
        try:
            response = await client.get(endpoint, params=params)
            if response.status_code >= 400:
                raise OllamaResponseError(response.status_code, response.text)
            return response.json()
        except httpx.RequestError as exc:
            raise OllamaConnectionError(
                f"Impossible de se connecter au serveur Ollama sur {self.host}: {exc}"
            ) from exc

    async def post(
        self, endpoint: str, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Exécute une requête POST asynchrone vers un endpoint d'Ollama.

        Args:
            endpoint: Chemin de l'endpoint (ex: '/api/embed', '/api/generate').
            json_data: Corps JSON de la requête.

        Returns:
            dict[str, Any]: Réponse JSON décodée.

        Raises:
            OllamaConnectionError: Si le serveur est injoignable.
            OllamaResponseError: Si l'API renvoie un code de statut HTTP >= 400.
        """
        endpoint = "/" + endpoint.lstrip("/")
        client = await self._get_client()
        try:
            response = await client.post(endpoint, json=json_data)
            if response.status_code >= 400:
                raise OllamaResponseError(response.status_code, response.text)
            return response.json()
        except httpx.RequestError as exc:
            raise OllamaConnectionError(
                f"Impossible de se connecter au serveur Ollama sur {self.host}: {exc}"
            ) from exc

    async def list_models(self) -> list[str]:
        """Récupère la liste des noms de modèles disponibles sur le serveur Ollama.

        Returns:
            list[str]: Liste des identifiants/noms des modèles installés.
        """
        data = await self.get("/api/tags")
        models = data.get("models", [])
        return [m.get("name", "") for m in models if "name" in m]

    async def has_model(self, model_name: str) -> bool:
        """Vérifie si un modèle particulier est présent sur le serveur.

        Args:
            model_name: Nom du modèle (ex: 'embeddinggemma' ou 'gemma4:12b').

        Returns:
            bool: True si le modèle (ou un alias correspondant) est installé.
        """
        models = await self.list_models()
        target = model_name.strip().lower()

        for m in models:
            m_lower = m.lower()
            # Match exact ou correspondance nom sans tag (ex: 'embeddinggemma' correspond à 'embeddinggemma:latest')
            if m_lower == target or m_lower.split(":")[0] == target:
                return True
        return False


# =====================================================================
# Fonction Utilitaire Standalone
# =====================================================================


async def is_server_running(host: str | None = None, timeout: float = 5.0) -> bool:
    """Vérifie de façon autonome si le serveur Ollama est opérationnel.

    Cette fonction est particulièrement utile pour les tests rapides
    (ex: `tests/test_ollama.py`) sans instancier manuellement un client.

    Args:
        host: URL optionnelle du serveur Ollama.
        timeout: Délai maximal d'attente en secondes.

    Returns:
        bool: True si le serveur répond avec succès, False sinon.
    """
    client = OllamaClient(host=host, timeout=timeout)
    try:
        return await client.is_server_running()
    finally:
        await client.close()
