"""
service/core.py

Pipeline d'indexation et de recherche sémantique

Ce module orchestre :
    - la lecture et le découpage (chunking) des fichiers          -> service/utils.py
    - la génération des embeddings via Ollama / EmbeddingGemma    -> ollama_client/embedding.py
    - le stockage et la recherche vectorielle via ChromaDB        -> storage/base.py
"""

# --------------- #
# --- Modules --- #
# --------------- #

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from recherche_fichiers.service import utils
from recherche_fichiers.storage.base import VectorStore
from recherche_fichiers.ollama_client import get_embedding

# -------------------------------------- #
# --- Constantes/ Variables globales --- #
# -------------------------------------- #

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".txt"}

_store: VectorStore | None = None

# ----------------- #
# --- Fonctions --- #
# ----------------- #


def _get_store() -> VectorStore:
    """Accès paresseux (lazy) à l'instance unique de VectorStore."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


async def index_directory(path: str) -> int:
    """
    Indexe, de bout en bout, tous les fichiers .txt d'un répertoire (recherche récursive)
    lecture -> chunking -> embedding -> stockage ChromaDB.

    Args:
        path: chemin du répertoire à indexer.

    Returns:
        Le nombre total de chunks indexés.

    Raises:
        NotADirectoryError: si `path` n'est pas un répertoire existant.
    """
    directory = Path(path)
    if not directory.is_dir():
        raise NotADirectoryError(f"Le chemin '{path}' n'est pas un répertoire valide.")

    files = utils.list_files_by_format(directory, SUPPORTED_FORMATS)
    if not files:
        logger.warning("Aucun fichier .txt trouvé dans %s", path)
        return 0

    total_chunks = 0
    for file_path in files:
        total_chunks += await _index_file(file_path)

    logger.info(
        "Indexation terminée : %d chunk(s) ajouté(s) depuis %s", total_chunks, path
    )
    return total_chunks


async def _index_file(file_path: Path) -> int:
    """Indexe un unique fichier .txt : lecture, chunking, embedding, stockage."""

    try:
        content = utils.read_text_file(file_path)
    except Exception as e:
        logger.error("Impossible de lire le fichier %s: %s", file_path, e)
        return 0

    if not content.strip():
        logger.warning("Fichier vide ignoré : %s", file_path)
        return 0

    document_id = utils.make_document_id(file_path)
    chunks = utils.chunk_text(content)

    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk_index, chunk_content in enumerate(chunks):

        # Récupération du vecteur d'embedding
        try:
            embedding_vector = await get_embedding(chunk_content)
        except Exception as e:
            logger.error("Échec de l'embedding pour le chunk: %s", e)
            continue  # Passer au chunk suivant sans faire planter l'application

        # Création d'un identifiant unique pour le chunk
        chunk_id = f"{document_id}_{chunk_index}"

        ids.append(chunk_id)
        embeddings.append(embedding_vector)
        documents.append(chunk_content)
        metadatas.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source_path": str(file_path),
                "format": file_path.suffix.lstrip("."),
                "chunk_index": chunk_index,
            }
        )

    _get_store().add_documents(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info("Fichier indexé : %s (%d chunk(s))", file_path, len(chunks))

    return len(chunks)


async def search(query: str, k: int = 5) -> list[dict]:
    """
    Recherche sémantique : vectorise la requête puis interroge ChromaDB pour retourner les k chunks les plus pertinents.

    Args:
        query: texte de la requête utilisateur.
        k    : nombre de résultats à retourner (top-k).

    Returns:
        Liste de résultats (dicts avec 'content', 'source_path', 'chunk_index', 'score'), triés par pertinence décroissante.
    """
    if not query or not query.strip():
        return []

    # Récupération du vecteur d'embedding
    try:
        query_embedding = await get_embedding(query)
    except Exception as e:
        logger.error("Échec de l'embedding : %s", e)
        return []

    raw_results = _get_store().search(query_embedding=query_embedding, k=k)

    return utils.format_search_results(raw_results)


# ------------ #
# --- Main --- #
# ------------ #

if __name__ == "__main__":

    # Démonstration de bout en bout, sans création de fichier de test dédié. Usage : python core.py [chemin_du_dossier]
    import sys

    logging.basicConfig(level=logging.INFO)
    demo_path = sys.argv[1] if len(sys.argv) > 1 else "data/demo"

    async def _demo() -> None:
        print(f"Indexation de : {demo_path}")
        nb_chunks = await index_directory(demo_path)
        print(f"-> {nb_chunks} chunk(s) indexé(s).\n")

        query = "exercice"
        print(f"Recherche : '{query}'")
        results = await search(query, k=5)
        for i, result in enumerate(results, start=1):
            print(
                f"{i}. [{result['source_path']} - chunk {result['chunk_index']}] "
                f"score={result['score']:.4f}"
            )
            print(f"   {result['content'][:150]}...")

    asyncio.run(_demo())
