"""Module d'inférence LLM via Ollama pour le traitement en langage naturel.

Utilise principalement le modèle `gemma4:12b` (ou équivalent configuré) pour :
- La reformulation de requêtes de recherche utilisateur
- Le regroupement thématique d'exercices ou de documents
- La synthèse ou la génération de documents à partir de résultats trouvés
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .base import (
    DEFAULT_TIMEOUT,
    OllamaClient,
    OllamaError,
)

logger = logging.getLogger(__name__)

# Tentative de récupération des configurations globales
try:
    from recherche_fichiers.config import LLM_MODEL  # type: ignore
except (ImportError, AttributeError):
    LLM_MODEL = None

# Modèle par défaut défini dans architecture.md et le cahier des charges
DEFAULT_LLM_MODEL = LLM_MODEL or os.getenv("LLM_MODEL") or "gemma4:12b"


# =====================================================================
# Exceptions (Erreur étiqueter pour la gestion des erreurs)
# =====================================================================


class LLMError(OllamaError):
    """Levée lors d'une erreur d'inférence avec le LLM."""

    pass


# =====================================================================
# Client (OllamaClient)
# =====================================================================


class LLMClient(OllamaClient):
    """Client dédié aux interactions textuelles avec le modèle de langage (LLM)."""

    def __init__(
        self,
        host: str | None = None,
        default_model: str = DEFAULT_LLM_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise le client LLM.

        Args:
            host: URL du serveur Ollama.
            default_model: Nom du modèle LLM (défaut: 'gemma4:12b').
            timeout: Délai d'attente en secondes.
        """
        super().__init__(host=host, timeout=timeout)
        self.default_model = default_model

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        stream: bool = False,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Génère une complétion textuelle via l'endpoint `/api/generate`.

        Args:
            prompt: Texte d'instruction ou question pour le modèle.
            system: Prompt système optionnel pour guider le comportement.
            model: Nom du modèle (défaut: `self.default_model`).
            temperature: Degré de créativité (0.0 = déterministe, 1.0 = créatif).
            stream: Si True, la réponse complète est quand même concaténée ici.
            options: Paramètres additionnels de génération Ollama.

        Returns:
            str: Le texte généré par le modèle.

        Raises:
            LLMError: Si la génération échoue.
        """
        target_model = model or self.default_model
        req_options = options or {}
        req_options.setdefault("temperature", temperature)

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": stream,
            "options": req_options,
        }
        if system:
            payload["system"] = system

        try:
            data = await self.post("/api/generate", json_data=payload)
            response_text = data.get("response", "")
            return response_text.strip()
        except Exception as err:
            raise LLMError(
                f"Erreur lors de la génération avec le modèle {target_model}: {err}"
            ) from err

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Envoie un historique de conversation structuré via l'endpoint `/api/chat`.

        Args:
            messages: Liste de dictionnaires au format `[{"role": "user"|"assistant"|"system", "content": "..."}]`.
            model: Nom du modèle.
            temperature: Paramètre de température d'échantillonnage.
            options: Paramètres avancés de configuration Ollama.

        Returns:
            str: Le contenu textuel du message assistant retourné.
        """
        target_model = model or self.default_model
        req_options = options or {}
        req_options.setdefault("temperature", temperature)

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": req_options,
        }

        try:
            data = await self.post("/api/chat", json_data=payload)
            message = data.get("message", {})
            return message.get("content", "").strip()
        except Exception as err:
            raise LLMError(
                f"Erreur lors de l'appel /api/chat avec le modèle {target_model}: {err}"
            ) from err

    # =================================================================
    # Méthodes Métier Spécifiques au Projet (Cahier des charges)
    # =================================================================

    async def reformulate_query(self, query: str) -> str:
        """Reformule et enrichit une requête en langage naturel pour la recherche sémantique.

        Exemple:
            "des exos sur les boucles" -> "exercices algorithmique programmation boucles for while itération"

        Args:
            query: Requête brute saisie par l'utilisateur.

        Returns:
            str: Requête reformulée enrichie de synonymes et concepts clés.
        """
        system_prompt = (
            "Tu es un assistant expert en recherche documentaire et sémantique. "
            "Ta mission est de reformuler la requête de l'utilisateur pour maximiser "
            "la pertinence de la recherche vectorielle et lexicale. "
            "Renvoie uniquement les mots-clés et concepts essentiels, sans phrase d'introduction ni politesse."
        )
        user_prompt = (
            f"Requête utilisateur: {query}\nMots-clés et reformulation enrichie:"
        )
        return await self.generate(
            prompt=user_prompt, system=system_prompt, temperature=0.2
        )

    async def group_by_theme(
        self,
        documents: list[str | dict[str, Any]],
        themes: list[str] | None = None,
    ) -> dict[str, list[Any]]:
        """Regroupe des contenus ou exercices retrouvés selon des thématiques logiques.

        Args:
            documents: Liste d'extraits textuels ou de dictionnaires de documents.
            themes: Liste optionnelle de thèmes imposés.

        Returns:
            dict[str, list[Any]]: Dictionnaire associant chaque thème aux documents pertinents.
        """
        if not documents:
            return {}

        doc_descriptions = []
        for i, doc in enumerate(documents):
            if isinstance(doc, dict):
                content = doc.get("content", str(doc))[:300]
                doc_id = doc.get("chunk_id", doc.get("document_id", f"doc_{i}"))
            else:
                content = str(doc)[:300]
                doc_id = f"doc_{i}"
            doc_descriptions.append(f"[{doc_id}]: {content}")

        docs_formatted = "\n---\n".join(doc_descriptions)
        themes_instruction = (
            f"Thèmes suggérés: {', '.join(themes)}"
            if themes
            else "Déduis des thèmes pertinents automatiquement."
        )

        prompt = (
            "Organise les documents suivants par thématiques d'apprentissage ou d'exercices.\n"
            f"{themes_instruction}\n\n"
            "Retourne UNIQUEMENT un objet JSON valide dont les clés sont les noms des thèmes "
            'et les valeurs sont des listes d\'identifiants de documents (ex: ["doc_0", "doc_1"]).\n\n'
            f"Documents à classer :\n{docs_formatted}\n\n"
            "Format JSON strict :"
        )

        system = "Tu es un classificateur de documents pédagogiques. Tu réponds exclusivement en JSON valide."
        raw_output = await self.generate(prompt=prompt, system=system, temperature=0.1)

        # Extraction et parsing sécurisé du JSON
        try:
            # Nettoyage d'éventuels blocs markdown ```json ... ```
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            parsed: dict[str, list[Any]] = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError:
            logger.warning(
                "Échec du décodage JSON pour le regroupement par thème. Réponse brute: %s",
                raw_output,
            )
            return {"Général": [f"doc_{i}" for i in range(len(documents))]}

    async def summarize_documents(
        self,
        contents: list[str],
        query: str | None = None,
    ) -> str:
        """Génère une synthèse concise des extraits documentaires retrouvés.

        Args:
            contents: Liste des textes retrouvés.
            query: Requête d'origine si applicable pour cibler la synthèse.

        Returns:
            str: Synthèse claire rédigée en français.
        """
        if not contents:
            return "Aucun contenu à synthétiser."

        joined_context = "\n\n".join(f"- {c}" for c in contents)
        query_context = f" en lien avec la recherche '{query}'" if query else ""
        prompt = (
            f"Synthétise les extraits de documents suivants{query_context}. "
            "Sois concis, précis et pédagogique.\n\n"
            f"Extraits :\n{joined_context}\n\n"
            "Synthèse :"
        )
        system = "Tu es un assistant d'analyse documentaire. Réponds de façon claire et structurée en français."
        return await self.generate(prompt=prompt, system=system, temperature=0.3)
