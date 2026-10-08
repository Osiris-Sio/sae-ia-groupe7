#### Sprint 3 : Synthèse Gemma4, Citations & Interface Comparative

* User Stories :
   * US 1.3.1 : En tant que développeur, j'implémente `ollama_client/llm.py` (`generate()` async vers `gemma4:12b`) avec un prompt qui force la citation explicite des sources (chemin + numéro de chunk).
   * US 1.3.2 : En tant que développeur, j'ajoute dans `service/core.py` une fonction `synthesize(query, chunks)` qui construit le prompt à partir des chunks récupérés (vectoriel + lexical) et retourne un texte avec citations.
   * US 1.3.3 : En tant qu'utilisateur, je vois dans `ui_gradio.py` les résultats lexical et vectoriel affichés côte à côte (deux `gr.Dataframe` ou deux colonnes distinctes), plus la synthèse en dessous.
   * US 1.3.4 : En tant qu'utilisateur, je vois les passages extraits surlignés dans le texte source affiché, via un composant `gr.HTML()` custom.
   * US 1.3.5 : En tant qu'utilisateur, je vois les métriques de chaque recherche (temps d'inférence, tokens générés/seconde, score de similarité cosinus brut) affichées à côté des résultats.
   * US 1.3.6 : En tant que développeur, je m'assure que toutes les valeurs renvoyées aux composants Gradio sont JSON-sérialisables (str, int, float, list, dict uniquement).

* Livrables / DoR & DoD :
   * `synthesize()` produit un texte citant au moins une source réelle, testé sur la requête de démo du sujet.
   * Affichage côte à côte fonctionnel dans l'UI, avec les deux moteurs visiblement différenciés.
   * Surbrillance visible et correcte sur au moins un cas de test (le passage surligné correspond bien au chunk retourné).
   * Métriques affichées et correctes (comparées manuellement à un calcul de référence une fois).
   * Aucune erreur de sérialisation lors des tests manuels de l'UI.