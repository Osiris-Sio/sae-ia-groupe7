#### Sprint 5 : Finitions et Améliorations de l'Application

- User Stories :
  - US 1.5.1 : En tant qu'équipe, nous finalisons `data/demo/` avec un jeu de fichiers réels, propre et représentatif (au moins 2-3 fichiers par format), nettoyé de tout contenu inutile.
  - US 1.5.2 : En tant qu'utilisateur, je peux filtrer ma recherche par extension et/ou par dossier de départ.
  - US 1.5.3 : En tant qu'utilisateur, je dispose d'une interface Gradio responsive et adaptée aux différentes tailles d'écran sur PC, afin d'éviter les problèmes d'affichage lorsque la fenêtre est trop petite.
  - US 1.5.4 : En tant qu'utilisateur, je peux utiliser une version exécutable `.exe` de l'application afin de pouvoir la lancer plus facilement sans passer par une commande Python.
  - US 1.5.5 : En tant qu'utilisateur, si aucune base de données n'est disponible, je peux sélectionner un dossier contenant les fichiers à indexer afin de créer la base de données.
  - US 1.5.6 : En tant qu'utilisateur, je peux modifier les paramètres directement depuis l'application, notamment reconstruire la base de données (relancer l'indexation) et modifier les paramètres actuellement définis dans le fichier `.env`.
  - US 1.5.7 : En tant qu'utilisateur, je peux effectuer des recherches dans de nouveaux formats de fichiers, notamment .np, .xml et .xlsx.
  - US 1.5.8 : En tant qu'utilisateur, je peux exploiter le contenu visuel de mes documents grâce à l'intégration d'un VLM (Vision Language Model).

- Livrables / DoR & DoD :
  - Dataset de démo final committé, testé par une personne qui n'a pas participé à sa création (vérifie qu'il tourne "à froid").
  - Interface Gradio adaptée aux différentes tailles de fenêtre sur PC.
  - Application exécutable en `.exe` et testée.
  - En l'absence de base de données, possibilité de sélectionner un dossier et de lancer l'indexation.
  - Paramètres modifiables directement depuis l'application et possibilité de reconstruire la base de données.
  - Nouveaux formats de fichiers pris en charge et testés.
  - VLM intégré et testé sur des documents contenant des éléments visuels.
  - Fonctionnalité de filtrage testée.
  - README suffisant pour qu'une personne extérieure lance le projet sans aide orale et sans terminal .
  - Démonstration de l'exemple comparatif fonctionnelle et chronométrée (savoir combien de temps ça prend en live).
  - Revue de code croisée faite, remarques consignées (même informellement) dans `docs/monitoring/` ou équivalent.
  - Historique Git vérifié : commits réguliers tout au long du projet, pas de gros commit final unique.
