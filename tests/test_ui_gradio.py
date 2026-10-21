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

    Les appels au moteur de recherche sont simulés afin de tester
    le comportement de l'interface sans effectuer de vraies recherches.
    """

    async def test_rechercher_displays_only_selected_modes(self):
        """
        Vérifie que seuls les modes sélectionnés sont exécutés
        et affichés, et que le contenu est correctement échappé en HTML.
        """

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

            # Lance une recherche avec les modes lexical et vectoriel.
            result = await ui_gradio.rechercher(
                "ma recherche",
                ["Lexical (Mots-clés)", "Vectoriel (Sémantique)"],
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

        # Vérifie que la synthèse et les informations de fragments
        # ne sont pas affichées dans les résultats.
        self.assertNotIn("Synthèse", result)
        self.assertNotIn("<th>Chunk</th>", result)
        self.assertNotIn("<td>0</td>", result)

    async def test_rechercher_requires_at_least_one_mode(self):
        """
        Vérifie qu'un message est affiché lorsqu'aucun mode
        de recherche n'est sélectionné.
        """

        # Simule le moteur pour vérifier qu'il n'est pas appelé.
        with patch.object(
            ui_gradio, "search_mixed", new_callable=AsyncMock
        ) as search:
            result = await ui_gradio.rechercher("ma recherche", [])

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
        with patch.object(
            ui_gradio, "search_mixed", new_callable=AsyncMock
        ) as search:
            result = await ui_gradio.rechercher(" ", ["Lexical (Mots-clés)"])

        # Vérifie le message demandant de saisir une recherche.
        self.assertIn("Entrez une recherche", result)

        # Vérifie qu'aucune recherche n'a été lancée.
        search.assert_not_awaited()

    def test_format_results_html_includes_only_selected_panel(self):
        """
        Vérifie que le HTML contient uniquement le panneau sélectionné
        et affiche un message lorsque celui-ci ne contient aucun résultat.
        """

        # Génère le HTML avec le mode hybride sélectionné
        # et des listes de résultats vides.
        result = ui_gradio.format_results_html(
            ["Hybride (recommandé)"],
            {
                "Hybride (recommandé)": [],
                "Lexical (Mots-clés)": [],
            },
        )

        # Vérifie que seul le panneau sélectionné est affiché.
        self.assertIn("Hybride (recommandé)", result)
        self.assertNotIn("Lexical (Mots-clés)", result)

        # Vérifie le message affiché en l'absence de résultats.
        self.assertIn("Aucun résultat trouvé", result)

        # Vérifie que les panneaux sont disposés verticalement.
        self.assertIn("flex-direction:column", result)


if __name__ == "__main__":
    unittest.main()
