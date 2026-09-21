#### Sprint 2 : Index Lexical & Extraction Multi-formats

* User Stories :
   * US 1.2.1 : En tant que développeur, j'étends `storage/base.py` avec une classe `LexicalStore` (SQLite, table `documents` + table virtuelle `chunks_fts` en FTS5), avec `add_documents()` et `search()` cohérents avec `VectorStore`.
   * US 1.2.2 : En tant que développeur, je vérifie que l'extension FTS5 est bien disponible dans notre environnement Python et je documente la version SQLite utilisée.
   * US 1.2.3 : En tant que développeur, j'étends `service/utils.py` avec des parsers pour PDF (`pdfplumber`/`pypdf`), DOCX (`python-docx`) et CSV (`pandas`), en plus du `.txt`/`.md` déjà géré.
   * US 1.2.4 : En tant que développeur, j'adapte `service/core.py` pour que `index_directory(path)` écrive simultanément dans `VectorStore` et `LexicalStore`, avec le même `chunk_id` dans les deux.
   * US 1.2.5 : En tant que développeur, j'implémente `search_mixed(query, mode="lexical|vectorial|hybrid", k=5)` dans `service/core.py`, qui route vers l'un, l'autre, ou combine les deux stores.
   * US 1.2.6 : En tant qu'utilisateur, je choisis mon mode de recherche via un `gr.Radio` dans `ui_gradio.py`, et je vois les résultats correspondants s'afficher.
   * US 1.2.7 : En tant qu'équipe, nous étoffons `data/demo/` avec des fichiers dans tous les formats désormais supportés (pdf, docx, csv en plus de txt/md).

* Livrables / DoR & DoD :
   * `LexicalStore.search()` retourne des résultats cohérents sur une requête test (`tests/test_search.py` couvre le lexical en plus du vectoriel).
   * Les 3 modes de `search_mixed()` fonctionnent et sont testés (au moins un test par mode).
   * `chunk_id` identique entre SQLite et ChromaDB vérifié par un test (recherche croisée possible).
   * `ui_gradio.py` : le `gr.Radio` change réellement le comportement de la recherche (pas juste visuel).
   * Au moins un fichier de chaque format cible dans `data/demo/`, tous indexés avec succès.
   * Requête de démonstration documentée dans le README (ex. l'exemple "modalités d'absence aux examens" du sujet) montrant la différence lexical vs vectoriel.