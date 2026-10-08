# --------------- #
# --- Modules --- #
# --------------- #

import sys
from pathlib import Path

# Ajout du dossier 'src' au chemin de recherche Python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from recherche_fichiers.service import core

# ------------- #
# --- Tests --- #
# ------------- #

class TestCore(unittest.IsolatedAsyncioTestCase):
    """
    Tests d'intégration du service principal (core.py) en exécutant les fonctions asynchrones avec isolation des dépendances 
    externes (Ollama & VectorStore).
    """

    def setUp(self):
        """Réinitialise l'instance du singleton du magasin de vecteurs avant chaque test."""
        core._store = None

    async def test_index_directory_invalid_path(self):
        """Vérifie qu'une exception NotADirectoryError est bien levée si le dossier source n'existe pas."""
        with self.assertRaises(NotADirectoryError):
            await core.index_directory("chemin/inexistant/impossible")

    @patch("recherche_fichiers.service.core._index_file", 
           new_callable=AsyncMock)
    @patch("recherche_fichiers.service.utils.list_files_by_format")
    async def test_index_directory_success(self, 
                                           mock_list_files, 
                                           mock_index_file):
        """Vérifie le parcours et le comptage des morceaux lors de l'indexation d'un dossier."""
        # Simulation des fichiers trouvés dans le dossier
        mock_list_files.return_value = [
            Path("data/demo/note.txt"),
            Path("data/demo/python_fonctions.txt")
        ]
        # Simulation du nombre de chunks retournés par chaque fichier (2 et 3)
        mock_index_file.side_effect = [2, 3]

        total_chunks = await core.index_directory("data/demo")

        self.assertEqual(total_chunks, 5)
        self.assertEqual(mock_index_file.call_count, 2)

    @patch("recherche_fichiers.service.core._get_store")
    @patch("recherche_fichiers.service.core.get_embedding", 
           new_callable=AsyncMock)
    @patch("recherche_fichiers.service.utils.read_text_file")
    async def test_index_file_success(self, 
                                      mock_read, 
                                      mock_get_embedding, 
                                      mock_get_store):
        """
        Vérifie la chaîne complète d'indexation d'un fichier :
        Lecture du texte -> Découpage -> Vectorisation -> Enregistrement dans le store.
        """
        file_path = Path("data/demo/note.txt")
        mock_read.return_value = "Ceci est un test de contenu."
        mock_get_embedding.return_value = [0.1, 
                                           0.2, 
                                           0.3]
        
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        chunks_indexed = await core._index_file(file_path)

        self.assertEqual(chunks_indexed, 1)
        mock_get_embedding.assert_awaited_once_with("Ceci est un test de contenu.")
        mock_store.add_documents.assert_called_once()

    @patch("recherche_fichiers.service.core._get_store")
    @patch("recherche_fichiers.service.core.get_embedding", 
           new_callable=AsyncMock)
    async def test_search_valid_query(self, 
                                      mock_get_embedding, 
                                      mock_get_store):
        """Vérifie la recherche sémantique par vectorisation de la requête utilisateur."""
        mock_get_embedding.return_value = [0.1, 
                                           0.2, 
                                           0.3]
        
        mock_store = MagicMock()
        mock_store.search.return_value = {
            "documents": [["Résultat de recherche"]],
            "metadatas": [[{"source_path": "data/demo/note.txt", 
                            "chunk_index": 0}]],
            "distances": [[0.05]]
        }
        mock_get_store.return_value = mock_store

        results = await core.search("exercice", k=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], 
                         "Résultat de recherche")
        mock_get_embedding.assert_awaited_once_with("exercice")
        mock_store.search.assert_called_once_with(query_embedding=[0.1, 0.2, 0.3], k=1)

    async def test_search_empty_query(self):
        """Vérifie qu'une requête vide ne déclenche aucune recherche et renvoie une liste vide."""
        results = await core.search("")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()