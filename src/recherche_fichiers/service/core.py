"""
service/core.py

Pipeline d'indexation et de recherche sémantique et lexicale

Ce module orchestre :
    - la lecture et le découpage (chunking) des fichiers          -> service/utils.py
    - la génération des embeddings via Ollama / EmbeddingGemma    -> ollama_client/embedding.py
    - le stockage vectoriel (ChromaDB) et lexical (BM25)          -> storage/base.py
"""

# --------------- #
# --- Modules --- #
# --------------- #

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys

# Permet la résolution des modules que le script soit lancé directement ou via le package
_src_dir = Path(__file__).resolve().parents[2]
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

logger = logging.getLogger(__name__)

from recherche_fichiers.service import utils
from recherche_fichiers.storage.base import VectorStore, LexicalStore
from recherche_fichiers.ollama_client import get_embedding

# -------------------------------------- #
# --- Constantes/ Variables globales --- #
# -------------------------------------- #

SUPPORTED_FORMATS = {".txt", ".md", ".pdf", ".docx", ".csv"}

_vector_store: VectorStore | None = None
_lexical_store: LexicalStore | None = None

# ----------------- #
# --- Fonctions --- #
# ----------------- #


def _get_vector_store() -> VectorStore:
    """Accès paresseux (lazy) à l'instance unique de VectorStore."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_lexical_store() -> LexicalStore:
    """Accès paresseux (lazy) à l'instance unique de LexicalStore."""
    global _lexical_store
    if _lexical_store is None:
        _lexical_store = LexicalStore()
    return _lexical_store


async def index_directory(path: str) -> int:
    """
    Indexe, de bout en bout, tous les fichiers pris en charge d'un répertoire (recherche récursive)
    lecture -> chunking -> embedding -> stockage VectorStore & LexicalStore.

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
        logger.warning("Aucun fichier compatible trouvé dans %s", path)
        return 0

    total_chunks = 0
    for file_path in files:
        total_chunks += await _index_file(file_path)

    logger.info(
        "Indexation terminée : %d chunk(s) ajouté(s) depuis %s", total_chunks, path
    )
    return total_chunks


async def _index_file(file_path: Path) -> int:
    """Indexe un unique fichier : lecture, chunking, embedding, stockage vectoriel et lexical."""

    try:
        content = utils.load_file_content(file_path)
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

    if ids:
        # Stockage dans le store vectoriel (ChromaDB)
        _get_vector_store().add_documents(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        # Stockage simultané dans le store lexical (BM25) avec les mêmes chunk_ids
        _get_lexical_store().add_documents(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    logger.info("Fichier indexé : %s (%d chunk(s))", file_path, len(ids))

    return len(ids)


async def search_mixed(query: str, mode: str = "hybrid", k: int = 5) -> list[dict]:
    """
    Recherche multi-mode : oriente vers le store lexical, le store vectoriel, ou combine les deux en mode hybride.

    Args:
        query: texte de la requête utilisateur.
        mode : mode de recherche parmi "vectorial", "lexical", "hybrid".
        k    : nombre de résultats à retourner (top-k).

    Returns:
        Liste de résultats (dicts avec 'content', 'source_path', 'chunk_index', 'score'), triés par pertinence.
    """
    if not query or not query.strip():
        return []

    mode = mode.lower()
    if mode not in {"vectorial", "lexical", "hybrid"}:
        raise ValueError(
            f"Mode de recherche inconnu : '{mode}'. Valeurs acceptées : 'vectorial', 'lexical', 'hybrid'."
        )

    # Mode 1 : Recherche vectorielle pure
    if mode == "vectorial":
        try:
            query_embedding = await get_embedding(query)
        except Exception as e:
            logger.error("Échec de l'embedding : %s", e)
            return []
        raw_results = _get_vector_store().search(embedding=query_embedding, k=k)
        return utils.format_search_results(raw_results)

    # Mode 2 : Recherche lexicale pure
    if mode == "lexical":
        raw_results = _get_lexical_store().search(query=query, k=k)
        return utils.format_search_results(raw_results)

    # Mode 3 : Recherche hybride (RRF - Reciprocal Rank Fusion)
    try:
        query_embedding = await get_embedding(query)
        vec_raw = _get_vector_store().search(embedding=query_embedding, k=k * 2)
    except Exception as e:
        logger.error("Échec de la partie vectorielle en mode hybride : %s", e)
        vec_raw = {}

    lex_raw = _get_lexical_store().search(query=query, k=k * 2)

    vec_results = utils.format_search_results(vec_raw)
    lex_results = utils.format_search_results(lex_raw)

    return _reciprocal_rank_fusion(vec_results, lex_results, k=k)


def _reciprocal_rank_fusion(
    vector_results: list[dict], lexical_results: list[dict], k: int = 5, rrf_k: int = 60
) -> list[dict]:
    """
    Combine et réordonne deux listes de résultats en utilisant l'algorithme Reciprocal Rank Fusion (RRF).
    Score RRF = sum(1 / (rrf_k + rank))
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}

    def _process_results(results_list: list[dict]):
        for rank, res in enumerate(results_list, start=1):
            key = (res.get("source_path"), res.get("chunk_index"))
            if key not in doc_map:
                doc_map[key] = res
            scores[key] = scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

    _process_results(vector_results)
    _process_results(lexical_results)

    sorted_keys = sorted(scores.keys(), key=lambda item: scores[item], reverse=True)

    fused_results = []
    for key in sorted_keys[:k]:
        item = doc_map[key].copy()
        item["score"] = scores[key]
        fused_results.append(item)

    return fused_results


###############################################################################################
### FONCTION OBSOLÈTE : A SUPPRIMER DÈS QUE TOUS LES APPELS ONT ÉTÉ NETTOYÉS DANS LE PROJET ###
###############################################################################################


async def search(query: str, k: int = 5) -> list[dict]:
    """
    Recherche sémantique par défaut (conserve la rétrocompatibilité).
    """

    import warnings

    warnings.warn(
        "La fonction 'search' est obsolète, utilisez 'search_mixed(query, mode='vectorial', k=k)' à la place.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await search_mixed(query=query, mode="vectorial", k=k)


###############################################################################################
### FONCTION OBSOLÈTE : A SUPPRIMER DÈS QUE TOUS LES APPELS ONT ÉTÉ NETTOYÉS DANS LE PROJET ###
###############################################################################################

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
        for mode in ["vectorial", "lexical", "hybrid"]:
            print(f"Recherche mode '{mode}' : '{query}'")
            results = await search_mixed(query, mode=mode, k=3)
            for i, result in enumerate(results, start=1):
                print(
                    f"  {i}. [{result['source_path']} - chunk {result['chunk_index']}] "
                    f"score={result['score']:.4f}"
                )
                print(f"     {result['content'][:100]}...")
            print()

    asyncio.run(_demo())
