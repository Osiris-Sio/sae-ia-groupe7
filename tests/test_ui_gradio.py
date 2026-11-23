import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Permet d'importer le package situé dans le dossier src/
# lorsque les tests sont lancés depuis la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recherche_fichiers import ui_gradio


class GradioSearchTests(unittest.IsolatedAsyncioTestCase):
    """
    Tests unitaires de la recherche dans l'interface Gradio.

    Les appels au moteur de recherche et au LLM sont simulés afin de tester
    le comportement de l'interface sans effectuer de vraies recherches.
    """

    @patch("recherche_fichiers.ui_gradio.synthesize", new_callable=AsyncMock)
    async def test_rechercher_displays_only_selected_modes(self, mock_synthesize):
        """
        Vérifie que seuls les modes sélectionnés sont exécutés
        et affichés, et que le contenu est correctement échappé en HTML.
        """
        mock_synthesize.return_value = "Description LLM générée"

        # Simule une recherche et retourne un résultat fictif.
        async def search_side_effect(query, mode, k):
            return [
                {
                    "source_path": "a.txt",
                    "chunk_index": 0,
                    "score": 0.8,
                    "content": "Résultat <important>",
                }
            ]

        # Remplace le moteur de recherche par un mock asynchrone.
        with patch.object(
            ui_gradio,
            "search_mixed",
            new_callable=AsyncMock,
            side_effect=search_side_effect,
        ) as search:

            # Lance une recherche avec les modes lexical et vectoriel (descriptions LLM activées).
            result = await ui_gradio.rechercher(
                "ma recherche",
                ["Lexical (Mots-clés)", "Vectoriel (Sémantique)"],
                True,
            )

        # Vérifie que le moteur a été appelé deux fois.
        self.assertEqual(len(search.await_args_list), 2)

        # Vérifie que les bons modes ont été transmis au moteur.
        self.assertEqual(
            {call.kwargs["mode"] for call in search.await_args_list},
            {"lexical", "vectorial"},
        )

        # Vérifie que seuls les modes sélectionnés sont affichés.
        self.assertIn("Lexical (Mots-clés)", result)
        self.assertIn("Vectoriel (Sémantique)", result)
        self.assertNotIn("Hybride (recommandé)", result)

        # Vérifie que les caractères spéciaux du contenu sont échappés.
        self.assertIn("Résultat &lt;important&gt;", result)

        # Vérifie que la description LLM est bien présente.
        self.assertIn("Description LLM :", result)
        self.assertIn("Description LLM générée", result)

        # Vérifie que le contenu de l'extrait apparaît avant la description LLM.
        content_pos = result.find("Résultat &lt;important&gt;")
        desc_pos = result.find("Description LLM :")
        self.assertTrue(content_pos < desc_pos)

    async def test_rechercher_requires_at_least_one_mode(self):
        """
        Vérifie qu'un message est affiché lorsqu'aucun mode
        de recherche n'est sélectionné.
        """

        # Simule le moteur pour vérifier qu'il n'est pas appelé.
        with patch.object(ui_gradio, "search_mixed", new_callable=AsyncMock) as search:
            result = await ui_gradio.rechercher("ma recherche", [], True)

        # Vérifie le message affiché à l'utilisateur.
        self.assertIn("Sélectionnez au moins un mode", result)

        # Vérifie qu'aucune recherche n'a été lancée.
        search.assert_not_awaited()

    async def test_rechercher_requires_a_query(self):
        """
        Vérifie qu'une requête vide ou composée uniquement d'espaces
        est refusée avant l'appel au moteur de recherche.
        """

        # Simule le moteur pour vérifier qu'il n'est pas appelé.
        with patch.object(ui_gradio, "search_mixed", new_callable=AsyncMock) as search:
            result = await ui_gradio.rechercher(" ", ["Lexical (Mots-clés)"], True)

        # Vérifie le message demandant de saisir une recherche.
        self.assertIn("Entrez une recherche", result)

        # Vérifie qu'aucune recherche n'a été lancée.
        search.assert_not_awaited()

    def test_format_results_html_includes_only_selected_panel(self):
        """
        Vérifie que le HTML contient uniquement le panneau sélectionné,
        gère le formatage Markdown riche (titres, listes, liens, gras)
        et affiche un message lorsque le panneau ne contient aucun résultat.
        """

        # Vérifie le rendu Markdown de base (titres, listes, liens, gras)
        md_sample = (
            "## Titre du document\n\n"
            "1. Premier point\n"
            "* Puce importante\n"
            "[Lien externe](https://example.com)\n"
            "**texte en gras**"
        )
        rendered = ui_gradio.render_simple_markdown(md_sample)
        self.assertTrue("<h3" in rendered or "<h2" in rendered or "Titre du document" in rendered)
        self.assertIn("Lien externe", rendered)
        self.assertIn("<a href=\"https://example.com\">Lien externe</a>", rendered)
        self.assertIn("<strong>texte en gras</strong>", rendered)

        # Génère le HTML avec le mode hybride sélectionné
        # et des listes de résultats vides.
        result = ui_gradio.format_results_html(
            ["Hybride (recommandé)"],
            {
                "Hybride (recommandé)": [],
                "Lexical (Mots-clés)": [],
            },
            {},
            query="",
            enable_llm_desc=True,
        )

        # Vérifie que seul le panneau sélectionné est affiché.
        self.assertIn("Hybride (recommandé)", result)
        self.assertNotIn("Lexical (Mots-clés)", result)

        # Vérifie le message affiché en l'absence de résultats.
        self.assertIn("Aucun résultat trouvé", result)

        # Vérifie que les panneaux sont disposés verticalement.
        self.assertIn("flex-direction:column", result)

    def test_highlight_passage_safe_against_html_keywords(self):
        """Vérifie que le surlignage de mots clés sensibles (style, color) ne corrompt pas le HTML."""
        content = "Le style du code et la color sont importants."
        res = ui_gradio.highlight_passage(content, "style color")
        self.assertIn(
            '<mark style="background-color: #f0c988; padding: 2px 4px; border-radius: 4px; color: black">style</mark>',
            res,
        )
        self.assertIn(
            '<mark style="background-color: #f0c988; padding: 2px 4px; border-radius: 4px; color: black">color</mark>',
            res,
        )
        self.assertNotIn("style=<mark", res)

    @patch("recherche_fichiers.ui_gradio.synthesize", new_callable=AsyncMock)
    async def test_rechercher_includes_metrics_and_global_synthesis(
        self, mock_synthesize
    ):
        """Vérifie que le temps d'exécution et la synthèse globale RAG sont affichés sans emoji et avec déduplication."""
        mock_synthesize.return_value = "Synthèse globale complète"

        # Simule deux modes qui retournent le même chunk identique (déduplication)
        duplicate_chunk = [
            {
                "source_path": "cours.pdf",
                "chunk_index": 1,
                "score": 0.95,
                "content": "Contenu du cours",
            }
        ]

        with patch.object(
            ui_gradio,
            "search_mixed",
            new_callable=AsyncMock,
            return_value=duplicate_chunk,
        ):
            result = await ui_gradio.rechercher(
                "cours",
                ["Hybride (recommandé)", "Vectoriel (Sémantique)"],
                True,
            )

        # Vérifie métriques et synthèse globale
        self.assertIn("Temps d'exécution :", result)
        self.assertIn("Synthèse globale des documents (RAG)", result)
        self.assertIn("Synthèse globale complète", result)

        # Vérifie l'absence absolue d'emojis dans le HTML retourné
        self.assertNotIn("⏱", result)
        self.assertNotIn("🤖", result)
        self.assertNotIn("🔍", result)

        # Vérifie la déduplication : 1 appel description unitaire + 1 appel synthèse globale = 2 appels
        # (sans déduplication, il y aurait eu 2 appels unitaires + 1 synthèse = 3 appels)
        self.assertEqual(len(mock_synthesize.await_args_list), 2)

    def test_format_results_html_includes_tokens_per_second_and_raw_score_header(self):
        """Vérifie que le débit de tokens/s et l'en-tête de score brut sont bien affichés."""
        result = ui_gradio.format_results_html(
            selected_modes=["Hybride (recommandé)"],
            results_by_label={"Hybride (recommandé)": [
                {"source_path": "a.txt", "chunk_index": 0, "score": 0.85, "content": "texte"}
            ]},
            descriptions_by_label={},
            query="test",
            enable_llm_desc=False,
            execution_time_ms=120.5,
            tokens_per_second=45.2,
        )

        self.assertIn("Temps d'exécution :", result)
        self.assertIn("120.5 ms", result)
        self.assertIn("Tokens générés/seconde :", result)
        self.assertIn("45.2 tokens/s", result)
        self.assertIn("Score brut", result)

    @patch("recherche_fichiers.ui_gradio.synthesize", new_callable=AsyncMock)
    async def test_rechercher_displays_tokens_per_second_when_available(self, mock_synthesize):
        """Vérifie que la métrique de débit LLM est bien propagée par rechercher()."""
        mock_synthesize.return_value = "Synthèse"
        mock_results = [{"source_path": "doc.txt", "chunk_index": 0, "score": 0.9, "content": "hello"}]

        with patch.object(ui_gradio, "search_mixed", new_callable=AsyncMock, return_value=mock_results):
            with patch.object(ui_gradio, "get_session_tokens_per_second", return_value=55.8):
                result = await ui_gradio.rechercher("hello", ["Hybride (recommandé)"], True)

        self.assertIn("Temps d'exécution :", result)
        self.assertIn("Tokens générés/seconde :", result)
        self.assertIn("55.8 tokens/s", result)


if __name__ == "__main__":
    unittest.main()
