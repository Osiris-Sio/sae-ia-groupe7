"""Module de génération d'embeddings vectoriels via Ollama.

Utilise principalement le modèle `embeddinggemma` via l'endpoint `/api/embed`.

Documentation de la dimension vectorielle :
-------------------------------------------
- Modèle de référence : `embeddinggemma`
- Dimension native des vecteurs : 768
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from recherche_fichiers.ollama_client.base import (
    DEFAULT_TIMEOUT,
    OllamaClient,
    OllamaError,
    OllamaResponseError,
)

logger = logging.getLogger(__name__)

# Tentative de récupération des configurations globales
try:
    from recherche_fichiers.config import EMBEDDING_MODEL  # type: ignore
except (ImportError, AttributeError):
    EMBEDDING_MODEL = None

# Constantes du modèle d'embedding
DEFAULT_EMBEDDING_MODEL = (
    EMBEDDING_MODEL or os.getenv("EMBEDDING_MODEL") or "embeddinggemma"
)

# Dimension native documentée et attendue pour EmbeddingGemma
DEFAULT_EMBEDDING_DIM = 768


# =====================================================================
# Exceptions (Erreur étiqueter pour la gestion des erreurs)
# =====================================================================


class EmbeddingError(OllamaError):
    """Levée lors d'un échec de calcul d'embeddings vectoriels."""

    pass


# =====================================================================
# Client (OllamaClient)
# =====================================================================


class EmbeddingClient(OllamaClient):
    """Client dédié à l'extraction d'embeddings vectoriels via Ollama."""

    def __init__(
        self,
        host: str | None = None,
        default_model: str = DEFAULT_EMBEDDING_MODEL,
        expected_dim: int = DEFAULT_EMBEDDING_DIM,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise le client d'embedding.

        Args:
            host: URL du serveur Ollama (facultatif).
            default_model: Modèle d'embedding par défaut ('embeddinggemma').
            expected_dim: Dimension attendue des vecteurs (768 par défaut).
            timeout: Délai d'expiration des requêtes HTTP en secondes.
        """
        super().__init__(host=host, timeout=timeout)
        self.default_model = default_model
        self.expected_dim = expected_dim

    def validate_embedding(
        self,
        embedding: Sequence[float],
        expected_dim: int | None = None,
    ) -> bool:
        """Valide la conformité et la dimension d'un vecteur d'embedding.

        Args:
            embedding: Le vecteur retourné par le modèle.
            expected_dim: La dimension attendue (self.expected_dim par défaut).

        Returns:
            bool: True si la dimension correspond et le vecteur n'est pas vide.

        Raises:
            EmbeddingError: Si le vecteur est vide ou si sa dimension est incorrecte.
        """
        target_dim = expected_dim or self.expected_dim
        if not embedding:
            raise EmbeddingError("Le vecteur d'embedding retourné est vide.")

        actual_dim = len(embedding)
        if actual_dim != target_dim:
            logger.warning(
                "Dimension de l'embedding inattendue : reçu %d, attendu %d",
                actual_dim,
                target_dim,
            )
        return True

    async def get_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
        truncate_dim: int | None = None,
    ) -> list[list[float]]:
        """Génère les embeddings pour une liste de textes en une seule requête `/api/embed`.

        Args:
            texts: Liste des chaînes de caractères à vectoriser.
            model: Nom du modèle d'embedding (ex: 'embeddinggemma').
            truncate_dim: Tronque optionnellement les vecteurs (ex: 512, 256 ou 128 avec MRL).

        Returns:
            list[list[float]]: Liste des vecteurs d'embeddings (flottants).

        Raises:
            EmbeddingError: Si la requête échoue ou si aucun embedding n'est retourné.
        """
        if not texts:
            return []

        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "input": texts,
        }

        try:
            # Appel officiel recommandé à l'endpoint /api/embed
            data = await self.post("/api/embed", json_data=payload)
            embeddings = data.get("embeddings")

            # Fallback rétrocompatible pour les serveurs Ollama plus anciens (< 0.1.44)
            if embeddings is None and "embedding" in data:
                embeddings = [data["embedding"]]

            if not embeddings or not isinstance(embeddings, list):
                raise EmbeddingError(
                    f"Réponse invalide du serveur Ollama pour /api/embed : {data}"
                )

            # Option de troncature MRL si spécifiée
            if truncate_dim is not None and truncate_dim > 0:
                embeddings = [vec[:truncate_dim] for vec in embeddings]

            # Validation du premier vecteur pour vérification de dimension
            if embeddings and len(embeddings) > 0:
                self.validate_embedding(
                    embeddings[0],
                    expected_dim=truncate_dim or self.expected_dim,
                )

            return embeddings

        except OllamaResponseError as err:
            # Si /api/embed renvoie 404 (version ancienne), tentons /api/embeddings un par un
            if err.status_code == 404:
                logger.info(
                    "Endpoint /api/embed non trouvé (404), tentative avec /api/embeddings."
                )
                return await self._fallback_legacy_embeddings(
                    texts, target_model, truncate_dim
                )
            raise EmbeddingError(
                f"Erreur API lors de la génération d'embeddings: {err}"
            ) from err
        except Exception as err:
            raise EmbeddingError(
                f"Échec de génération d'embeddings pour {len(texts)} texte(s): {err}"
            ) from err

    async def _fallback_legacy_embeddings(
        self,
        texts: list[str],
        model: str,
        truncate_dim: int | None = None,
    ) -> list[list[float]]:
        """Fallback sur l'ancien endpoint `/api/embeddings` pour compatibilité."""
        results: list[list[float]] = []
        for text in texts:
            payload = {"model": model, "prompt": text}
            data = await self.post("/api/embeddings", json_data=payload)
            vec = data.get("embedding", [])
            if not vec:
                raise EmbeddingError(
                    f"Embedding vide reçu via /api/embeddings pour le texte: {text[:30]}..."
                )
            if truncate_dim is not None and truncate_dim > 0:
                vec = vec[:truncate_dim]
            results.append(vec)
        return results

    async def get_embedding(
        self,
        text: str,
        model: str | None = None,
        truncate_dim: int | None = None,
    ) -> list[float]:
        """Génère l'embedding vectoriel d'un unique texte.

        Args:
            text: Le texte à vectoriser.
            model: Nom du modèle (défaut: 'embeddinggemma').
            truncate_dim: Dimension de troncature optionnelle.

        Returns:
            list[float]: Vecteur d'embedding (dimension 768 par défaut).
        """
        embeddings = await self.get_embeddings(
            texts=[text],
            model=model,
            truncate_dim=truncate_dim,
        )
        if not embeddings:
            raise EmbeddingError("Aucun embedding retourné pour le texte fourni.")
        return embeddings[0]

    # Alias standards pratiques pour pipelines RAG / vector stores
    async def embed_query(self, query: str) -> list[float]:
        """Génère l'embedding d'une requête de recherche utilisateur."""
        return await self.get_embedding(query)

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Génère les embeddings d'une collection de documents ou de chunks."""
        return await self.get_embeddings(documents)


# =====================================================================
# Fonctions Utilitaires Standalone
# =====================================================================


async def get_embedding(
    text: str,
    host: str | None = None,
    model: str = DEFAULT_EMBEDDING_MODEL,
    truncate_dim: int | None = None,
) -> list[float]:
    """Génère l'embedding d'un texte de manière autonome.

    Idéal pour des scripts ou des tests unitaires simples.
    """
    client = EmbeddingClient(host=host, default_model=model)
    try:
        return await client.get_embedding(text, model=model, truncate_dim=truncate_dim)
    finally:
        await client.close()


async def get_embeddings(
    texts: list[str],
    host: str | None = None,
    model: str = DEFAULT_EMBEDDING_MODEL,
    truncate_dim: int | None = None,
) -> list[list[float]]:
    """Génère les embeddings d'une liste de textes de manière autonome."""
    client = EmbeddingClient(host=host, default_model=model)
    try:
        return await client.get_embeddings(
            texts, model=model, truncate_dim=truncate_dim
        )
    finally:
        await client.close()
