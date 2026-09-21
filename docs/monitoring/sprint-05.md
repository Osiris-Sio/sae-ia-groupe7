#### Sprint 5 : Finitions, Dataset de Démo & Préparation à l'Évaluation

* User Stories :
   * US 1.5.1 : En tant qu'équipe, nous finalisons `data/demo/` avec un jeu de fichiers propre et représentatif (au moins 2-3 fichiers par format), nettoyé de tout contenu inutile.
   * US 1.5.2 : En tant qu'utilisateur, je peux filtrer ma recherche par extension et/ou par dossier de départ (fonctionnalité bonus si le temps le permet).
   * US 1.5.3 : En tant qu'équipe, nous rédigeons un README complet : installation, configuration (`.env`), lancement (sans Docker, donc instructions Python explicites : venv, `pip install -r requirements.txt`, commande de démarrage), modèles utilisés, architecture, membres du projet et répartition des rôles.
   * US 1.5.4 : En tant qu'équipe, nous préparons une démonstration reproductible de l'exemple comparatif du sujet ("modalités d'absence aux examens") pour l'oral/l'évaluation.
   * US 1.5.5 : En tant qu'équipe, nous vérifions que chaque membre peut expliquer n'importe quelle ligne de code de sa partie, en particulier les choix d'algorithme (chunking, scoring, prompt de synthèse).
   * US 1.5.6 : En tant qu'équipe, nous faisons une revue croisée du code (chacun relit une partie qu'il n'a pas écrite) pour repérer les zones fragiles avant l'évaluation.

* Livrables / DoR & DoD :
   * Dataset de démo final committé, testé par une personne qui n'a pas participé à sa création (vérifie qu'il tourne "à froid").
   * README suffisant pour qu'une personne extérieure lance le projet sans aide orale.
   * Démonstration de l'exemple comparatif fonctionnelle et chronométrée (savoir combien de temps ça prend en live).
   * Revue de code croisée faite, remarques consignées (même informellement) dans `docs/monitoring/` ou équivalent.
   * Historique Git vérifié : commits réguliers tout au long du projet, pas de gros commit final unique.