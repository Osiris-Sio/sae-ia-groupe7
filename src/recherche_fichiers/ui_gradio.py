"""
Interface utilisateur web Gradio pour le moteur de recherche documentaire.

Permet de :
- Rechercher par mots-clés (lexical), sémantique (vectoriel) ou hybride (RRF).
- Afficher les passages pertinents avec surbrillance des termes recherchés.
- Visualiser le score, la source et le contenu de chaque extrait.
- Générer à la demande des descriptions et synthèses documentaires via LLM local.
- Afficher les métriques de recherche (temps d'exécution).
"""

from __future__ import annotations

import asyncio
from html import escape
import os
from pathlib import Path
import re
import sys
import time

# Désactive la télémétrie distante pour éviter tout blocage réseau ou délai inutile
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

# Permet la résolution des modules que le script soit lancé directement ou via -m
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import gradio as gr

try:
    from markdown_it import MarkdownIt

    _md: MarkdownIt | None = MarkdownIt("commonmark", {"breaks": True, "html": False})
except Exception:
    _md = None

try:
    from recherche_fichiers.service.core import search_mixed, synthesize
except ImportError:
    from service.core import search_mixed, synthesize

try:
    from recherche_fichiers.ollama_client.llm import (
        get_session_tokens_per_second,
        reset_session_stats,
    )
except ImportError:
    try:
        from ollama_client.llm import (
            get_session_tokens_per_second,
            reset_session_stats,
        )
    except ImportError:

        def get_session_tokens_per_second():
            return None

        def reset_session_stats():
            pass


try:
    from recherche_fichiers.ollama_client import OllamaConnectionError, OllamaError
except ImportError:
    from ollama_client import OllamaConnectionError, OllamaError


try:
    from recherche_fichiers.config import TOP_K, EMBEDDING_MODEL, LLM_MODEL
except (ImportError, AttributeError):
    try:
        from config import TOP_K, EMBEDDING_MODEL, LLM_MODEL
    except (ImportError, AttributeError):
        TOP_K = 5
        EMBEDDING_MODEL = "embeddinggemma"
        LLM_MODEL = "gemma2:2b"

MODE_MAPPING = {
    "Hybride (recommandé)": "hybrid",
    "Vectoriel (Sémantique)": "vectorial",
    "Lexical (Mots-clés)": "lexical",
}

_CONTEXT_WINDOW_MARKERS = (
    "context length",
    "context window",
    "context size",
    "maximum context",
    "too many tokens",
    "prompt is too long",
    "input length exceeds",
    "fenêtre de contexte",
    "dépasse la fenêtre",
)


def highlight_passage(content: str, query: str) -> str:
    """Surligne les termes de la recherche de manière sécurisée en une seule passe."""
    if not content:
        return ""

    escaped_content = escape(str(content))
    if not query or not str(query).strip():
        return escaped_content

    words = [re.escape(w) for w in set(query.strip().split()) if len(w) > 2]
    if not words:
        return escaped_content

    try:
        pattern = re.compile(r"(" + "|".join(words) + r")", re.IGNORECASE)
        return pattern.sub(
            r'<mark style="background-color: #f0c988; padding: 2px 4px; border-radius: 4px; color: black">\1</mark>',
            escaped_content,
        )
    except Exception:
        return escaped_content


def render_simple_markdown(text: str) -> str:
    """Convertit le Markdown en HTML avec la bibliothèque markdown-it-py."""
    if not text:
        return ""
    if _md is not None:
        return _md.render(text).strip()
    return escape(str(text)).replace("\n", "<br>")


async def generate_chunk_description(query: str, result: dict) -> str:
    """Génère une description/résumé LLM spécifique pour un chunk donné."""
    content = result.get("content", "")
    source = result.get("source_path", "Inconnu")
    if not content.strip():
        return "Pas de contenu à décrire."

    try:
        desc = await synthesize(
            query,
            [
                {
                    "source_path": source,
                    "chunk_index": result.get("chunk_index", 0),
                    "content": content,
                }
            ],
        )
        return desc
    except Exception:
        return "Erreur lors de la génération de la description."


def _ollama_warning_message(error: OllamaError | str) -> str:
    """Convertit une erreur Ollama en message compréhensible pour l'utilisateur."""
    messages = [str(error)]
    current_error = error if isinstance(error, BaseException) else None
    while current_error is not None:
        if isinstance(current_error, OllamaConnectionError):
            return (
                "Le serveur Ollama ne répond pas. Vérifiez qu'il est démarré, "
                "puis réessayez."
            )
        current_error = current_error.__cause__
        if current_error is not None:
            messages.append(str(current_error))

    error_text = " ".join(messages).casefold()
    if any(marker in error_text for marker in _CONTEXT_WINDOW_MARKERS):
        return (
            "Votre requête dépasse la fenêtre de contexte du modèle. "
            "Réduisez la requête ou désactivez les descriptions et la synthèse IA, "
            "puis réessayez."
        )
    if any(
        marker in error_text
        for marker in (
            "impossible de se connecter",
            "connection refused",
            "failed to connect",
            "could not connect",
            "timed out",
            "timeout",
        )
    ):
        return (
            "Le serveur Ollama ne répond pas. Vérifiez qu'il est démarré, "
            "puis réessayez."
        )
    return f"Ollama n'a pas pu traiter la requête : {error}"


def _is_synthesis_error(value: str) -> bool:
    """Repère les erreurs renvoyées sous forme de texte par le service de synthèse."""
    return value.startswith("Erreur lors de la génération de la synthèse")


def format_results_html(
    selected_modes: list[str],
    results_by_label: dict[str, list[dict]],
    descriptions_by_label: dict[str, dict[int, str]],
    query: str = "",
    enable_llm_desc: bool = True,
    execution_time_ms: float | None = None,
    global_synthesis: str = "",
    tokens_per_second: float | None = None,
) -> str:
    """Affiche les modes sélectionnés dans des panneaux empilés avec surbrillance, métriques et synthèse globale."""
    selected_mode_set = set(selected_modes)
    selected_labels = [label for label in MODE_MAPPING if label in selected_mode_set]
    if not selected_labels:
        return "<p>Sélectionnez au moins un mode de recherche.</p>"

    content_header = "Contenu & Description LLM" if enable_llm_desc else "Contenu"

    panels = []
    for label in selected_labels:
        results = results_by_label.get(label, [])
        mode_descs = descriptions_by_label.get(label, {})
        if results:
            rows = ""
            for idx, result in enumerate(results):
                score = f"{float(result.get('score') or 0.0):.4f}"
                content_html = highlight_passage(
                    str(result.get("content") or ""), query
                )

                # Construction de la cellule : contenu extrait en premier
                cell_content = f"<div style='line-height:1.4;'>{content_html}</div>"
                if enable_llm_desc:
                    raw_llm_desc = mode_descs.get(idx, "En attente de description...")
                    llm_desc_html = render_simple_markdown(raw_llm_desc)
                    cell_content += (
                        "<div style='margin-top:10px;padding:8px 12px;"
                        "background-color:rgba(234, 88, 12, 0.08);border-left:3px solid #ea580c;"
                        "border-radius:4px;font-size:0.95em;line-height:1.5;'>"
                        "<strong style='display:block;margin-bottom:4px;color:#ea580c;'>Description LLM :</strong>"
                        f"<div class='llm-desc-text'>{llm_desc_html}</div>"
                        "</div>"
                    )

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
            "<thead><tr>"
            '<th style="width:24%">Source</th>'
            '<th style="width:12%" title="Score brut (similarité cosinus en vectoriel, BM25 en lexical, RRF en hybride)">Score brut</th>'
            f'<th style="width:64%">{content_header}</th>'
            "</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table></div></section>"
        )

    output_parts = [
        "<style>"
        ".llm-desc-text h2, .llm-desc-text h3, .llm-desc-text h4 { margin: 8px 0 4px 0; font-size: 1.05em; font-weight: 600; }"
        ".llm-desc-text ul, .llm-desc-text ol { margin: 4px 0 6px 18px; padding: 0; }"
        ".llm-desc-text li { margin-bottom: 2px; }"
        ".llm-desc-text p { margin: 4px 0; }"
        ".llm-desc-text a { color: #38bdf8; text-decoration: underline; }"
        "</style>"
    ]

    if execution_time_ms is not None:
        metrics_html = (
            f"<strong>Temps d'exécution :</strong> {execution_time_ms:.1f} ms"
        )
        if tokens_per_second is not None:
            metrics_html += f" | <strong>Tokens générés/seconde :</strong> {tokens_per_second:.1f} tokens/s"
        output_parts.append(
            f'<div style="font-size:0.95em;color:#4b5563;margin-bottom:12px;">'
            f"{metrics_html}"
            f"</div>"
        )

    output_parts.append(
        '<div style="display:flex;flex-direction:column;gap:16px">'
        f'{"".join(panels)}'
        "</div>"
    )

    if global_synthesis and global_synthesis.strip():
        output_parts.append(
            '<section style="margin-top:16px;border:1px solid #ea580c;'
            'border-radius:10px;padding:16px;background:var(--background-fill-primary);">'
            '<h3 style="margin:0 0 10px;color:#ea580c;">Synthèse globale des documents (RAG)</h3>'
            f'<div class="llm-desc-text" style="line-height:1.6;">{render_simple_markdown(global_synthesis)}</div>'
            "</section>"
        )

    return "".join(output_parts)


async def rechercher(
    query: str, selected_modes: list[str] | None, enable_llm_desc: bool
):
    """Exécute la recherche, mesure la latence et génère les descriptions / synthèse LLM."""
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

    reset_session_stats()
    start_time = time.perf_counter()

    # Exécution asynchrone des recherches mixtes
    try:
        mode_results = await asyncio.gather(
            *(search_mixed(query=query, mode=mode, k=TOP_K) for _, mode in modes)
        )
    except OllamaError as exc:
        message = _ollama_warning_message(exc)
        gr.Warning(message)
        return f"<p>{escape(message)}</p>"
    results_by_label = dict(zip((label for label, _ in modes), mode_results))

    descriptions_by_label = {label: {} for label in results_by_label}
    global_synthesis = ""

    if enable_llm_desc:
        # Optimisation : déduplication des chunks pour éviter les appels LLM redondants
        unique_chunks_map: dict[tuple, dict] = {}
        for results in results_by_label.values():
            for res in results:
                ckey = (res.get("source_path"), res.get("chunk_index"))
                if ckey not in unique_chunks_map:
                    unique_chunks_map[ckey] = res

        # 1. Génération unitaire des descriptions sur les chunks uniques
        chunk_keys = list(unique_chunks_map.keys())
        desc_tasks = [
            generate_chunk_description(query, unique_chunks_map[k]) for k in chunk_keys
        ]
        if desc_tasks:
            generated_descs = await asyncio.gather(*desc_tasks)
            descs_by_key = dict(zip(chunk_keys, generated_descs))
            for label, results in results_by_label.items():
                for idx, res in enumerate(results):
                    ckey = (res.get("source_path"), res.get("chunk_index"))
                    descriptions_by_label[label][idx] = descs_by_key.get(ckey, "")

        # 2. Synthèse globale RAG sur les meilleurs chunks uniques
        unique_chunks = list(unique_chunks_map.values())
        if unique_chunks:
            try:
                global_synthesis = await synthesize(query, unique_chunks[:TOP_K])
            except Exception:
                global_synthesis = (
                    "Erreur lors de la génération de la synthèse globale."
                )

    synthesis_errors = [
        value
        for descriptions in descriptions_by_label.values()
        for value in descriptions.values()
        if _is_synthesis_error(value)
    ]
    if _is_synthesis_error(global_synthesis):
        synthesis_errors.append(global_synthesis)
    if synthesis_errors:
        message = _ollama_warning_message(synthesis_errors[0])
        gr.Warning(message)
        for descriptions in descriptions_by_label.values():
            for idx, value in descriptions.items():
                if _is_synthesis_error(value):
                    descriptions[idx] = message
        if _is_synthesis_error(global_synthesis):
            global_synthesis = message

    execution_time_ms = (time.perf_counter() - start_time) * 1000
    tokens_per_second = get_session_tokens_per_second() if enable_llm_desc else None

    html_results = format_results_html(
        selected_labels,
        results_by_label,
        descriptions_by_label,
        query,
        enable_llm_desc,
        execution_time_ms=execution_time_ms,
        global_synthesis=global_synthesis,
        tokens_per_second=tokens_per_second,
    )
    return html_results


async def rechercher_ui(
    query: str, selected_modes: list[str] | None, enable_llm_desc: bool
):
    """Désactive le bouton durant la recherche et le réactive même en cas d'erreur."""
    yield gr.update(), gr.update(interactive=False)
    try:
        result = await rechercher(query, selected_modes, enable_llm_desc)
    except Exception:
        yield gr.update(), gr.update(interactive=True)
        raise
    yield result, gr.update(interactive=True)


def create_interface() -> gr.Blocks:
    """Construit et configure l'interface Gradio."""
    print(
        f"\n======================================================\n"
        f" Modèles IA actifs :\n"
        f" - LLM       : {LLM_MODEL}\n"
        f" - Embedding : {EMBEDDING_MODEL}\n"
        f"======================================================\n",
        flush=True,
    )
    with gr.Blocks(title=" 🔍 Recherche de fichiers & Descriptions LLM") as demo:
        gr.Markdown("# 🔍 Recherche de fichiers & Descriptions LLM")
        gr.Markdown(
            f"Recherche hybride, vectorielle et lexicale dans le contenu des documents.<br>"
            f"*(Modèles actifs : LLM <code>{LLM_MODEL}</code> | Embedding <code>{EMBEDDING_MODEL}</code>)*"
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
                    label="Activer les descriptions et la synthèse IA (LLM)",
                    value=False,
                    info="Optionnel. Laisser décoché pour une recherche instantanée.",
                )
                search_button = gr.Button("Rechercher", variant="primary")

        results_output = gr.HTML()

        search_button.click(
            fn=rechercher_ui,
            inputs=[query_input, mode_input, llm_desc_checkbox],
            outputs=[results_output, search_button],
        )
        query_input.submit(
            fn=rechercher_ui,
            inputs=[query_input, mode_input, llm_desc_checkbox],
            outputs=[results_output, search_button],
        )
    return demo


def __getattr__(name: str):
    """Permet l'accès paresseux à l'interface pour éviter de l'instancier à l'import."""
    if name == "interface":
        return create_interface()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    app = create_interface()
    app.launch(debug=True)
