"""
service/utils.py

Fonctions utilitaires pour le service d'indexation et de recherche :
    - Contrôle des fichiers
    - Lecture des fichiers
    - Découpage (chunking) du texte
    - Formatage des résultats de recherche
"""

# --------------- #
# --- Modules --- #
# --------------- #

from __future__ import annotations

import re
from pathlib import Path

# ------------------ #
# --- Constantes --- #
# ------------------ #

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50

# ----------------- #
# --- Fonctions --- #
# ----------------- #

def list_files_by_format(directory: Path, 
                         formats  : set[str]
                         ) -> list[Path]:
    """
    Liste (de manière récursive) les fichiers d'un répertoire dont l'extension (ex: ".txt") correspond à l'un des formats 
    spécifiés.

    Args:
        directory: répertoire racine dans lequel chercher les fichiers.
        formats  : ensemble d'extensions acceptées, avec le point (ex: ".txt").

    Returns:
        Liste triée des chemins de fichiers correspondants.
    """
    return sorted(
        p for p in directory.rglob("*")
        if  p.is_file() 
        and p.suffix.lower() in formats
    )


def read_text_file(file_path: Path) -> str:
    """
    Lit le contenu d'un fichier texte en UTF-8, en ignorant les octets invalides plutôt que de planter.
    """
    return file_path.read_text(encoding="utf-8", 
                               errors  ="ignore")


def make_document_id(file_path: Path) -> str:
    """
    Génère un `document_id` stable et sans caractères problématiques (utilisable comme préfixe d'identifiant ChromaDB) 
    à partir du chemin absolu du fichier.
    """
    return re.sub(r"[^a-zA-Z0-9_-]", 
                  "_", 
                  str(file_path.resolve()))


def chunk_text(text      : str, 
               chunk_size: int = CHUNK_SIZE, 
               overlap   : int = CHUNK_OVERLAP
               ) -> list[str]:
    """
    Découpe un texte en chunks de `chunk_size` caractères maximum, avec un chevauchement `overlap` entre chunks successifs. 
    Le point de coupe est recherché sur un saut de ligne ou une fin de phrase proche de la limite afin d'éviter de couper 
    un mot en deux.

    Args:
        text      : texte source à découper.
        chunk_size: taille maximale d'un chunk, en caractères.
        overlap   : chevauchement entre deux chunks consécutifs, en caractères.

    Returns:
        Liste ordonnée des chunks (chaînes non vides).
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start             = 0
    text_length       = len(text)

    while start < text_length:
        end = min(start + chunk_size, 
                  text_length)

        if end < text_length:
            boundary = text.rfind("\n", 
                                  start, 
                                  end)
            if boundary <= start:
                boundary = text.rfind(". ", 
                                      start, 
                                      end)
            if boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        next_start = end - overlap
        start      = next_start if next_start > start else end

    return chunks


def format_search_results(raw_results: dict) -> list[dict]:
    """
    Convertit le résultat brut retourné par `VectorStore.search()` en une liste de dicts directement exploitables par l'UI
    [{content, source_path, chunk_index, score}, ...].

    """
    # Fonction volontairement tolérante : si une clé attendue est absente, une liste vide est utilisée plutôt que de lever 
    # une exception.
    documents = (raw_results.get("documents") or [[]])[0]
    metadatas = (raw_results.get("metadatas") or [[]])[0]
    distances = (raw_results.get("distances") or [[]])[0]
    results   = []

    for content, metadata, distance in zip(documents, 
                                           metadatas,
                                           distances):
        metadata = metadata or {}
        results.append({
            "content"    : content,
            "source_path": metadata.get("source_path"),
            "chunk_index": metadata.get("chunk_index"),
            "score"      : distance,
        })
    return results