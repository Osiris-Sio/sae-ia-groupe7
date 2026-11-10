import asyncio
from html import escape
import sys
from pathlib import Path
import re

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

def highlight_passage(content: str, query: str) -> str:
    """Surligne les termes de la recherche ou les passages pertinents de manière optimisée."""
    if not content:
        return ""
    
    escaped_content = escape(str(content))
    if not query or not str(query).strip():
        return escaped_content
    
    words = set(query.strip().split())
    highlighted = escaped_content
    
    for word in words:
        if len(word) > 2:
            try:
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                highlighted = pattern.sub(
                    r'<mark style="background-color: #f0c988; padding: 2px 4px; border-radius: 4px; color: black">\g<0></mark>',
                    highlighted
                )
            except Exception:
                # En cas de pattern invalide généré par regex
                continue
                
    return highlighted

def format_results_html(
    selected_modes: list[str],
    results_by_label: dict[str, list[dict]],
    query: str = "",
) -> str:
    """Affiche les modes sélectionnés dans des panneaux empilés avec surbrillance."""
    selected_mode_set = set(selected_modes)
    selected_labels = [label for label in MODE_MAPPING if label in selected_mode_set]
    if not selected_labels:
        return "<p>Sélectionnez au moins un mode de recherche.</p>"

    panels = []
    for label in selected_labels:
        results = results_by_label.get(label, [])
        if results:
            rows = ""
            for result in results:
                score = f"{float(result.get('score') or 0.0):.4f}"
                content_html = highlight_passage(str(result.get('content') or ''), query)
                rows += (
                    "<tr>"
                    f"<td>{escape(str(result.get('source_path') or ''))}</td>"
                    f"<td>{escape(score)}</td>"
                    f"<td>{content_html}</td>"
                    "</tr>"
                )
        else:
            rows = '<tr><td colspan="3">Aucun résultat trouvé.</td></tr>'

        panels.append(
            '<section style="min-width:0;border:1px solid #d1d5db;'
            'border-radius:10px;padding:16px;background:var(--background-fill-primary);">'
            f'<h3 style="margin:0 0 12px">{escape(label)}</h3>'
            '<div style="overflow-x:auto">'
            '<table style="width:100%;border-collapse:collapse;'
            'text-align:left;table-layout:fixed">'
            '<thead><tr>'
            '<th style="width:24%">Source</th>'
            '<th style="width:12%">Score</th>'
            '<th style="width:64%">Contenu</th>'
            '</tr></thead>'
            f'<tbody>{rows}</tbody>'
            '</table></div></section>'
        )

    return (
        '<div style="display:flex;flex-direction:column;gap:16px">'
        f'{"".join(panels)}'
        '</div>'
    )


async def rechercher(query: str, selected_modes: list[str] | None) -> str:
    """Recherche dans les modes sélectionnés et affiche uniquement leurs résultats avec surbrillance."""
    if not query or not query.strip():
        return "<p>Entrez une recherche.</p>"

    selected_labels = set(selected_modes or [])
    modes = [
        (label, mode)
        for label, mode in MODE_MAPPING.items()
        if label in selected_labels
    ]
    if not modes:
        return format_results_html([], {}, query)

    mode_results = await asyncio.gather(
        *(search_mixed(query=query, mode=mode, k=TOP_K) for _, mode in modes)
    )
    results_by_label = dict(zip((label for label, _ in modes), mode_results))

    return format_results_html(selected_labels, results_by_label, query)


with gr.Blocks() as interface:
    gr.Markdown("# 🔍 Recherche de fichiers")
    gr.Markdown(
        "Choisissez les modes à comparer. Seuls les modes sélectionnés "
        "seront affichés."
    )
    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="Votre recherche",
                placeholder="Entrez vos mots-clés ou une question...",
                lines=2,
            )
        with gr.Column(scale=1):
            mode_input = gr.CheckboxGroup(
                choices=list(MODE_MAPPING),
                value=["Hybride (recommandé)"],
                label="Modes de recherche",
                info="Vous pouvez en sélectionner plusieurs.",
            )
            search_button = gr.Button("Rechercher", variant="primary")

    results_output = gr.HTML()
    search_button.click(
        fn=rechercher,
        inputs=[query_input, mode_input],
        outputs=results_output,
    )
    query_input.submit(
        fn=rechercher,
        inputs=[query_input, mode_input],
        outputs=results_output,
    )


if __name__ == "__main__":
    interface.launch(debug=True)