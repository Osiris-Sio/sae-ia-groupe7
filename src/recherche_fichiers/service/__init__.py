"""
Package service : Orchestration de la recherche et de l'indexation sémantique et lexicale.
"""

from .core import index_directory, search_mixed, search
from .utils import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_text,
    format_search_results,
    list_files_by_format,
    load_file_content,
    make_document_id,
    read_csv_file,
    read_docx_file,
    read_pdf_file,
    read_text_file,
)

__all__ = [
    # Core
    "index_directory",
    "search_mixed",
    "search",  # Conservé pour la rétrocompatibilité
    # Utils
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "list_files_by_format",
    "read_text_file",
    "read_pdf_file",
    "read_docx_file",
    "read_csv_file",
    "load_file_content",
    "make_document_id",
    "chunk_text",
    "format_search_results",
]