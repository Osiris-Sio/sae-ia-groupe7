#### Sprint 4 : Robustesse, Résilience & Modularité

* User Stories :
   * US 1.4.1 : En tant que développeur, je gère proprement dans `ollama_client/base.py` les cas Ollama indisponible, timeout, et réponse JSON malformée (exceptions typées, jamais de crash silencieux).
   * US 1.4.2 : En tant qu'utilisateur, je vois un message clair (`gr.Error()` / `gr.Warning()`) si le serveur Ollama ne répond pas ou si ma requête dépasse la fenêtre de contexte.
   * US 1.4.3 : En tant que développeur, j'utilise `gr.update()` pour désactiver le bouton "Rechercher" pendant le traitement, afin d'éviter les doubles envois.
   * US 1.4.4 : En tant que développeur, j'externalise tous les paramètres (URL Ollama, noms de modèles, chemins, `k` par défaut) dans `config.py` via `pydantic-settings`, aucun hardcoding restant.
   * US 1.4.5 : En tant qu'équipe, nous vérifions que remplacer `gemma4:12b` par un autre modèle ne demande de modifier que `config.py` (test de résilience type "évaluation surprise").
   * US 1.4.6 : En tant qu'équipe, nous complétons `tests/` avec des tests d'intégration (pipeline complet ingestion → recherche → synthèse) en plus des tests unitaires existants.
   * US 1.4.7 : En tant qu'équipe, nous mettons à jour la documentation technique (architecture, schéma des deux bases, guide d'installation) dans le dépôt Git, en continu.

* Livrables / DoR & DoD :
   * Simulation d'un Ollama down (arrêt du serveur) : l'UI affiche une erreur propre, pas de crash du process.
   * Changement de modèle testé en conditions réelles (chronométré, doit rester faisable en ~15 min).
   * `config.py` revu par toute l'équipe, zéro valeur en dur retrouvée dans une recherche du code (`grep` sur les IP/noms de modèles).
   * Au moins un test d'intégration de bout en bout qui passe (`pytest tests/`).
   * README et doc architecture à jour, reflétant l'état réel du code (pas l'état prévu au départ).