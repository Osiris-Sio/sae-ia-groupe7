"""Package `ollama_client` : Couche d'interaction asynchrone avec le serveur Ollama.

Fournit :
- `OllamaClient` : client générique HTTP asynchrone et vérification de santé (`is_server_running`).
- `EmbeddingClient` : extraction de vecteurs sémantiques avec `embeddinggemma` (dimension 768).
- `LLMClient` : inférence et raisonnement avec `gemma4:12b`.
"""

from .base import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_TIMEOUT,
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    is_server_running,
)
from .embedding import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingClient,
    EmbeddingError,
    get_embedding,
    get_embeddings,
)
from .llm import (
    DEFAULT_LLM_MODEL,
    LLMClient,
    LLMError,
)

__all__ = [
    # Base
    "OllamaClient",
    "is_server_running",
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_TIMEOUT",
    "OllamaError",
    "OllamaConnectionError",
    "OllamaResponseError",
    "OllamaModelNotFoundError",
    # Embedding
    "EmbeddingClient",
    "EmbeddingError",
    "get_embedding",
    "get_embeddings",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_EMBEDDING_DIM",
    # LLM
    "LLMClient",
    "LLMError",
    "DEFAULT_LLM_MODEL",
]
