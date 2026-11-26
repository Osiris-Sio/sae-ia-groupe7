from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3

import chromadb

try:
    from recherche_fichiers.config import settings
except ImportError:
    settings = None  # type: ignore[assignment]


def _default_lexical_persist_path() -> str:
    """Calcule le chemin par défaut de la base SQLite FTS5 à partir de `settings`."""
    if settings is not None and settings.data_dir is not None:
        return str(Path(settings.data_dir) / "lexical.db")
    return "data/lexical.db"


def _default_chroma_persist_path() -> str:
    """Calcule le chemin par défaut de ChromaDB à partir de `settings`."""
    if settings is not None and settings.chroma_persist_path:
        return settings.chroma_persist_path
    if settings is not None and settings.data_dir is not None:
        return str(Path(settings.data_dir) / "chroma")
    return "data/chroma"


def _default_chroma_collection_name() -> str:
    """Retourne le nom de collection ChromaDB par défaut depuis `settings`."""
    if settings is not None and settings.chroma_collection_name:
        return settings.chroma_collection_name
    return "documents"


def _default_top_k() -> int:
    """Retourne le `top_k` par défaut depuis `settings`."""
    if settings is not None and settings.top_k:
        return settings.top_k
    return 5


class LexicalStore:
    """
    Gère le stockage et la recherche lexicale des chunks avec SQLite FTS5.
    """

    def __init__(self, persist_path: str | Path | None = None):
        resolved_path = (
            _default_lexical_persist_path()
            if persist_path is None
            else str(persist_path)
        )

        # Crée le dossier de la base si nécessaire.
        if resolved_path != ":memory:":
            Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)

        # Ouvre la base SQLite.
        self.connection = sqlite3.connect(resolved_path)

        # Crée la table qui conserve le texte et les métadonnées des chunks.
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT
            )
            """)

        # Crée l'index lexical FTS5 utilisé pour la recherche.
        self.connection.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(id UNINDEXED, content)
            """)

        # Enregistre la création des tables.
        self.connection.commit()

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Ajoute les chunks et leurs métadonnées dans SQLite."""

        # Arrête la fonction si aucun chunk n'est fourni.
        if not ids:
            return

        # Vérifie que les listes ont la même longueur.
        if len(ids) != len(documents):
            raise ValueError("ids et documents doivent avoir la même longueur.")

        # Vérifie qu'il y a une métadonnée par chunk.
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError("metadatas doit avoir la même longueur que ids.")

        # Convertit les métadonnées en JSON pour les enregistrer dans SQLite.
        metadata_values = (
            [json.dumps(metadata) for metadata in metadatas]
            if metadatas is not None
            else [None] * len(ids)
        )

        # Ajoute les chunks à la table et à l'index lexical.
        with self.connection:
            self.connection.executemany(
                "INSERT INTO documents (id, content, metadata) VALUES (?, ?, ?)",
                zip(ids, documents, metadata_values),
            )
            self.connection.executemany(
                "INSERT INTO chunks_fts (id, content) VALUES (?, ?)",
                zip(ids, documents),
            )

    def search(self, query: str, k: int | None = None) -> dict:
        """Recherche les k chunks les mieux classés par BM25."""
        resolved_k = _default_top_k() if k is None else k

        # Vérifie que le nombre de résultats demandé est valide.
        if resolved_k <= 0:
            raise ValueError("k doit être supérieur à 0.")

        # Nettoyage des mots pour éviter les erreurs de syntaxe SQLite FTS5
        # (ex: ponctuation isolée comme '?', parenthèses, guillemets).
        tokens = re.findall(r"\w+", query)
        if not tokens:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "scores": [[]],
            }

        # Encadrement de chaque token pour forcer une recherche de termes littéraux sécurisée.
        safe_query = " ".join(f'"{token}"' for token in tokens)

        try:
            # Recherche les chunks correspondants et les classe avec BM25.
            rows = self.connection.execute(
                """
                SELECT chunks_fts.id, chunks_fts.content, documents.metadata,
                       bm25(chunks_fts) AS score
                FROM chunks_fts
                JOIN documents ON documents.id = chunks_fts.id
                WHERE chunks_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (safe_query, resolved_k),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []

        # Renvoie les résultats dans une structure similaire à VectorStore.
        return {
            "ids": [[row[0] for row in rows]],
            "documents": [[row[1] for row in rows]],
            "metadatas": [
                [json.loads(row[2]) if row[2] is not None else None for row in rows]
            ],
            "scores": [[row[3] for row in rows]],
        }

    def close(self) -> None:
        """Ferme la connexion SQLite."""
        self.connection.close()


class VectorStore:
    """
    Gère le stockage et la recherche des vecteurs avec ChromaDB.
    """

    def __init__(
        self,
        persist_path: str | Path | None = None,
        collection_name: str | None = None,
    ):
        resolved_path = (
            _default_chroma_persist_path()
            if persist_path is None
            else str(persist_path)
        )
        resolved_collection = (
            _default_chroma_collection_name()
            if collection_name is None
            else collection_name
        )

        # Initialise la base ChromaDB.
        self.client = chromadb.PersistentClient(path=resolved_path)

        # Récupère ou crée la collection.
        self.collection = self.client.get_or_create_collection(
            name=resolved_collection
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """
        Ajoute les chunks et leurs embeddings dans ChromaDB.
        """

        # Arrête la fonction si aucun chunk n'est fourni.
        if not ids:
            return

        # Vérifie que les listes ont la même longueur.
        if not (len(ids) == len(documents) == len(embeddings)):
            raise ValueError(
                "ids, documents et embeddings doivent avoir " "la même longueur."
            )

        # Vérifie qu'il y a une métadonnée par chunk.
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError("metadatas doit avoir la même longueur que ids.")

        # Ajoute les données dans ChromaDB.
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: list[float] | None = None,
        k: int | None = None,
        embedding: list[float] | None = None,
    ) -> dict:
        """
        Recherche les k chunks les plus proches.
        """
        target_embedding = query_embedding if query_embedding is not None else embedding
        if target_embedding is None:
            raise ValueError("Un vecteur d'embedding doit être fourni.")

        resolved_k = _default_top_k() if k is None else k
        if resolved_k <= 0:
            raise ValueError("k doit être supérieur à 0.")

        # Recherche les chunks les plus similaires.
        return self.collection.query(
            query_embeddings=[target_embedding],
            n_results=resolved_k,
        )