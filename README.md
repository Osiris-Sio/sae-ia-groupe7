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

Ce projet permet de retrouver des informations directement **au cœur des documents** (`.pdf`, `.docx`, `.md`, `.txt`, `.csv`).

Chaque méthode de recherche a ses forces et ses limites :

- **Recherche par mots-clés (lexicale) :** très rapide pour trouver un mot exact, mais ne comprend pas les synonymes ni les phrases naturelles.
- **Recherche par le sens (sémantique avec IA) :** comprend le sens général de la question, mais peut manquer de précision sur du code ou des termes très précis.

**Le but du projet :** combiner les deux approches et comparer leurs résultats en direct dans une interface web simple (**Gradio**).

---

## 🗺️ État d'Avancement des Sprints

- 🟢 **Sprint 0 (Organisation & Cadrage) :** Cahier des charges, architecture du code et planning validés.
- 🟢 **Sprint 1 (Connexion IA & Première recherche) :**
  - Connexion locale à Ollama (`base.py`, `embedding.py`, `llm.py`).
  - Transformation du texte en vecteurs avec **EmbeddingGemma**.
  - Sauvegarde et recherche des vecteurs avec **ChromaDB** (`storage/base.py`).
  - Découpage et recherche dans les fichiers texte (`service/core.py`).
  - Interface graphique dans le navigateur (**Gradio**).
  - Fichiers d'exemple pour tester (`data/demo/`).
  - **66 tests automatiques** qui valident le bon fonctionnement.
- 🟡 **Sprint 2 (À venir) :** Ajout de la recherche par mots-clés (SQLite FTS5), lecture des PDF, Word et CSV, et fusion des résultats.

---

## 🚀 Démarrage Rapide (En 3 étapes)

### 1. Prérequis

> ⚠️ **Environnement testé :** Le projet a été développé et testé uniquement sous **Windows 11** (avec PowerShell). Nous n'avons pas testé sur d'autres systèmes (Linux, macOS, etc.).

- Système : **Windows 11**.
- Avoir **Python 3.11** installé.
- Avoir **[Ollama](https://ollama.com/)** installé et lancé.

Téléchargez le modèle d'IA pour le texte :

```bash
ollama pull embeddinggemma
```

### 2. Installer les dépendances

Dans votre terminal PowerShell, lancez simplement :

```powershell
py -3.11 -m pip install -r requirements.txt
```

### 3. Lancer l'application

```powershell
# Étape A : Analyser les fichiers d'exemple
py -3.11 src/recherche_fichiers/service/core.py data/demo

# Étape B : Ouvrir l'application web
py -3.11 src/recherche_fichiers/ui_gradio.py
```

L'application s'ouvre dans votre navigateur à l'adresse : **http://127.0.0.1:7860**.

---

## 🧪 Lancer les Tests

Les tests vérifient automatiquement le code en moins d'une seconde, sans avoir besoin d'allumer Ollama :

```powershell
# Lancer tous les tests (66 tests)
py -3.11 -m unittest discover tests
```

Pour tester une partie précise :

```powershell
py -3.11 tests/test_ollama.py     # Connexion au serveur Ollama
py -3.11 tests/test_embedding.py  # Transformation du texte en vecteurs
py -3.11 tests/test_llm.py        # Fonctions du modèle de texte
py -3.11 tests/test_storage.py    # Base de données ChromaDB
py -3.11 tests/test_core.py       # Découpage et recherche de fichiers
```

---

## 📁 Architecture du Projet

👉 Pour voir le schéma complet et le fonctionnement détaillé du code, consultez le fichier **[architecture.md](architecture.md)**.

```text
sae-ia-groupe7/
├── data/
│   ├── demo/                # Fichiers d'exemples pour tester (.txt, .md, .csv, ...)
│   └── chroma/              # Base de données créée automatiquement
├── docs/
│   ├── monitoring/          # Suivi officiel des Sprints (sprint-00 à sprint-05)
│   └── troubleshooting.md   # Guide de dépannage et débogage
├── src/
│   └── recherche_fichiers/
│       ├── config.py        # Réglages généraux (adresses, modèles, options)
│       ├── ui_gradio.py     # Interface web utilisateur (Gradio)
│       ├── service/         # Découpage des textes et logique de recherche
│       │   ├── core.py      # Programme principal
│       │   └── utils.py     # Fonctions d'aide (lecture de fichier, découpage)
│       ├── storage/         # Sauvegarde des données
│       │   └── base.py      # Base de données ChromaDB
│       └── ollama_client/   # Communication avec Ollama
│           ├── base.py      # Envoi des requêtes à Ollama
│           ├── embedding.py # Création des vecteurs (EmbeddingGemma)
│           ├── llm.py       # Génération de texte (Gemma 4 12B)
│           └── vlm.py       # Modèle pour les images (prévu pour plus tard)
├── tests/                   # Tests automatiques
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
| `LLM_MODEL`           | `gemma4:12b`             | Modèle utilisé pour reformuler et résumer            |
| `TOP_K`               | `5`                      | Nombre de résultats affichés par recherche           |
| `CHROMA_PERSIST_PATH` | `data/chroma`            | Dossier où est enregistrée la base de données        |

---

## 🛠️ Dépannage Rapide

| Problème                           | Ce qui se passe                                  | Ce qu'il faut faire                                                |
| :--------------------------------- | :----------------------------------------------- | :----------------------------------------------------------------- |
| `OllamaConnectionError`            | Ollama n'est pas allumé                          | Lancer Ollama sur votre ordinateur ou taper `ollama serve`         |
| `model 'embeddinggemma' not found` | Le modèle n'est pas téléchargé                   | Taper `ollama pull embeddinggemma` dans votre terminal             |
| `ModuleNotFoundError`              | Python ne trouve pas le dossier `src`            | Lancer la commande avec `python -m recherche_fichiers...`          |
| Aucun résultat trouvé              | Les fichiers n'ont pas encore été analysés       | Lancer `py -3.11 src/recherche_fichiers/service/core.py data/demo` |
| Port `7860` déjà utilisé           | L'application tourne déjà dans un autre terminal | Fermer l'autre fenêtre ou changer le numéro de port                |

👉 Pour voir toutes les astuces et solutions détaillées, consultez le **[Guide de Dépannage](docs/troubleshooting.md)**.

---

## 📜 Licence

Ce projet est sous licence **[CC BY-SA 4.0 (Creative Commons Attribution - Partage dans les Mêmes Conditions)](https://creativecommons.org/licenses/by-sa/4.0/)**.
