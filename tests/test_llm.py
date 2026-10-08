import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Importation du package src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recherche_fichiers.ollama_client.base import OllamaResponseError
from recherche_fichiers.ollama_client.llm import LLMClient, LLMError


class LLMClientTests(unittest.IsolatedAsyncioTestCase):
    """
    Tests unitaires du client de génération et de conversation LLM.
    """

    def setUp(self) -> None:
        self.client = LLMClient(default_model="modele-test")

    async def test_generate_sends_payload_and_strips_response(self) -> None:
        """
        Vérifie les paramètres envoyés à /api/generate
        et le nettoyage de la réponse.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"response": "  réponse générée  "},
        ) as post:
            result = await self.client.generate(
                prompt="question",
                system="consigne",
            )

        self.assertEqual(result, "réponse générée")
        post.assert_awaited_once_with(
            "/api/generate",
            json_data={
                "model": "modele-test",
                "prompt": "question",
                "stream": False,
                "options": {"temperature": 0.7},
                "system": "consigne",
            },
        )

    async def test_generate_keeps_custom_model_and_options(self) -> None:
        """
        Vérifie que le modèle et les options de génération
        fournis sont transmis sans perdre la température définie.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"response": "ok"},
        ) as post:
            await self.client.generate(
                prompt="question",
                model="autre-modele",
                temperature=0.2,
                stream=True,
                options={"top_p": 0.8, "temperature": 0.5},
            )

        post.assert_awaited_once_with(
            "/api/generate",
            json_data={
                "model": "autre-modele",
                "prompt": "question",
                "stream": True,
                "options": {"top_p": 0.8, "temperature": 0.5},
            },
        )

    async def test_generate_wraps_api_error_in_llm_error(self) -> None:
        """
        Vérifie que les erreurs de l'API de génération
        sont exposées sous forme de LLMError.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            side_effect=OllamaResponseError(500, "erreur serveur"),
        ):
            with self.assertRaises(LLMError):
                await self.client.generate("question")

    async def test_chat_sends_messages_and_returns_assistant_content(self) -> None:
        """
        Vérifie que chat() envoie l'historique de messages
        et retourne le contenu de la réponse assistant.
        """

        messages = [{"role": "user", "content": "bonjour"}]
        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            return_value={"message": {"content": "  salut  "}},
        ) as post:
            result = await self.client.chat(messages, temperature=0.4)

        self.assertEqual(result, "salut")
        post.assert_awaited_once_with(
            "/api/chat",
            json_data={
                "model": "modele-test",
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.4},
            },
        )

    async def test_chat_wraps_api_error_in_llm_error(self) -> None:
        """
        Vérifie qu'une erreur de l'API de conversation
        est exposée sous forme de LLMError.
        """

        with patch.object(
            self.client,
            "post",
            new_callable=AsyncMock,
            side_effect=OllamaResponseError(500, "erreur serveur"),
        ):
            with self.assertRaises(LLMError):
                await self.client.chat([])

    async def test_reformulate_query_delegates_to_generate(self) -> None:
        """
        Vérifie que la reformulation utilise une température
        basse et inclut la requête de l'utilisateur.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
            return_value="mots-clés",
        ) as generate:
            result = await self.client.reformulate_query("des exercices")

        self.assertEqual(result, "mots-clés")
        call = generate.await_args.kwargs
        self.assertIn("des exercices", call["prompt"])
        self.assertIn("reformuler", call["system"])
        self.assertEqual(call["temperature"], 0.2)

    async def test_group_by_theme_returns_empty_dict_without_documents(
        self,
    ) -> None:
        """
        Vérifie qu'aucun appel au modèle n'est effectué
        lorsqu'il n'y a aucun document à classer.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
        ) as generate:
            result = await self.client.group_by_theme([])

        self.assertEqual(result, {})
        generate.assert_not_awaited()

    async def test_group_by_theme_parses_json_in_markdown_block(self) -> None:
        """
        Vérifie que la réponse JSON entourée d'un bloc Markdown
        est correctement décodée.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
            return_value='```json\n{"Programmation": ["doc_0"]}\n```',
        ):
            result = await self.client.group_by_theme(
                [{"chunk_id": "doc_0", "content": "Boucles et variables"}],
                themes=["Programmation"],
            )

        self.assertEqual(result, {"Programmation": ["doc_0"]})

    async def test_group_by_theme_falls_back_on_invalid_json(self) -> None:
        """
        Vérifie que tous les documents sont conservés dans
        le thème Général lorsque la réponse n'est pas du JSON.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
            return_value="réponse invalide",
        ):
            with self.assertLogs(
                "recherche_fichiers.ollama_client.llm",
                level="WARNING",
            ):
                result = await self.client.group_by_theme(["un", "deux"])

        self.assertEqual(result, {"Général": ["doc_0", "doc_1"]})

    async def test_group_by_theme_handles_document_id_and_missing_ids(self) -> None:
        """
        Vérifie que group_by_theme prend en compte la clé document_id
        ou génère un identifiant par défaut pour les dictionnaires.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
            return_value='{"Algorithmes": ["doc_custom", "doc_1"]}',
        ) as generate_mock:
            result = await self.client.group_by_theme(
                [
                    {"document_id": "doc_custom", "content": "Tri fusion"},
                    {"content": "Dictionnaire sans identifiant"},
                ]
            )

        self.assertEqual(result, {"Algorithmes": ["doc_custom", "doc_1"]})
        prompt = generate_mock.await_args.kwargs["prompt"]
        self.assertIn("[doc_custom]: Tri fusion", prompt)
        self.assertIn("[doc_1]: Dictionnaire sans identifiant", prompt)

    async def test_summarize_documents_returns_message_for_empty_input(
        self,
    ) -> None:
        """
        Vérifie qu'un message explicite est retourné sans
        solliciter le modèle si la liste est vide.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
        ) as generate:
            result = await self.client.summarize_documents([])

        self.assertEqual(result, "Aucun contenu à synthétiser.")
        generate.assert_not_awaited()

    async def test_summarize_documents_includes_content_and_query(self) -> None:
        """
        Vérifie que la synthèse reprend les extraits et
        ajoute la requête au prompt.
        """

        with patch.object(
            self.client,
            "generate",
            new_callable=AsyncMock,
            return_value="synthèse",
        ) as generate:
            result = await self.client.summarize_documents(
                ["extrait de cours"],
                query="les boucles",
            )

        self.assertEqual(result, "synthèse")
        call = generate.await_args.kwargs
        self.assertIn("extrait de cours", call["prompt"])
        self.assertIn("les boucles", call["prompt"])
        self.assertEqual(call["temperature"], 0.3)


# Lancement des tests
if __name__ == "__main__":
    unittest.main()
