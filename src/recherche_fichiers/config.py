"""Configuration centralisée de l'application de recherche sémantique.

Définit l'ensemble des paramètres globaux et valeurs par défaut
(serveur Ollama, modèles IA, stockage ChromaDB, chunking et seuils)
via `pydantic-settings`. Ces paramètres peuvent être surchargés par des
variables d'environnement ou un fichier `.env`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du dépôt (trois niveaux au-dessus de ce fichier : dossier_test/)
_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _DEFAULT_PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Paramètres de configuration chargés depuis l'environnement / `.env`."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # =====================================================================
    # Chemins du Projet & Stockage
    # =====================================================================
    project_root: Path | None = Field(default=_DEFAULT_PROJECT_ROOT)
    data_dir: Path | None = Field(default=None)
    demo_dir: Path | None = Field(default=None)
    chroma_persist_path: str | None = Field(default=None)
    chroma_collection_name: str = Field(default="documents", min_length=1)

    # =====================================================================
    # Serveur Ollama
    # =====================================================================
    ollama_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_URL", "OLLAMA_HOST"),
    )
    ollama_embedding_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OLLAMA_EMBEDDING_URL", "EMBEDDING_URL"),
    )
    ollama_llm_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OLLAMA_LLM_URL", "LLM_URL"),
    )
    ollama_timeout: float = Field(default=300.0, gt=0)

    # =====================================================================
    # Modèles d'Intelligence Artificielle
    # =====================================================================
    embedding_model: str = Field(default="embeddinggemma", min_length=1)
    embedding_dim: int = Field(default=768, gt=0)
    llm_model: str = Field(default="gemma2:2b", min_length=1)
    vlm_model: str = Field(default="qwen3-vl", min_length=1)

    # =====================================================================
    # Paramètres de Recherche
    # =====================================================================
    top_k: int = Field(default=5, ge=1)
    similarity_threshold: float = Field(default=1.2)

    # =====================================================================
    # Paramètres de Découpage (Chunking) & Formats
    # =====================================================================
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)
    supported_formats: set[str] = Field(default_factory=lambda: {".txt"})

    @field_validator("supported_formats", mode="before")
    @classmethod
    def _parse_supported_formats(cls, value: Any) -> Any:
        """Permet de renseigner `SUPPORTED_FORMATS` en JSON ou en liste séparée par virgules."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if not stripped.startswith("["):
                items = [item.strip() for item in stripped.split(",") if item.strip()]
                return {item if item.startswith(".") else f".{item}" for item in items}
        return value

    @model_validator(mode="before")
    @classmethod
    def _empty_env_strings_to_none(cls, data: Any) -> Any:
        """Évite qu'une variable d'environnement vide (`""`) écrase un défaut."""
        if isinstance(data, dict):
            return {
                k: (None if isinstance(v, str) and v.strip() == "" else v)
                for k, v in data.items()
            }
        return data

    @model_validator(mode="after")
    def _populate_derived_paths_and_validate(self) -> Settings:
        """Calcule les chemins par défaut et vérifie la cohérence des paramètres."""
        if self.project_root is None:
            self.project_root = _DEFAULT_PROJECT_ROOT
        else:
            self.project_root = Path(self.project_root).expanduser().resolve()

        resolved_data_dir = (
            Path(self.data_dir).expanduser()
            if self.data_dir is not None
            else self.project_root / "data"
        )
        self.data_dir = resolved_data_dir

        if self.demo_dir is None:
            self.demo_dir = resolved_data_dir / "demo"
        else:
            self.demo_dir = Path(self.demo_dir).expanduser()

        if self.chroma_persist_path is None:
            self.chroma_persist_path = str(resolved_data_dir / "chroma")

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) doit être strictement inférieur "
                f"à chunk_size ({self.chunk_size})."
            )

        return self


settings = Settings()
