# Architecture du projet - Recherche Sémantique de Documents

## 1. Présentation et Objectifs

Ce projet a pour objectif d'explorer et rechercher des informations directement **au cœur des contenus de fichiers et répertoires**, dépassant les limites d'une simple recherche par titre.

L'application repose sur :
- **Une recherche sémantique** : Vectorisation des contenus via **EmbeddingGemma** et indexation vectorielle avec **ChromaDB**.
- **Une interface graphique** : Développée avec **Gradio** pour une interaction simple et dynamique.
- **Des modèles d'IA locaux** : Communication via **Ollama** pour l'extraction vectorielle et le traitement du langage naturel (**Gemma 4 12B**).

---

## 2. Architecture Globale

L'application est découpée en couches indépendantes :

```text
[ Utilisateur ]
       │
       ▼
┌──────────────┐
│  ui_gradio   │  <-- Interface graphique utilisateur
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   service/   │  <-- Logique métier (orchestration de l'indexation & recherche)
└──────┬───────┘
       ├────────────────────────┐
       ▼                        ▼
┌──────────────┐         ┌──────────────┐
│ ollama_client│         │   storage/   │
└──────┬───────┘         └──────┬───────┘
       │                        │
       ▼                        ▼
[ EmbeddingGemma / LLM ]   [ ChromaDB ]
```

---

## 3. Structure du Projet (`src/`)

```text
src/
├── recherche_fichiers/
│   ├── service/
│   │   ├── __init__.py
│   │   ├── core.py          # Logique principale : indexation, requêtes, coordination
│   │   └── utils.py         # Fonctions utilitaires : contrôle fichiers, nettoyage texte, chemins
│   ├── storage/
│   │   ├── __init__.py
│   │   └── base.py          # Gestion de la base vectorielle ChromaDB
│   ├── ollama_client/
│   │   ├── __init__.py
│   │   ├── base.py          # Connecteur générique de communication Ollama
│   │   ├── embedding.py     # Génération d'embeddings avec EmbeddingGemma
│   │   ├── llm.py           # Inférence LLM avec Gemma 4 12B
│   │   └── vlm.py           # Modèle multimodal vision (Qwen3-VL, prévu pour évolution)
│   ├── ui_gradio.py         # Point d'entrée de l'interface utilisateur Gradio
│   └── config.py            # Centralisation des paramètres et constantes
└── shared/
    └── logging.py           # Configuration partagée des logs
```

### Détail des composants

| Composant | Fichier(s) | Rôle |
| :--- | :--- | :--- |
| **Service** | `core.py`, `utils.py` | Orchestre la recherche et l'indexation, fait le lien entre l'UI, le stockage et Ollama, et fournit les fonctions utilitaires (vérification de fichiers, parsing, chunking). |
| **Storage** | `base.py` | Encapsule l'accès à **ChromaDB**. Stocke les vecteurs et métadonnées associées et réalise la recherche par similarité. *(SQLite et FTS5 ne sont pas nécessaires en v1, envisageables pour du full-text ou hybride ultérieurement).* |
| **Ollama Client** | `base.py`, `embedding.py`, `llm.py`, `vlm.py` | Gère les requêtes vers le serveur Ollama pour transformer les textes en vecteurs, appeler le LLM pour la reformulation/synthèse, ou traiter des images à terme. |
| **Interface** | `ui_gradio.py` | Interface utilisateur permettant de sélectionner un dossier, saisir une requête et consulter les résultats pertinents. Délègue toute la logique au package `service/`. |
| **Configuration** | `config.py` | Regroupe les paramètres globaux (adresses, modèles, seuils). |
| **Shared** | `logging.py` | Assure une traçabilité homogène dans toute l'application. |

---

## 4. Flux de Traitement

### 4.1. Indexation
```text
Fichiers sources 
  ──> Lecture du contenu 
  ──> Découpage en morceaux (chunking) 
  ──> EmbeddingGemma (génération des vecteurs) 
  ──> ChromaDB (enregistrement vecteurs + métadonnées : nom, chemin)
```

### 4.2. Recherche
```text
Requête utilisateur (Gradio)
  ──> EmbeddingGemma (vectorisation de la requête)
  ──> ChromaDB (recherche par similarité / plus proches voisins)
  ──> Extraction des résultats les plus pertinents (Top-K)
  ──> Affichage dans l'interface Gradio
```

---

## 5. Modèles d'Intelligence Artificielle

- **EmbeddingGemma** *(Rôle principal)* : Transforme le texte (documents et requêtes) en vecteurs numériques pour permettre la comparaison sémantique.
- **Gemma 4 12B** *(LLM complémentaire)* : Prévu pour reformuler des requêtes vagues, assister l'organisation des résultats, regrouper des contenus par thème ou générer des synthèses.
- **Qwen3-VL** *(VLM optionnel)* : Modèle de vision réservé pour de futures évolutions (analyse d'images ou de documents scannés).

---

## 6. Configuration (`config.py`)

Les paramètres clés de l'application sont isolés dans `config.py` :

```python
OLLAMA_URL = "http://serveur-ollama:11434"

EMBEDDING_MODEL = "embeddinggemma"
LLM_MODEL = "gemma4:12b"

TOP_K = 5  # Nombre de résultats retournés à l'utilisateur
```

---

## 7. Choix Techniques

- **Python** : Langage de référence pour l'écosystème IA et manipulation de données.
- **Gradio** : Prototypage rapide d'interface web réactive et intuitive.
- **Ollama** : Serveur d'inférence local assurant l'exécution des modèles sans dépendance cloud.
- **ChromaDB** : Base vectorielle légère, intégrée et performante pour la recherche de similarité.
- **Déploiement** : Exécution directe en environnement Python standard (Docker non requis pour la v1).

---

## 8. Évolutions Possibles (Roadmap)

- **Filtres avancés** : Recherche ciblée par extension de fichier (`.py`, `.pdf`, `.md`, etc.) ou par sous-répertoire.
- **Recherche hybride** : Combinaison de la recherche sémantique (vecteurs) et lexicale (mots-clés / FTS5 / BM25).
- **Traitement documentaire avancé (Niveau 2)** :
  - Regroupement automatique d'exercices ou sujets de TD par thématique.
  - Analyse comparative de développements de code pour cibler la version la plus fonctionnelle.
  - Synthèse automatique de documents à partir des résultats.
- **Multimodalité** : Intégration de Qwen3-VL pour l'indexation de documents visuels et PDF scannés.