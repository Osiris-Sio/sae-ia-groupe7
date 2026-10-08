# --------------- #
# --- Modules --- #
# --------------- #

import sys
from pathlib import Path

# Ajout du dossier 'src' au chemin de recherche Python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from recherche_fichiers.service import utils

# ------------- #
# --- Tests --- #
# ------------- #

class TestUtils(unittest.TestCase):
    """
    Tests unitaires pour les fonctions utilitaires de traitement de fichiers, de découpage de texte (chunking) et de formatage 
    des résultats.
    """

    def setUp(self):
        """Initialisation du chemin du dossier de démonstration pour les tests."""
        self.demo_dir = Path("data/demo")

    def test_list_files_by_format(self):
        """Vérifie le filtrage récursif des fichiers selon l'extension."""
        formats = {".txt"}
        files   = utils.list_files_by_format(self.demo_dir, formats)

        # On vérifie que 6 fichier sont trouvés et que tous ont l'extension .txt
        self.assertEqual(len(files), 6)
        for f in files:
            self.assertEqual(f.suffix.lower(), ".txt")
            self.assertTrue(f.is_file())

    def test_read_text_file(self):
        """Vérifie la lecture du contenu texte d'un fichier existant."""
        test_file = self.demo_dir / "note.txt"
        if test_file.exists():
            content = utils.read_text_file(test_file)
            self.assertIsInstance(content, str)

    def test_make_document_id(self):
        """Vérifie le nettoyage du chemin d'accès pour générer un ID de document valide."""
        path = Path("/home/user/document test #1.txt")
        doc_id = utils.make_document_id(path)
        self.assertNotIn(" ", doc_id)
        self.assertNotIn("#", doc_id)

    def test_chunk_text_short(self):
        """Vérifie qu'un texte plus court que la taille de chunk retourne un seul morceau."""
        text = "Bonjour, ceci est un test court."
        chunks = utils.chunk_text(text, 
                                  chunk_size=500, 
                                  overlap=50)
        self.assertEqual(chunks, [text])

    def test_chunk_text_empty(self):
        """Vérifie qu'un texte vide ou ne contenant que des espaces retourne une liste vide."""
        self.assertEqual(utils.chunk_text(""), [])
        self.assertEqual(utils.chunk_text("   \n  "), [])

    def test_chunk_text_long(self):
        """Vérifie le découpage d'un texte long en plusieurs morceaux avec chevauchement."""
        text = "Phrase un.\nPhrase deux.\nPhrase trois.\nPhrase quatre."
        chunks = utils.chunk_text(text, 
                                  chunk_size=25, 
                                  overlap=5)
        self.assertGreater(len(chunks), 1)

    def test_format_search_results(self):
        """Vérifie la transformation de la structure brute reçue de ChromaDB en liste utilisable par l'UI."""
        raw_results = {
            "documents": [["Contenu chunk 0", 
                           "Contenu chunk 1"]],
            "metadatas": [[
                {"source_path": "data/demo/note.txt", "chunk_index": 0},
                {"source_path": "data/demo/note.txt", "chunk_index": 1}
            ]],
            "distances": [[0.12, 
                           0.45]]
        }

        formatted = utils.format_search_results(raw_results)

        # Vérification du format de sortie
        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]["content"], 
                         "Contenu chunk 0")
        self.assertEqual(formatted[0]["source_path"], 
                         "data/demo/note.txt")
        self.assertEqual(formatted[0]["chunk_index"], 0)
        self.assertEqual(formatted[0]["score"], 0.12)

    def test_format_search_results_empty(self):
        """Vérifie que le formatage gère correctement une structure de résultats vide."""
        self.assertEqual(utils.format_search_results({}), [])


if __name__ == "__main__":
    unittest.main()