# --------------- #
# --- Modules --- #
# --------------- #

import sys
from pathlib import Path

# Ajout du dossier 'src' au chemin de recherche Python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from unittest.mock import patch, MagicMock
from recherche_fichiers.service import utils

# ------------- #
# --- Tests --- #
# ------------- #

class TestUtils(unittest.TestCase):
    """
    Tests unitaires pour les fonctions utilitaires de traitement de fichiers multi-formats, 
    de découpage de texte (chunking) et de formatage des résultats.
    """

    def setUp(self):
        """Initialisation du chemin du dossier de démonstration pour les tests."""
        self.demo_dir = Path("data/demo")

    def test_list_files_by_format(self):
        """Vérifie le filtrage récursif des fichiers selon plusieurs formats supportés."""
        formats = {".txt", ".md", ".pdf"}
        # Création d'un dossier temporaire ou utilisation du dossier existant
        files = utils.list_files_by_format(self.demo_dir, formats)

        for f in files:
            self.assertIn(f.suffix.lower(), formats)
            self.assertTrue(f.is_file())

    def test_read_text_file(self):
        """Vérifie la lecture du contenu texte d'un fichier existant."""
        test_file = self.demo_dir / "note.txt"
        if test_file.exists():
            content = utils.read_text_file(test_file)
            self.assertIsInstance(content, str)

    @patch("pdfplumber.open")
    def test_read_pdf_file(self, mock_pdf_open):
        """Vérifie l'extraction de texte depuis un fichier PDF."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Texte extrait de la page PDF."
        mock_pdf_instance = MagicMock()
        mock_pdf_instance.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf_instance

        content = utils.read_pdf_file(Path("dummy.pdf"))
        self.assertIn("Texte extrait", content)

    @patch("docx.Document")
    def test_read_docx_file(self, mock_docx):
        """Vérifie l'extraction de texte et de tableaux depuis un fichier DOCX."""
        mock_doc = MagicMock()
        p1 = MagicMock()
        p1.text = "Paragraphe Word."
        mock_doc.paragraphs = [p1]
        mock_doc.tables = []
        mock_docx.return_value = mock_doc

        content = utils.read_docx_file(Path("dummy.docx"))
        self.assertEqual(content, "Paragraphe Word.")

    @patch("pandas.read_csv")
    def test_read_csv_file(self, mock_read_csv):
        """Vérifie l'extraction de texte depuis un fichier CSV via pandas."""
        mock_df = MagicMock()
        mock_df.to_string.return_value = "col1 | col2\nval1 | val2"
        mock_read_csv.return_value = mock_df

        content = utils.read_csv_file(Path("dummy.csv"))
        self.assertIn("col1 | col2", content)

    def test_load_file_content_unsupported(self):
        """Vérifie qu'un format de fichier non pris en charge lève une exception ValueError."""
        with self.assertRaises(ValueError):
            utils.load_file_content(Path("image.png"))

    def test_make_document_id(self):
        """Vérifie le nettoyage du chemin d'accès pour générer un ID de document valide."""
        path = Path("/home/user/document test #1.txt")
        doc_id = utils.make_document_id(path)
        self.assertNotIn(" ", doc_id)
        self.assertNotIn("#", doc_id)

    def test_chunk_text_short(self):
        """Vérifie qu'un texte plus court que la taille de chunk retourne un seul morceau."""
        text = "Bonjour, ceci est un test court."
        chunks = utils.chunk_text(text, chunk_size=500, overlap=50)
        self.assertEqual(chunks, [text])

    def test_chunk_text_empty(self):
        """Vérifie qu'un texte vide ou ne contenant que des espaces retourne une liste vide."""
        self.assertEqual(utils.chunk_text(""), [])
        self.assertEqual(utils.chunk_text("   \n  "), [])

    def test_chunk_text_long(self):
        """Vérifie le découpage d'un texte long en plusieurs morceaux avec chevauchement."""
        text = "Phrase un.\nPhrase deux.\nPhrase trois.\nPhrase quatre."
        chunks = utils.chunk_text(text, chunk_size=25, overlap=5)
        self.assertGreater(len(chunks), 1)

    def test_format_search_results_distances(self):
        """Vérifie la transformation de la structure brute avec 'distances' (VectorStore)."""
        raw_results = {
            "documents": [["Contenu chunk 0", "Contenu chunk 1"]],
            "metadatas": [[
                {"source_path": "data/demo/note.txt", "chunk_index": 0},
                {"source_path": "data/demo/note.txt", "chunk_index": 1}
            ]],
            "distances": [[0.12, 0.45]]
        }

        formatted = utils.format_search_results(raw_results)

        self.assertEqual(len(formatted), 2)
        self.assertEqual(formatted[0]["content"], "Contenu chunk 0")
        self.assertEqual(formatted[0]["score"], 0.12)

    def test_format_search_results_scores(self):
        """Vérifie la transformation de la structure brute avec 'scores' (LexicalStore)."""
        raw_results = {
            "documents": [["Contenu lexical"]],
            "metadatas": [[{"source_path": "data/demo/note.md", "chunk_index": 0}]],
            "scores": [[1.85]]
        }

        formatted = utils.format_search_results(raw_results)

        self.assertEqual(len(formatted), 1)
        self.assertEqual(formatted[0]["score"], 1.85)

    def test_format_search_results_empty(self):
        """Vérifie que le formatage gère correctement une structure de résultats vide."""
        self.assertEqual(utils.format_search_results({}), [])


if __name__ == "__main__":
    unittest.main()