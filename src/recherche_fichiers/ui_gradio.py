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
    from recherche_fichiers.service.core import search_mixed, synthesize
except ImportError:
    from service.core import search_mixed, synthesize

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

def render_simple_markdown(text: str) -> str:
    """Convertit basiquement le texte (gras, italique) sans bibliothèque externe tout en restant sécurisé."""
    if not text:
        return ""
    safe_text = escape(str(text))
    # Gras (**texte** ou __texte__)
    safe_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', safe_text)
    safe_text = re.sub(r'__(.*?)__', r'<strong>\1</strong>', safe_text)
    # Italique (*texte* ou _texte_)
    safe_text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', safe_text)
    safe_text = re.sub(r'_(.*?)_', r'<em>\1</em>', safe_text)
    # Sauts de ligne
    safe_text = safe_text.replace('\n', '<br>')
    return safe_text

async def generate_chunk_description(query: str, result: dict) -> str:
    """Génère une description/résumé LLM spécifique pour un chunk donné."""
    content = result.get('content', '')
    source = result.get('source_path', 'Inconnu')
    if not content.strip():
        return "Pas de contenu à décrire."
    
    try:
        # On réutilise la fonction synthesize pour générer la description unitaire
        desc = await synthesize(query, [{"source_path": source, "chunk_index": result.get("chunk_index", 0), "content": content}])
        return desc
    except Exception:
        return "Erreur lors de la génération de la description."

def format_results_html(
    selected_modes: list[str],
    results_by_label: dict[str, list[dict]],
    descriptions_by_label: dict[str, dict[int, str]],
    query: str = "",
    enable_llm_desc: bool = True,
) -> str:
    """Affiche les modes sélectionnés dans des panneaux empilés avec surbrillance et description LLM optionnelle par résultat."""
    selected_mode_set = set(selected_modes)
    selected_labels = [label for label in MODE_MAPPING if label in selected_mode_set]
    if not selected_labels:
        return "<p>Sélectionnez au moins un mode de recherche.</p>"

    panels = []
    for label in selected_labels:
        results = results_by_label.get(label, [])
        mode_descs = descriptions_by_label.get(label, {})
        if results:
            rows = ""
            for idx, result in enumerate(results):
                score = f"{float(result.get('score') or 0.0):.4f}"
                content_html = highlight_passage(str(result.get('content') or ''), query)
                
                # Construction de la cellule contenu (+ description LLM si activée)
                cell_content = ""
                if enable_llm_desc:
                    raw_llm_desc = mode_descs.get(idx, "En attente de description...")
                    llm_desc_html = render_simple_markdown(raw_llm_desc)
                    cell_content += (
                        "<div style='margin-bottom:10px;padding:8px 12px;background-color:#27272a;"
                        "border-left:3px solid #ea580c;border-radius:4px;color:#1e293b;font-size:0.95em;'>"
                        "<strong style='display:block;margin-bottom:4px;color:#ea580c;'>Description LLM :</strong>"
                        f"<div>{llm_desc_html}</div>"
                        "</div>"
                    )
                cell_content += content_html

                rows += (
                    "<tr>"
                    f"<td>{escape(str(result.get('source_path') or ''))}</td>"
                    f"<td>{escape(score)}</td>"
                    f"<td>{cell_content}</td>"
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
            '<th style="width:64%">Contenu & Description LLM</th>'
            '</tr></thead>'
            f'<tbody>{rows}</tbody>'
            '</table></div></section>'
        )

    return (
        '<div style="display:flex;flex-direction:column;gap:16px">'
        f'{"".join(panels)}'
        '</div>'
    )


async def rechercher(query: str, selected_modes: list[str] | None, enable_llm_desc: bool):
    """Exécute la recherche et génère les descriptions LLM individuelles si l'option est activée."""
    if not query or not query.strip():
        return "<p>Entrez une recherche.</p>"

    selected_labels = set(selected_modes or [])
    modes = [
        (label, mode)
        for label, mode in MODE_MAPPING.items()
        if label in selected_labels
    ]
    if not modes:
        return format_results_html([], {}, {}, query, enable_llm_desc)

    # Exécution asynchrone des recherches mixtes
    mode_results = await asyncio.gather(
        *(search_mixed(query=query, mode=mode, k=TOP_K) for _, mode in modes)
    )
    results_by_label = dict(zip((label for label, _ in modes), mode_results))

    # Génération asynchrone des descriptions LLM uniquement si demandé
    descriptions_by_label = {}
    desc_tasks = []
    task_keys = []

    for label, results in results_by_label.items():
        descriptions_by_label[label] = {}
        for idx, result in enumerate(results):
            if enable_llm_desc:
                desc_tasks.append(generate_chunk_description(query, result))
                task_keys.append((label, idx))

    if desc_tasks:
        generated_descs = await asyncio.gather(*desc_tasks)
        for (label, idx), desc in zip(task_keys, generated_descs):
            descriptions_by_label[label][idx] = desc

    html_results = format_results_html(selected_labels, results_by_label, descriptions_by_label, query, enable_llm_desc)
    return html_results


with gr.Blocks() as interface:
    gr.Markdown("# 🔍 Recherche de fichiers & Descriptions LLM")
    gr.Markdown(
        "Chaque résultat de fichier retourné peut disposer d'une description "
        "générée par le LLM (avec prise en compte du formatage Markdown de base)."
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
            llm_desc_checkbox = gr.Checkbox(
                label="Générer les descriptions LLM pour les fichiers",
                value=True,
            )
            search_button = gr.Button("Rechercher", variant="primary")

    results_output = gr.HTML()

    search_button.click(
        fn=rechercher,
        inputs=[query_input, mode_input, llm_desc_checkbox],
        outputs=[results_output],
    )
    query_input.submit(
        fn=rechercher,
        inputs=[query_input, mode_input, llm_desc_checkbox],
        outputs=[results_output],
    )


if __name__ == "__main__":
    interface.launch(debug=True)