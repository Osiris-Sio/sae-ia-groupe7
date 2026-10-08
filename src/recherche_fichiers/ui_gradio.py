import sys
from pathlib import Path

# Permet la résolution des modules que le script soit lancé directement ou via -m
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import gradio as gr

try:
    from recherche_fichiers.service.core import search
except ImportError:
    from service.core import search

try:
    from recherche_fichiers.config import TOP_K
except (ImportError, AttributeError):
    try:
        from config import TOP_K
    except (ImportError, AttributeError):
        TOP_K = 5


async def rechercher(query: str):
    """
    Lance une recherche sémantique et retourne
    les résultats bruts.
    """
    return await search(query, k=TOP_K)


interface = gr.Interface(
    fn=rechercher,
    inputs=gr.Textbox(
        label="Votre recherche",
        placeholder="Entrez votre recherche..."
    ),
    outputs=gr.JSON(
        label="Résultats"
    ),
    title="Recherche de fichiers",
)


if __name__ == "__main__":
    interface.launch(debug=True)