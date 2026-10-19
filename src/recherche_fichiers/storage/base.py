import json
import sqlite3
from pathlib import Path

import chromadb


class LexicalStore:
    """
    Gère le stockage et la recherche lexicale des chunks avec SQLite FTS5.
    """

    def __init__(self, persist_path: str = "data/lexical.db"):
        # Crée le dossier de la base si nécessaire.
        if persist_path != ":memory:":
            Path(persist_path).parent.mkdir(parents=True, exist_ok=True)

        # Ouvre la base SQLite.
        self.connection = sqlite3.connect(persist_path)

        # Crée la table qui conserve le texte et les métadonnées des chunks.
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT
            )
            """
        )

        # Crée l'index lexical FTS5 utilisé pour la recherche.
        self.connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(id UNINDEXED, content)
            """
        )

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
            raise ValueError(
                "ids et documents doivent avoir la même longueur."
            )

        # Vérifie qu'il y a une métadonnée par chunk.
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                "metadatas doit avoir la même longueur que ids."
            )

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

    def search(self, query: str, k: int = 5) -> dict:
        """Recherche les k chunks les mieux classés par BM25."""

        # Vérifie que le nombre de résultats demandé est valide.
        if k <= 0:
            raise ValueError("k doit être supérieur à 0.")

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
            (query, k),
        ).fetchall()

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
        persist_path: str = "data/chroma",
        collection_name: str = "documents",
    ):
        # Initialise la base ChromaDB.
        self.client = chromadb.PersistentClient(path=persist_path)

        # Récupère ou crée la collection.
        self.collection = self.client.get_or_create_collection(
            name=collection_name
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
        if not (
            len(ids)
            == len(documents)
            == len(embeddings)
        ):
            raise ValueError(
                "ids, documents et embeddings doivent avoir "
                "la même longueur."
            )

        # Vérifie qu'il y a une métadonnée par chunk.
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                "metadatas doit avoir la même longueur que ids."
            )

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
        k: int = 5,
        embedding: list[float] | None = None,
    ) -> dict:
        """
        Recherche les k chunks les plus proches.
        """
        target_embedding = query_embedding if query_embedding is not None else embedding
        if target_embedding is None:
            raise ValueError("Un vecteur d'embedding doit être fourni.")

        if k <= 0:
            raise ValueError("k doit être supérieur à 0.")

        # Recherche les chunks les plus similaires.
        return self.collection.query(
            query_embeddings=[target_embedding],
            n_results=k,
        )