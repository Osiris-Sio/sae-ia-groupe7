#### Sprint 1 : Socle Ollama & Premier Pipeline Vectoriel de Bout en Bout

* User Stories :
   * US 1.1.1 : En tant qu'équipe, nous définissons le contrat de données commun (schéma de chunk : `chunk_id`, `document_id`, `content`, `source_path`, `format`, `chunk_index`) documenté et partagé avant d'écrire du code.
   * US 1.1.2 : En tant que développeur, j'implémente `ollama_client/base.py` (connexion HTTP asynchrone au serveur, vérification de disponibilité) à partir du wrapper fourni (`ollama_wrapper_iut.py`), en le passant en `async`/`await`.
   * US 1.1.3 : En tant que développeur, j'implémente `ollama_client/embedding.py` (appel à `/api/embed` avec `embeddinggemma`) et je vérifie/documente la dimension du vecteur retourné.
   * US 1.1.4  : En tant que développeur, j'implémente `storage/base.py` avec une classe `VectorStore` (ChromaDB `PersistentClient`, `add_documents()`, `search()`) et une collection persistante initialisée.
   * US 1.1.5 : En tant que développeur, j'implémente dans `service/core.py` un pipeline minimal `index_directory(path)` et `search(query, k=5)` reliant embedding → ChromaDB, testé sur un seul format simple (`.txt`).
   * US 1.1.6 : En tant qu'utilisateur, je dispose d'un `ui_gradio.py` minimal (une zone de texte + un bouton "Rechercher") qui appelle `search()` et affiche les résultats bruts.
   * US 1.1.7 : En tant qu'équipe, nous constituons un dataset de démo (`data/demo/`) avec au moins un fichier par format cible (pdf, docx, md, txt, csv), même si seul `.txt`/`.md` est réellement traité à ce stade.

* Livrables / DoR & DoD :
   * `ollama_client/base.py` et `embedding.py` non vides, testés par un appel réel à `embeddinggemma` (`tests/test_embedding.py` passe).
   * `storage/base.py` : `add_documents()`/`search()` fonctionnels sur ChromaDB, dimension du vecteur documentée dans le code ou le README.
   * `service/core.py` : `index_directory()` et `search()` démontrés de bout en bout sur au moins un fichier `.txt`.
   * `tests/test_ollama.py` vérifie que le serveur Ollama répond (`is_server_running()`).
   * `ui_gradio.py` lance une recherche réelle et affiche un résultat (pas de mock).
   * `data/demo/` committé avec au moins un fichier par format cible.
   * Point de vigilance explicite noté dans le sprint : l'index lexical (SQLite FTS5) n'est volontairement pas traité ce sprint, mais reste obligatoire pour le rendu final — prévu au Sprint 1.