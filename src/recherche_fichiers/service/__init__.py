"""
Package service : Orchestration de la recherche et de l'indexation sémantique.
"""

from service.core import index_directory, search
from service.utils import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_text,
    format_search_results,
    list_files_by_format,
    make_document_id,
    read_text_file,
)

__all__ = [
    # Core
    "index_directory",
    "search",
    # Utils
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "list_files_by_format",
    "read_text_file",
    "make_document_id",
    "chunk_text",
    "format_search_results",
]