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
[ EmbeddingGemma / LLM ]   [ ChromaDB & SQLite FTS5 ]
```

---

## 3. Structure du Projet

```text
src/
├── recherche_fichiers/
│   ├── service/
│   │   ├── __init__.py
│   │   ├── core.py          # Logique principale : indexation multi-stores, search_mixed, RRF
│   │   └── utils.py         # Fonctions utilitaires : parsers multi-formats (PDF, DOCX, CSV, TXT), chunking
│   ├── storage/
│   │   ├── __init__.py
│   │   └── base.py          # VectorStore (ChromaDB) et LexicalStore (SQLite FTS5 + BM25)
│   ├── ollama_client/
│   │   ├── __init__.py
│   │   ├── base.py          # Connecteur générique de communication Ollama
│   │   ├── embedding.py     # Génération d'embeddings avec EmbeddingGemma
│   │   ├── llm.py           # Inférence LLM avec Gemma 4 12B (reformulation, synthèse, thèmes)
│   │   └── vlm.py           # Modèle multimodal vision (Qwen3-VL, prévu pour évolution)
│   ├── ui_gradio.py         # Point d'entrée Gradio avec sélection de mode (Hybride, Vectoriel, Lexical)
│   └── config.py            # Centralisation des paramètres et constantes
└── shared/
    └── logging.py           # Configuration partagée des logs

tests/                       # 92 tests automatiques
├── ollama/                  # Tests unitaires du client Ollama (base, embedding, llm)
├── storage/                 # Tests unitaires de VectorStore et LexicalStore
└── service/                 # Tests unitaires du service core, utils et validation de recherche
```

### Détail des composants

| Composant         | Fichier(s)                                    | Rôle                                                                                                                                                                                                                                                                                                                                           |
| :---------------- | :-------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Service**       | `core.py`, `utils.py`                         | Orchestre la recherche et l'indexation simultanée. Implémente le moteur unifié `search_mixed()` supportant 3 modes (vectoriel, lexical, hybride RRF). Fournit l'extraction multi-formats (`pdfplumber`, `python-docx`, `pandas`) et le découpage en fragments (_chunks_).                                                                      |
| **Storage**       | `base.py`                                     | Encapsule les deux moteurs de stockage avec une API harmonisée :<br>- **VectorStore** : persistance et recherche de similarité vectorielle via **ChromaDB**.<br>- **LexicalStore** : table `documents` et table virtuelle `chunks_fts` via **SQLite FTS5** avec calcul de score **BM25**. Les deux partagent strictement les mêmes `chunk_id`. |
| **Ollama Client** | `base.py`, `embedding.py`, `llm.py`, `vlm.py` | Gère les requêtes asynchrones vers le serveur Ollama pour transformer les textes en vecteurs numériques (EmbeddingGemma) et exploiter le LLM pour des fonctionnalités cognitives (Gemma 4 12B).                                                                                                                                                |
| **Interface**     | `ui_gradio.py`                                | Interface utilisateur web (Gradio) permettant de saisir une requête, de choisir le mode via un composant `gr.Radio` et de visualiser les résultats JSON formatés.                                                                                                                                                                              |
| **Configuration** | `config.py`                                   | Regroupe les paramètres globaux (adresses, modèles, seuils, chemins de persistance).                                                                                                                                                                                                                                                           |
| **Shared**        | `logging.py`                                  | Assure une traçabilité homogène dans toute l'application.                                                                                                                                                                                                                                                                                      |

---

## 4. Flux de Traitement

### 4.1. Indexation Multi-Stores

```text
Fichiers sources (.txt, .md, .pdf, .docx, .csv)
  ──> Extraction du texte selon le format (utils.py)
  ──> Découpage en fragments avec recouvrement (chunking)
  ──> Génération d'un identifiant stable (chunk_id = f"{doc_id}_{index}")
  ──> EmbeddingGemma (calcul du vecteur de dimension 768)
  ──> Écriture synchronisée :
        ├── VectorStore : ChromaDB (vecteurs, documents, métadonnées)
        └── LexicalStore : SQLite FTS5 (texte brut indexé pour BM25)
```

### 4.2. Recherche et Fusion Hybride

```text
Requête utilisateur (Gradio : query + mode)
  ──> [Mode Vectoriel]  : embedding(query) ──> ChromaDB (cosine distance)
  ──> [Mode Lexical]    : query ──> SQLite FTS5 (BM25 ranking)
  ──> [Mode Hybride]    : exécution parallèle (Vectoriel + Lexical)
                          ──> Algorithme RRF (Reciprocal Rank Fusion : score = 1/(60 + rang))
                          ──> Tri combiné et extraction du Top-K
  ──> Affichage dans l'interface Gradio
```

### 4.3. Contrat de Données Commun (Schéma de Chunk)

Chaque fragment documentaire extrait et indexé respecte la structure commune partagée entre les couches `service` et `storage` :

| Champ         | Type  | Description                                                      |
| :------------ | :---- | :--------------------------------------------------------------- |
| `chunk_id`    | `str` | Identifiant unique du morceau (`{document_id}_{chunk_index}`)    |
| `document_id` | `str` | Identifiant du document source (nom normalisé ou hash)           |
| `content`     | `str` | Contenu textuel du fragment                                      |
| `source_path` | `str` | Chemin d'accès vers le fichier source sur le disque              |
| `format`      | `str` | Extension du document source (`txt`, `md`, `pdf`, `docx`, `csv`) |
| `chunk_index` | `int` | Indice séquentiel du fragment dans le document d'origine         |

---

## 5. Modèles d'Intelligence Artificielle

- **EmbeddingGemma** _(Rôle principal)_ : Transforme le texte (documents et requêtes) en vecteurs numériques (768 dimensions) pour permettre la comparaison sémantique.
- **Gemma 4 12B** _(LLM complémentaire)_ : Prévu pour reformuler des requêtes vagues, assister l'organisation des résultats, regrouper des contenus par thème ou générer des synthèses.
- **Qwen3-VL** _(VLM optionnel)_ : Modèle de vision réservé pour de futures évolutions (analyse d'images ou de documents scannés).

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

- **Python** : Version 3.11 sous Windows 11 pour l'écosystème IA et manipulation de données.
- **SQLite 3 (v3.45.1) + FTS5** : Base de données relationnelle légère et intégrée avec table virtuelle FTS5 pour la recherche plein texte et scoring BM25.
- **ChromaDB** : Base vectorielle intégrée pour le stockage et la recherche de similarité par embeddings.
- **Gradio** : Prototypage d'interface web réactive avec sélecteur dynamique de mode.
- **Ollama** : Serveur d'inférence local assurant l'exécution des modèles sans dépendance cloud.
- **Parsers documentaires** : `pdfplumber` (PDF), `python-docx` (Word), `pandas` (CSV).

---

## 8. Évolutions Possibles (Roadmap)

- **Filtres avancés (Sprint 3)** : Recherche ciblée par extension de fichier (`.pdf`, `.docx`, etc.) ou par sous-répertoire.
- **Re-ranking (Sprint 3)** : Réordonnancement fin des candidats après fusion RRF à l'aide d'un cross-encoder.
- **Traitement documentaire avancé (Niveau 2)** :
  - Regroupement automatique d'exercices ou sujets de TD par thématique.
  - Analyse comparative de développements de code pour cibler la version la plus fonctionnelle.
  - Synthèse automatique de documents à partir des résultats.
- **Multimodalité** : Intégration de Qwen3-VL pour l'indexation de documents visuels et PDF scannés.
