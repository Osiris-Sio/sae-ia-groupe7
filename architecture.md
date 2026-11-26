# Architecture du projet - Recherche Sémantique de Documents

## 1. Présentation et Objectifs

Ce projet a pour objectif d'explorer et rechercher des informations directement **au cœur des contenus de fichiers et répertoires**, dépassant les limites d'une simple recherche par titre.

L'application repose sur :

- **Une recherche sémantique** : Vectorisation des contenus via **EmbeddingGemma** et indexation vectorielle avec **ChromaDB**.
- **Une recherche lexicale** : Indexation rapide via **SQLite FTS5** et scoring **BM25**.
- **Une fusion hybride** : Combinaison des résultats via l'algorithme **RRF** (_Reciprocal Rank Fusion_).
- **Une synthèse documentaire (RAG)** : Résumé et descriptions sourcés via **LLM configurable (par exemple : Gemma 2)**.
- **Une interface graphique** : Développée avec **Gradio** pour comparer les modes en direct avec surlignage des termes clés.
- **Des modèles d'IA locaux** : Communication asynchrone via **Ollama**.

---

## 2. Architecture Globale

L'application est découpée en couches indépendantes :

```text
[ Utilisateur ]
       │
       ▼
┌──────────────┐
│  ui_gradio   │  <-- Interface graphique utilisateur (comparaison de modes & surlignage)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   service/   │  <-- Logique métier (indexation, search_mixed, RRF, synthesize)
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
│   │   ├── core.py          # Logique principale : indexation multi-stores, search_mixed, RRF, synthesize
│   │   └── utils.py         # Fonctions utilitaires : parsers multi-formats (NB, XML, XLSX, PDF, DOCX, CSV, TXT), chunking
│   ├── storage/
│   │   ├── __init__.py
│   │   └── base.py          # VectorStore (ChromaDB) et LexicalStore (SQLite FTS5 + BM25)
│   ├── ollama_client/
│   │   ├── __init__.py
│   │   ├── base.py          # Connecteur générique de communication Ollama
│   │   ├── embedding.py     # Génération d'embeddings avec EmbeddingGemma
│   │   ├── llm.py           # Inférence LLM (reformulation, synthèse, thèmes)
│   │   └── vlm.py           # Modèle multimodal vision (Qwen3-VL, prévu pour évolution)
│   ├── ui_gradio.py         # Point d'entrée Gradio (sélection multi-modes, tableaux, surlignage, descriptions LLM)
│   └── config.py            # Centralisation des paramètres et constantes
└── shared/
    └── logging.py           # Configuration partagée des logs

tests/                       # 117 tests automatiques
├── test_ui_gradio.py        # Tests unitaires de l'interface Gradio et du surlignage
├── ollama/                  # Tests unitaires du client Ollama (base, embedding, llm, synthèse)
├── storage/                 # Tests unitaires de VectorStore et LexicalStore
└── service/                 # Tests unitaires du core, utils, recherche et synthèse
```

### Détail des composants

| Composant         | Fichier(s)                                    | Rôle                                                                                                                                                                                                                                                                                                                   |
| :---------------- | :-------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Service**       | `core.py`, `utils.py`                         | Orchestre la recherche et l'indexation simultanée. Implémente le moteur unifié `search_mixed()` (vectoriel, lexical, hybride RRF), l'extraction multi-formats (`pdfplumber`, `python-docx`, `pandas`, `xml.etree.ElementTree`, `openpyxl`), le découpage en fragments (_chunks_), et la synthèse documentaire `synthesize()`. |
| **Storage**       | `base.py`                                     | Encapsule les deux moteurs de stockage :<br>- **VectorStore** : persistance et recherche de similarité vectorielle via **ChromaDB**.<br>- **LexicalStore** : table `documents` et table virtuelle `chunks_fts` via **SQLite FTS5** avec calcul de score **BM25**. Les deux partagent strictement les mêmes `chunk_id`. |
| **Ollama Client** | `base.py`, `embedding.py`, `llm.py`, `vlm.py` | Gère les requêtes asynchrones vers le serveur Ollama pour transformer les textes en vecteurs numériques (EmbeddingGemma) et exploiter le LLM pour des fonctionnalités cognitives (synthèse, reformulation, descriptions).                                                                                              |
| **Interface**     | `ui_gradio.py`                                | Interface utilisateur web (Gradio) permettant de saisir une requête, de sélectionner un ou plusieurs modes de recherche, d'afficher les résultats avec surlignage des mots-clés et de générer des descriptions LLM.                                                                                                    |
| **Configuration** | `config.py`                                   | Regroupe les paramètres globaux (adresses, modèles, seuils, chemins de persistance).                                                                                                                                                                                                                                   |
| **Shared**        | `logging.py`                                  | Assure une traçabilité homogène dans toute l'application.                                                                                                                                                                                                                                                              |

---

## 4. Flux de Traitement

### 4.1. Indexation Multi-Stores

```text
Fichiers sources (.txt, .nb, .md, .pdf, .docx, .csv, .xml, .xlsx)
  ──> Extraction du texte selon le format (utils.py)
        ├── .txt / .nb / .md : lecture du texte UTF-8
        ├── .xml : extraction des nœuds texte
        └── .xlsx : lecture des cellules de toutes les feuilles
  ──> Découpage en fragments avec recouvrement (chunking)
  ──> Génération d'un identifiant stable (chunk_id = f"{doc_id}_{index}")
  ──> EmbeddingGemma (calcul du vecteur de dimension 768)
  ──> Écriture synchronisée :
        ├── VectorStore : ChromaDB (vecteurs, documents, métadonnées)
        └── LexicalStore : SQLite FTS5 (texte brut indexé pour BM25)
```

### 4.2. Recherche et Fusion Hybride

```text
Requête utilisateur (Gradio : query + modes sélectionnés)
  ──> [Mode Vectoriel]  : embedding(query) ──> ChromaDB (cosine distance)
  ──> [Mode Lexical]    : query ──> SQLite FTS5 (BM25 ranking)
  ──> [Mode Hybride]    : exécution parallèle (Vectoriel + Lexical)
                          ──> Algorithme RRF (Reciprocal Rank Fusion : score = 1/(60 + rang))
                          ──> Tri combiné et extraction du Top-K
  ──> Affichage dans l'interface Gradio (avec surlignage des termes clés et option synthèse LLM)
```

### 4.3. Contrat de Données Commun (Schéma de Chunk)

Chaque fragment documentaire extrait et indexé respecte la structure commune partagée entre les couches `service` et `storage` :

| Champ         | Type  | Description                                                      |
| :------------ | :---- | :--------------------------------------------------------------- |
| `chunk_id`    | `str` | Identifiant unique du morceau (`{document_id}_{chunk_index}`)    |
| `document_id` | `str` | Identifiant du document source (nom normalisé ou hash)           |
| `content`     | `str` | Contenu textuel du fragment                                      |
| `source_path` | `str` | Chemin d'accès vers le fichier source sur le disque              |
| `format`      | `str` | Extension du document source (`txt`, `nb`, `md`, `pdf`, `docx`, `csv`, `xml`, `xlsx`) |
| `chunk_index` | `int` | Indice séquentiel du fragment dans le document d'origine         |

---

## 5. Modèles d'Intelligence Artificielle

- **EmbeddingGemma** _(Rôle principal)_ : Transforme le texte (documents et requêtes) en vecteurs numériques (768 dimensions) pour permettre la comparaison sémantique.
- **Gemma 2 2B / Gemma 4 12B** _(LLM complémentaire)_ : Utilisé pour la synthèse documentaire (`synthesize`), la reformulation et les descriptions de documents.
- **Qwen3-VL** _(VLM optionnel)_ : Modèle de vision réservé pour de futures évolutions (analyse d'images ou de documents scannés).

---

## 6. Configuration (`config.py`)

Les paramètres de l'application sont centralisés et validés via `pydantic-settings` (`Settings` et l'instance `settings`) dans `config.py`, avec surcharge possible par variables d'environnement ou fichier `.env`. Par défaut, `supported_formats` inclut `.nb`, `.xml` et `.xlsx`; une valeur `SUPPORTED_FORMATS` définie dans `.env` remplace la liste par défaut :

```python
from recherche_fichiers.config import settings

# Exemples d'accès via `settings`
settings.ollama_url
settings.embedding_model
settings.embedding_dim
settings.llm_model
settings.vlm_model
settings.top_k
settings.chunk_size
settings.chunk_overlap
settings.chroma_persist_path
settings.supported_formats
```

---

## 7. Choix Techniques

- **Python** : Version 3.11 sous Windows 11 pour l'écosystème IA et manipulation de données.
- **SQLite 3 (v3.45.1) + FTS5** : Base de données relationnelle légère et intégrée avec table virtuelle FTS5 pour la recherche plein texte et scoring BM25.
- **ChromaDB** : Base vectorielle intégrée pour le stockage et la recherche de similarité par embeddings.
- **Gradio** : Prototypage d'interface web réactive avec sélection multi-modes et surlignage.
- **Ollama** : Serveur d'inférence local assurant l'exécution des modèles sans dépendance cloud.
- **Parsers documentaires** : `pdfplumber` (PDF), `python-docx` (Word), `pandas` (CSV), `xml.etree.ElementTree` (XML) et `openpyxl` (Excel). Les fichiers `.nb` sont lus comme du texte UTF-8.

---

## 8. Évolutions Possibles (Roadmap)

- 🟢 **Sprint 3 (Validé)** : Synthèse documentaire (`synthesize()`), interface comparative avec surlignage, descriptions LLM et 109 tests unitaires.
- 🟢 **Sprint 4 (Validé)** : Robustesse face aux pannes Ollama/JSON/timeouts, configuration externalisée (`pydantic-settings` + `.env`), URLs dédiées Embedding/LLM et **117 tests automatiques**.
- 🟡 **Sprint 5 (En cours)** : US 1.5.7 terminée (recherche dans les fichiers `.nb`, `.xml` et `.xlsx`) ; finitions du dataset `data/demo/`, filtrage par extension/dossier (bonus), préparation de la démonstration reproductible et revue de code croisée.
- ⚪ **Évolutions futures** : Re-ranking par cross-encoder, filtres avancés par sous-dossier / extension, et multimodalité (Qwen3-VL).
