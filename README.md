# 🔍 Moteur de Recherche Documentaire Hybride (Lexical & Sémantique)

> **SAE S5 - Application IA** | BUT Informatique (3ᵉ année, 2026 - 2027)  
> **IUT de Calais - Université du Littoral Côte d'Opale**

---

## 👥 Équipe & Encadrement

- **Étudiants (TPC) :**
  - Louis AMEDRO (_Osiris Sio_) - Responsable
  - Noé COLIN (_Kiizer861_)
  - Valentin MINNEBO (_Jonedeuf_)
- **Enseignants référents :**
  - M. COZOT
  - Mme PACOU

---

## 📌 Présentation & Objectifs

Ce projet permet de retrouver des informations directement **au cœur des documents** (`.pdf`, `.docx`, `.md`, `.txt`, `.csv`), puis d'en générer une synthèse structurée et sourcée via un modèle de langage (LLM).

Chaque méthode de recherche a ses forces et ses limites :

- **Recherche par mots-clés (lexicale) :** très rapide pour trouver un mot exact, mais ne comprend pas les synonymes ni les phrases naturelles.
- **Recherche par le sens (sémantique avec IA) :** comprend le sens général de la question, mais peut manquer de précision sur du code ou des termes très précis.

**Le but du projet :** combiner les deux approches et comparer leurs résultats en direct dans une interface web simple (**Gradio**).

---

## 🌐 Explorer le Projet en Ligne

Vous pouvez inspecter, visualiser et explorer l'intégralité de ce dépôt via ces outils en ligne :

- 📦 **[GitIngest](https://gitingest.com/Osiris-Sio/sae-ia-groupe7)** : Analyser et formater l'intégralité du code pour les LLM / IA.
- 💻 **[GitHub1s](https://github1s.com/Osiris-Sio/sae-ia-groupe7)** : Parcourir le code dans un éditeur VS Code directement dans votre navigateur.
- 📊 **[GitDiagram](https://gitdiagram.com/osiris-sio/sae-ia-groupe7)** : Visualiser interactivement l'architecture du projet sous forme de diagramme.

---

## 🗺️ État d'Avancement des Sprints

- 🟢 **Sprint 0 (Organisation & Cadrage) :** Cahier des charges, architecture du code et planning validés.
- 🟢 **Sprint 1 (Socle Ollama & Premier Pipeline Vectoriel) :**
  - Connexion locale à Ollama (`base.py`, `embedding.py`, `llm.py`).
  - Transformation du texte en vecteurs avec **EmbeddingGemma**.
  - Sauvegarde et recherche des vecteurs avec **ChromaDB** (`storage/base.py`).
  - Découpage et recherche dans les fichiers texte (`service/core.py`).
  - Interface graphique dans le navigateur (**Gradio**).
  - Fichiers d'exemple pour tester (`data/demo/`).
  - **66 tests automatiques** initiaux.
- 🟢 **Sprint 2 (Index Lexical & Extraction Multi-formats) :**
  - Indexation lexicale avec **SQLite FTS5** et scoring **BM25** (`storage/base.py`).
  - Extraction multi-formats : **PDF** (`pdfplumber`), **Word** (`python-docx`), **CSV** (`pandas`), en plus de `.txt` et `.md` (`service/utils.py`).
  - Synchronisation stricte des `chunk_id` entre ChromaDB et SQLite (`service/core.py`).
  - Moteur de recherche unifié `search_mixed()` avec 3 modes (Vectoriel, Lexical, Hybride avec algorithme RRF).
  - Sélection multiple des modes de recherche dans l'interface Gradio (`ui_gradio.py`), avec affichage vertical des seuls modes sélectionnés.
  - Dataset de démonstration complet dans `data/demo/` couvrant les 5 formats.
  - **94 tests automatiques** organisés en sous-dossiers.
- 🟢 **Sprint 3 (Synthèse Gemma4, Citations & Interface Comparative) :**
  - Synthèse de documents avec citations des sources (`synthesize()` dans `service/core.py`).
  - Sélection multi-modes dans l'interface Gradio (`ui_gradio.py`), avec affichage comparatif des résultats.
  - Surlignage dynamique des termes recherchés dans les extraits.
  - Option de description/résumé par LLM pour chaque document retourné.
  - Métriques d'inférence en direct (temps d'exécution, débit de génération en tokens/s, scores bruts).
  - **109 tests automatiques** unitaires et d'intégration (avec `tests/test_ui_gradio.py`).
- 🟡 **Sprint 4 (À venir) :** Robustesse, résilience face aux pannes Ollama et configuration externalisée.

---

## 🚀 Démarrage Rapide (En 3 étapes)

### 1. Prérequis

> ⚠️ **Environnement testé :** Le projet a été développé et testé uniquement sous **Windows 11** (avec PowerShell). Nous n'avons pas testé sur d'autres systèmes (Linux, macOS, etc.).

- Système : **Windows 11**.
- Avoir **Python 3.11** installé.
- Avoir **[Ollama](https://ollama.com/)** installé et lancé.

Téléchargez les modèles d'IA nécessaires :

```bash
ollama pull embeddinggemma

ollama pull gemma2:2b
```

### 2. Installer les dépendances

Dans votre terminal PowerShell, lancez simplement :

```powershell
py -3.11 -m pip install -r requirements.txt
```

### 3. Lancer l'application

```powershell
# Attention, tout doit être effacé avant de lancer l'indexation
Remove-Item -Recurse -Force data/chroma, data/lexical.db
```

```powershell
# Étape A : Analyser les fichiers d'exemple (indexation simultanée ChromaDB & SQLite)
py -3.11 src/recherche_fichiers/service/core.py data/demo

# Étape B : Ouvrir l'application web
py -3.11 src/recherche_fichiers/ui_gradio.py
```

L'application s'ouvre dans votre navigateur à l'adresse : **http://127.0.0.1:7860**. Vous pouvez y sélectionner un ou plusieurs modes (**Hybride**, **Vectoriel** et/ou **Lexical**) pour comparer leurs résultats, avec surlignage des termes et descriptions LLM.

---

## 🧪 Lancer les Tests

Les tests vérifient automatiquement le code en moins d'une seconde, sans avoir besoin d'allumer Ollama :

```powershell
# Lancer tous les tests (109 tests unitaires et d'intégration)
py -3.11 -m unittest discover tests
```

Pour tester une partie précise :

```powershell
# Module Interface Gradio (surlignage, formatage, recherche)
py -3.11 tests/test_ui_gradio.py

# Module Ollama (connexion, embeddings, LLM, synthèse)
py -3.11 tests/ollama/test_ollama.py
py -3.11 tests/ollama/test_embedding.py
py -3.11 tests/ollama/test_llm.py

# Module Stockage (ChromaDB vectoriel & SQLite FTS5 lexical)
py -3.11 tests/storage/test_vector_store.py
py -3.11 tests/storage/test_lexical_store.py

# Module Service & Intégration (Core, parsing multi-formats, recherche hybride, synthèse)
py -3.11 tests/service/test_core.py
py -3.11 tests/service/test_utils.py
py -3.11 tests/service/test_search.py
```

### 🔄 Intégration Continue (CI/CD)

Le projet intègre un pipeline CI/CD complet (automatique et manuel) :

- **Automatique sur GitHub Actions (`.github/workflows/ci.yml`) :**
  - Se déclenche automatiquement à chaque **Push** et **Pull Request** vers les branches `main` et `dev`.
  - Exécute les 109 tests, contrôle la syntaxe et s'assure qu'aucun fichier sensible (bases SQLite/Chroma) n'est commité, sous environnement officiel Windows (`windows-latest` avec PowerShell).
  - Déclenchable également manuellement depuis l'onglet **Actions** de GitHub (_Run workflow_).
- **Manuelle en local avant commit (`scripts/verify.ps1`) :**
  - Exécutez simplement avant de commiter pour tout valider en 1 seconde :
    ```powershell
    .\scripts\verify.ps1
    # ou : py -3.11 scripts/verify.py
    ```
  - _(Optionnel)_ Pour bloquer automatiquement tout commit en cas d'erreur de test, installez le hook Git :
    ```powershell
    .\scripts\install_hook.ps1
    ```

👉 Pour consulter le détail des normes de code, de la stratégie de test et de la CI/CD, voir le guide **[docs/development_quality.md](docs/development_quality.md)**.

---

## 📁 Architecture du Projet

👉 Pour voir le schéma complet et le fonctionnement détaillé du code, consultez le fichier **[architecture.md](architecture.md)**.

```text
sae-ia-groupe7/
├── .github/
│   └── workflows/
│       └── ci.yml           # Pipeline CI/CD GitHub Actions (109 tests auto sur PR et push)
├── data/
│   ├── demo/                # Fichiers d'exemples (.txt, .md, .csv, .docx, .pdf)
│   ├── chroma/              # Base de données vectorielle ChromaDB
│   └── lexical.db           # Base de données lexicale SQLite FTS5 (BM25)
├── docs/
│   ├── development_quality.md # Guide de qualité logicielle, normes de code et CI/CD
│   ├── monitoring/          # Suivi officiel des Sprints (sprint-00 à sprint-05)
│   └── troubleshooting.md   # Guide de dépannage et débogage
├── scripts/
│   ├── verify.ps1           # Script PowerShell de vérification pré-commit locale
│   ├── verify.py            # Script Python multiplateforme de validation des tests
│   └── install_hook.ps1     # Installe le hook Git pre-commit automatique
├── src/
│   └── recherche_fichiers/
│       ├── config.py        # Réglages généraux (adresses, modèles, options)
│       ├── ui_gradio.py     # Interface web utilisateur (multi-modes, surlignage, LLM)
│       ├── service/         # Découpage des textes, parsing, synthèse et recherche
│       │   ├── core.py      # Programme principal (indexation, search_mixed, RRF, synthesize)
│       │   └── utils.py     # Parsers (PDF, DOCX, CSV, TXT), découpage (chunking)
│       ├── storage/         # Sauvegarde et indexation des données
│       │   └── base.py      # VectorStore (ChromaDB) et LexicalStore (SQLite FTS5)
│       └── ollama_client/   # Communication asynchrone avec Ollama
│           ├── base.py      # Client HTTP générique
│           ├── embedding.py # Création des vecteurs (EmbeddingGemma)
│           ├── llm.py       # Fonctions LLM (reformulation, synthèse, thèmes)
│           └── vlm.py       # Modèle vision (prévu pour plus tard)
├── tests/                   # 109 tests automatiques organisés par domaine
│   ├── test_ui_gradio.py    # Tests unitaires de l'interface Gradio et du surlignage
│   ├── ollama/              # Tests unitaires du client Ollama (base, embedding, llm)
│   ├── storage/             # Tests unitaires de VectorStore et LexicalStore
│   └── service/             # Tests unitaires du core, utils et validation de recherche
├── requirements.txt         # Liste des modules Python nécessaires
├── architecture.md          # Explication détaillée de l'architecture
└── README.md
```

---

## ⚙️ Réglages (`config.py`)

Les réglages principaux sont dans `src/recherche_fichiers/config.py` :

| Variable              | Valeur par défaut        | Description                                          |
| :-------------------- | :----------------------- | :--------------------------------------------------- |
| `OLLAMA_URL`          | `http://localhost:11434` | Adresse du serveur Ollama                            |
| `EMBEDDING_MODEL`     | `embeddinggemma`         | Modèle utilisé pour transformer le texte en vecteurs |
| `EMBEDDING_DIM`       | `768`                    | Taille des vecteurs                                  |
| `LLM_MODEL`           | `gemma2:2b`              | Modèle utilisé pour reformuler et résumer            |
| `TOP_K`               | `5`                      | Nombre de résultats affichés par recherche           |
| `CHROMA_PERSIST_PATH` | `data/chroma`            | Dossier où est enregistrée la base de données        |

---

## 🤖 Comment changer de modèle d'IA ?

L'application utilise deux types d'intelligence artificielle :

3. **L'IA de recherche (Embedding)** : convertit le texte en vecteurs pour la recherche sémantique (par défaut : `embeddinggemma`).
4. **L'IA de texte (LLM)** : génère les descriptions unitaires et la synthèse globale RAG (par défaut : `gemma2:2b` ou `llama3.2:3b`).

Le changement de modèle se fait en **3 étapes simples** :

### 1. Télécharger le modèle dans Ollama

Dans votre terminal :

```bash
ollama pull gemma4:12b
# ou pour un autre modèle d'embedding :
ollama pull nomic-embed-text
```

### 2. Indiquer le nouveau modèle (au choix)

#### Option A (Recommandée : sans modifier le code)

Définissez la variable dans votre terminal avant de lancer l'application :

- **PowerShell (Windows) :**
  ```powershell
  $env:LLM_MODEL = "gemma4:12b"
  ```
- **Bash (Linux / macOS) :**
  ```bash
  export LLM_MODEL="gemma4:12b"
  ```

#### Option B (Permanente dans le code)

Dans `src/recherche_fichiers/config.py` :

```python
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:12b")
```

### 3. Lancer l'application

```powershell
py -3.11 -m recherche_fichiers.ui_gradio
```

Au démarrage, l'interface affiche instantanément dans le terminal et sous le titre web les modèles actifs réels.

---

### 🌐 Utiliser un serveur Ollama distant (autre machine / GPU / VM)

Pour déléguer l'inférence à un serveur Ollama distant, **ne mettez pas l'URL dans `LLM_MODEL`** (qui ne sert qu'au nom du modèle), mais utilisez **`OLLAMA_URL`** :

- **En PowerShell :**
  ```powershell
  $env:OLLAMA_URL = "http://192.168.1.50:11434"
  $env:LLM_MODEL = "llama3.2:3b"
  ```
- **Ou dans `src/recherche_fichiers/config.py` :**
  ```python
  OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.1.50:11434")
  LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
  ```

> [!NOTE]
> **Et pour les API externes (OpenAI ChatGPT, Google Gemini, Mistral API) ?**
> Le projet utilise le protocole natif d'Ollama (`/api/generate` et `/api/embed`). Pour brancher directement une API tierce commerciale, il suffit d'utiliser une passerelle compatible Ollama (comme _LiteLLM_ ou _vLLM_) qui traduira les requêtes.

> [!IMPORTANT]
> **Cas particulier du modèle d'embedding (`EMBEDDING_MODEL`) :**
> Si vous changez le modèle d'embedding (ex. `nomic-embed-text`), la dimension vectorielle et les représentations changent. Vous devez vider et ré-indexer les documents :
>
> ```powershell
> Remove-Item -Recurse -Force data/chroma, data/lexical.db
> py -3.11 src/recherche_fichiers/service/core.py data/demo
> ```

---

## 🗄️ Moteur Lexical & Version SQLite

Le moteur de recherche par mots-clés s'appuie sur le moteur **SQLite FTS5** intégré à l'environnement Python 3.11 sous Windows 11 :

- **Version SQLite :** `3.45.1`
- **Extension FTS5 :** Compilée nativement dans la bibliothèque standard (`sqlite3`), activant la table virtuelle `chunks_fts`.
- **Scoring de pertinence :** Algorithme probabiliste **BM25** natif SQLite FTS5.
- **Résilience aux requêtes :** Assainissement automatique des caractères de ponctuation (`?`, `!`, `()`, `:`, etc.) pour garantir des recherches stables sans erreur de syntaxe.

---

## 💡 Démonstration Comparative : Lexical vs Vectoriel vs Hybride

Dans l'interface Gradio (`ui_gradio.py`), vous pouvez cocher les modes à comparer en direct :

### Cas 1 : Requête en langage naturel conceptuel (`"modalités d'absence aux examens"`)

- **Mode Lexical (BM25) :** Cherche strictement les termes exacts `"modalités"`, `"absence"` ou `"examens"`. Si un document administratif formule la consigne avec des synonymes (_"Procédure en cas d'empêchement médical lors des épreuves"_), la recherche lexicale peut passer à côté du document (score nul).
- **Mode Vectoriel (Sémantique) :** Analyse le sens profond. Grâce aux représentations vectorielles d'EmbeddingGemma, il retrouve immédiatement les passages traitant des justificatifs médicaux et dispenses d'épreuves, même sans aucun mot-clé identique.
- **Mode Hybride (RRF) :** Grâce à la fusion par rangs réciproques (**RRF** - _Reciprocal Rank Fusion_), les documents combinant pertinence sémantique et vocabulaire commun sont hissés au premier rang.

### Cas 2 : Requête sur un terme technique ou sigle précis (`"SQL"` ou `"TCP"`)

- **Mode Lexical (BM25) :** Redoutablement précis. Les documents `bdd_sql.txt` ou `reseaux_tcp_ip.txt` remontent instantanément avec une certitude absolue.
- **Mode Vectoriel (Sémantique) :** Peut diluer la recherche en assimilant un sigle très court à des notions informatiques génériques voisines.
- **Mode Hybride (RRF) :** Empêche le "flou" sémantique d'éclipser les fichiers contenant le mot exact.

---

## 📋 Comprendre les Résultats Affichés

L'interface affiche les résultats sous forme de tableau clair :

| Information           | Description                                                                                                                                                                                                                                                                                  |
| :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`Source`**          | Le fichier d'origine (`data/demo/...`).                                                                                                                                                                                                                                                      |
| **`Score`**           | La note de pertinence :<br>• En **Vectoriel** : distance cosinus (plus c'est proche de `0`, plus le sens est proche).<br>• En **Lexical** : score BM25 (plus c'est élevé, plus le mot est important).<br>• En **Hybride** : score RRF combiné (plus c'est élevé, plus le résultat est fort). |
| **`Contenu`**         | L'extrait de texte trouvé, avec surlignage des termes clés de la recherche.                                                                                                                                                                                                                  |
| **`Description LLM`** | _(Optionnel)_ Synthèse unitaire générée par le modèle de langage pour résumer le passage.                                                                                                                                                                                                    |

---

## 🛠️ Dépannage Rapide

| Problème                           | Ce qui se passe                                  | Ce qu'il faut faire                                                |
| :--------------------------------- | :----------------------------------------------- | :----------------------------------------------------------------- |
| `OllamaConnectionError`            | Ollama n'est pas allumé                          | Lancer Ollama sur votre ordinateur ou taper `ollama serve`         |
| `model 'embeddinggemma' not found` | Le modèle n'est pas téléchargé                   | Taper `ollama pull embeddinggemma` dans votre terminal             |
| `ModuleNotFoundError`              | Python ne trouve pas le dossier `src`            | Lancer la commande avec `py -3.11 src/recherche_fichiers/...`      |
| Aucun résultat trouvé              | Les fichiers n'ont pas encore été analysés       | Lancer `py -3.11 src/recherche_fichiers/service/core.py data/demo` |
| Port `7860` déjà utilisé           | L'application tourne déjà dans un autre terminal | Fermer l'autre fenêtre ou changer le numéro de port                |

👉 Pour voir toutes les astuces et solutions détaillées, consultez le **[Guide de Dépannage](docs/troubleshooting.md)**.

---

## 📜 Licence

Ce projet est sous licence **[CC BY-SA 4.0 (Creative Commons Attribution - Partage dans les Mêmes Conditions)](https://creativecommons.org/licenses/by-sa/4.0/)**.
