"""Configuration centralisée de l'application de recherche sémantique.

Définit l'ensemble des constantes globales et paramètres par défaut
(serveur Ollama, modèles IA, stockage ChromaDB, chunking et seuils).
Ces paramètres peuvent être surchargés par des variables d'environnement.
"""

from __future__ import annotations

import os
from pathlib import Path

# =====================================================================
# Chemins du Projet
# =====================================================================

# Racine du dépôt (trois niveaux au-dessus de ce fichier)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Dossiers de données et de persistance
DATA_DIR = PROJECT_ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"

# Base vectorielle ChromaDB
CHROMA_PERSIST_PATH = str(DATA_DIR / "chroma")
CHROMA_COLLECTION_NAME = "documents"


# =====================================================================
# Serveur Ollama
# =====================================================================

# Adresse du serveur Ollama (localhost en développement, ou serveur distant)
OLLAMA_URL = (
    os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
)

# Timeout des requêtes HTTP vers Ollama (en secondes)
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))


# =====================================================================
# Modèles d'Intelligence Artificielle
# =====================================================================

# Modèle d'embedding vectoriel (Rôle principal : recherche sémantique)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
EMBEDDING_DIM = 768  # Dimension native d'EmbeddingGemma

# Modèle de langage (LLM)
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:12b")

# Modèle vision multimodal
VLM_MODEL = os.getenv("VLM_MODEL", "qwen3-vl")


# =====================================================================
# Paramètres de Recherche
# =====================================================================

# Nombre maximal de résultats retournés à l'utilisateur
TOP_K = int(os.getenv("TOP_K", "5"))

# Seuil de distance vectorielle pour filtrer les résultats non pertinents
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "1.2"))


# =====================================================================
# Paramètres de Découpage (Chunking) & Formats
# =====================================================================

# Taille maximale d'un chunk (en caractères)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))

# Chevauchement entre chunks consécutifs (en caractères)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Formats documentaires supportés
SUPPORTED_FORMATS = {".txt"}
