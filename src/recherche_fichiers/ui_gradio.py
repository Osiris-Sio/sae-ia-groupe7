import sys
from pathlib import Path

# Permet la résolution des modules que le script soit lancé directement ou via -m
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import gradio as gr

try:
    from recherche_fichiers.service.core import search_mixed
except ImportError:
    from service.core import search_mixed

try:
    from recherche_fichiers.config import TOP_K
except (ImportError, AttributeError):
    try:
        from config import TOP_K
    except (ImportError, AttributeError):
        TOP_K = 5

MODE_MAPPING = {
    "Hybride (recommandé)": "hybrid",
    "Vectoriel (Sémantique)": "vectorial",
    "Lexical (Mots-clés)": "lexical",
}


async def rechercher(query: str, mode_label: str):
    """
    Lance la recherche selon le mode sélectionné (Hybride, Vectoriel, Lexical)
    et retourne les résultats formatés.
    """
    mode = MODE_MAPPING.get(mode_label, "hybrid")
    return await search_mixed(query=query, mode=mode, k=TOP_K)


interface = gr.Interface(
    fn=rechercher,
    inputs=[
        gr.Textbox(
            label="Votre recherche",
            placeholder="Entrez vos mots-clés ou une question en langage naturel...",
            lines=2,
        ),
        gr.Radio(
            choices=[
                "Hybride (recommandé)",
                "Vectoriel (Sémantique)",
                "Lexical (Mots-clés)",
            ],
            value="Hybride (recommandé)",
            label="Mode de recherche",
            info="Sélectionnez l'algorithme de recherche souhaité.",
        ),
    ],
    outputs=gr.JSON(label="Résultats"),
    title="🔍 Recherche de fichier",
    description="Comparez en direct la recherche vectorielle (sens), lexicale (mots-clés SQLite FTS5) et hybride (RRF).",
    flagging_mode="never",
)


if __name__ == "__main__":
    interface.launch(debug=True)
