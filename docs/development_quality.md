# 🛡️ Qualité de Développement & Bonnes Pratiques (CI/CD)

> **Projet SAE S5 - Application IA** | BUT Informatique (3ᵉ année)  
> **Groupe 7** : Louis AMEDRO, Noé COLIN, Valentin MINNEBO

---

## 📌 1. Objectifs de la Démarche Qualité

Ce document formalise les normes de qualité logicielle, les conventions de code et les processus d'automatisation (CI/CD) mis en œuvre sur le projet afin de garantir :

1. **La robustesse du code** : tolérance aux pannes, gestion rigoureuse des erreurs et cas limites.
2. **La maintenabilité** : architecture modulaire claire, typage explicite et documentation intégrée.
3. **La non-régression** : exécution rapide et systématique d'une suite de 94 tests unitaires et d'intégration.
4. **L'intégrité du dépôt Git** : blocage des fichiers parasites (bases de données locales, caches temporaires).

---

## 🏗️ 2. Normes et Architecture du Code

### 2.1 Séparation stricte des responsabilités
Le code source est compartimenté en modules découplés selon le modèle architectural en couches :

- **`service/`** : Logique métier pure (lecture de fichiers, découpage en chunks, orchestration de la recherche, algorithme RRF). Ne dépend pas directement de la couche graphique.
- **`storage/`** : Couche de persistance et d'indexation (**VectorStore** avec ChromaDB et **LexicalStore** avec SQLite FTS5).
- **`ollama_client/`** : Couche d'infrastructure réseau asynchrone communiquant avec le serveur Ollama local.
- **`ui_gradio.py`** : Interface utilisateur (Gradio). Simple vue connectée au service métier unifié `search_mixed()`.

### 2.2 Typage et conventions Python
- **Conformité PEP 8** : Formatage standardisé, nommage clair et explicite des variables et fonctions.
- **Typage statique** : Utilisation systématique des annotations de types (`from __future__ import annotations`, `list[str]`, `dict | None`).
- **Logging professionnel** : Utilisation du module standard `logging` (`logger = logging.getLogger(__name__)`) pour le traçage des événements et des erreurs, évitant les instructions `print` désordonnées en production.
- **Gestion des dépréciations** : Lorsque des fonctions évoluent (ex: passage de `search()` vers `search_mixed()`), un avertissement explicite `warnings.warn(..., DeprecationWarning)` garantit la rétrocompatibilité temporaire.

---

## 🧪 3. Stratégie de Tests Automatisés

Le projet intègre **94 tests automatisés** exécutables en local en moins d'une seconde, sans nécessiter le lancement d'Ollama.

### 3.1 Organisation modulaire de `tests/`
Pour garantir la maintenabilité, les tests sont organisés en packages dédiés :

```text
tests/
├── __init__.py              # Marqueur de package global
├── ollama/                  # Tests unitaires du client Ollama (base, embedding, llm)
│   ├── __init__.py
│   ├── test_ollama.py
│   ├── test_embedding.py
│   └── test_llm.py
├── storage/                 # Tests unitaires de VectorStore et LexicalStore (FTS5)
│   ├── __init__.py
│   ├── test_vector_store.py
│   └── test_lexical_store.py
└── service/                 # Tests du core, utils (chunking, parsing) et validation hybride
    ├── __init__.py
    ├── test_core.py
    ├── test_utils.py
    └── test_search.py
```

> **Rôle des fichiers `__init__.py` dans les tests :**  
> Chaque sous-dossier de tests dispose de son fichier `__init__.py`. Cela transforme les dossiers en packages Python isolés, empêche toute collision de nom de fichier entre modules (ex: deux fichiers utilitaires de tests) et permet la découverte récursive automatique par `unittest` et les outils de CI/CD.

### 3.2 Principes d'isolation des tests
- **Zéro dépendance réseau** : Les appels vers Ollama sont simulés via `unittest.mock.AsyncMock` et `patch`, garantissant que les tests s'exécutent même sur une machine sans carte graphique ni serveur IA allumé.
- **Bases éphémères** : Les tests du `LexicalStore` s'exécutent sur une base SQLite en mémoire (`:memory:`), sans persistance sur disque.
- **Nettoyage sécurisé sous Windows** : Les tests utilisant ChromaDB emploient des répertoires temporaires avec protection contre les verrous de fichiers exclusifs de Windows (`PermissionError [WinError 32]`).

### 3.3 Couverture des cas limites et négatifs
Les tests ne vérifient pas seulement le cas idéal (*happy path*), ils valident la résilience du système face à des situations dégradées :
- Fichiers vides ou non pris en charge (`.xyz`).
- Documents corrompus ou illisibles.
- Indisponibilité du serveur Ollama (`OllamaConnectionError`).
- Requêtes lexicales contenant des caractères spéciaux ou de la ponctuation complexe (`?`, `!`, `()`, `:`, guillemets).

---

## 🔄 4. Intégration Continue (CI/CD)

Le projet dispose d'une chaîne CI/CD à double niveau : **locale avant commit** et **distante sur GitHub**.

### 4.1 En local : Vérification pré-commit manuelle ou automatique

Avant de commiter, chaque développeur peut exécuter le script de validation :

```powershell
.\scripts\verify.ps1
# ou directement en Python : py -3.11 scripts/verify.py
```

**Ce que fait ce script en 1 seconde :**
1. **Compilation syntaxique** : Vérifie qu'aucun fichier Python ne comporte d'erreur de syntaxe (`compileall src tests`).
2. **Contrôle Git anti-fuite** : Vérifie qu'aucune base de données locale (`data/chroma`, `data/lexical.db`) n'est suivie par Git.
3. **Exécution des 94 tests** : Lance la suite complète et affiche un bilan visuel clair.

> **Option Git Hook Automatique :**  
> Pour bloquer automatiquement tout commit si un test échoue :
> ```powershell
> .\scripts\install_hook.ps1
> ```

### 4.2 Sur GitHub : Pipeline GitHub Actions (`.github/workflows/ci.yml`)

À chaque `push` ou `pull_request` sur les branches `main` et `dev` (ou manuellement via `workflow_dispatch`), GitHub Actions :

1. Démarre deux machines virtuelles en parallèle : **Windows** (`windows-latest`) et **Linux** (`ubuntu-latest`).
2. Installe Python 3.11 et les dépendances du projet (`requirements.txt`).
3. Compile l'intégralité du code (`python -m compileall src tests`).
4. Vérifie l'absence de fichiers interdits dans l'index Git.
5. Exécute les 94 tests unitaires et d'intégration.
6. Valide ou bloque la Pull Request selon le résultat des tests.

---

## 📋 5. Règles de Contribution & Conventions Git

- **Branches de travail** :
  - `main` : Branche de production stable, protégée.
  - `dev` : Branche d'intégration des sprints en cours.
- **Format des commits (*Conventional Commits*)** :
  - `feat(...)` : Nouvelle fonctionnalité utilisateur.
  - `fix(...)` : Correction d'un bug.
  - `test(...)` : Ajout ou mise à jour de tests.
  - `docs(...)` : Mise à jour de la documentation.
  - `ci(...)` : Modification du pipeline ou des scripts CI/CD.
  - `refactor(...)` : Réorganisation du code sans changement de fonctionnalité.
- **Définition de Terminé (DoD - Definition of Done)** :
  - Aucune erreur de syntaxe ou d'importation.
  - 100% des tests passants (94 tests au vert).
  - Documentation mise à jour (`README.md`, `architecture.md`, `troubleshooting.md`).
  - Validation du pipeline CI GitHub Actions.
