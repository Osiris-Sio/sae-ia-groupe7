# 🛠️ Guide de Dépannage et Débogage

Ce guide regroupe les vérifications rapides, solutions aux erreurs fréquentes et procédures d'isolation pour le projet **Moteur de Recherche Documentaire**.

---

## ⚡ 1. Diagnostic Express (Vérifications en 1 ligne)

Avant de chercher plus loin, exécutez ces vérifications depuis la racine du projet :

### A. Tester la disponibilité du serveur Ollama

Le plus simple est d'interroger directement le serveur :
```powershell
# Méthode 1 (La plus rapide avec curl)
curl http://localhost:11434/
# Réponse attendue : "Ollama is running"
```

Ou via Python en incluant le dossier `src` :
```powershell
# Méthode 2 (En Python)
py -3.11 -c "import sys; sys.path.insert(0, 'src'); import asyncio; from recherche_fichiers.ollama_client.base import is_server_running; print('Ollama en ligne :', asyncio.run(is_server_running()))"
```
* Si `True` : Ollama est joignable.
* Si `False` : Ollama est éteint ou inaccessible sur le port configuré (défaut `11434`).

### B. Vérifier que le modèle d'embedding est téléchargé
```powershell
ollama list
```
Vérifiez que `embeddinggemma` figure dans la liste.

### C. Lancer la suite de tests unitaires (sans dépendance externe)
```powershell
py -3.11 -m unittest discover tests
```
Tous les tests doivent afficher `OK`.

---

## 🦙 2. Problèmes liés à Ollama

### Erreur : `OllamaConnectionError: Impossible de se connecter au serveur Ollama`
* **Cause :** Le service Ollama n'est pas lancé en arrière-plan.
* **Solution :**
  1. Lancez Ollama dans un terminal dédié :
     ```powershell
     ollama serve
     ```
  2. Ou sous Windows, vérifiez que l'icône Ollama est présente dans la zone de notification (près de l'horloge).
  3. Si Ollama écoute sur une adresse différente ou un port spécifique, définissez la variable d'environnement ou modifiez `.env` :
     ```powershell
     $env:OLLAMA_URL="http://127.0.0.1:11434"
     ```

### Erreur : `model 'embeddinggemma' not found`
* **Cause :** Le modèle n'a pas été téléchargé en local.
* **Solution :**
  ```powershell
  ollama pull embeddinggemma
  ```
  *(Optionnel, pour les fonctions avancées du LLM)* :
  ```powershell
  ollama pull gemma4:12b
  ```

### Erreur : `TimeoutException` / Délai d'attente dépassé
* **Cause :** Le modèle met du temps à se charger en mémoire lors de la toute première inférence.
* **Solution :**
  * Augmentez la variable `OLLAMA_TIMEOUT` dans `src/recherche_fichiers/config.py` ou via l'environnement :
    ```powershell
    $env:OLLAMA_TIMEOUT="120"
    ```

---

## 🐍 3. Problèmes d'Environnement Python & Imports

### Erreur : `ModuleNotFoundError: No module named 'recherche_fichiers'`
* **Cause :** Le dossier `src/` n'était pas automatiquement dans le chemin de recherche de Python.
* **Solutions :**
  * **Option recommandée (lancer le fichier directement) :**
    ```powershell
    py -3.11 src/recherche_fichiers/ui_gradio.py
    ```
    *(Les scripts `core.py` et `ui_gradio.py` ajoutent désormais automatiquement le dossier `src` dans `sys.path`).*
  * **Option avec variable d'environnement :**
    ```powershell
    $env:PYTHONPATH="src"
    py -3.11 src/recherche_fichiers/ui_gradio.py
    ```
    py -3.11 src/recherche_fichiers/ui_gradio.py
    ```

### Erreur : Mauvaise version de Python exécutée
* **Cause :** Sur Windows, `python` pointe parfois sur une version globale non compatible (ex: Python 3.14 / MSYS2 / Windows Store).
* **Solution :**
  * Utilisez explicitement le lanceur Windows :
    ```powershell
    py -3.11 --version
    ```
  * Ou activez systématiquement votre environnement virtuel :
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```

---

## 💾 4. Base Vectorielle ChromaDB

### Erreur : Incohérence des dimensions ou corruption de la collection
* **Symptôme :** ChromaDB rejette l'insertion ou la recherche avec un message du type `dimensionality does not match`.
* **Explication :** `embeddinggemma` utilise des vecteurs de dimension 768. Si une ancienne base a été initialisée avec un autre modèle, un conflit se produit.
* **Solution (Réinitialisation propre du cache vectoriel) :**
  Supprimez simplement le dossier de persistance pour repartir sur une base propre :
  ```powershell
  Remove-Item -Recurse -Force data/chroma
  ```
  Puis réindexez le jeu de données :
  ```powershell
  py -3.11 src/recherche_fichiers/service/core.py data/demo
  ```

---

## 🌐 5. Interface Gradio (`ui_gradio.py`)

### Erreur : `OSError: [Errno 10048] Only one usage of each socket address`
* **Cause :** Le port par défaut de Gradio (`7860`) est déjà occupé par une instance précédente restée active en arrière-plan.
* **Solution :**
  * Fermez l'ancien processus dans le Gestionnaire des tâches ou lancez sur un autre port via les options Gradio :
    ```python
    interface.launch(server_port=7865)
    ```

### La recherche ne renvoie aucun résultat
* **Points à vérifier :**
  1. Avez-vous indexé les documents avant de chercher ? ChromaDB est vide par défaut au premier lancement.
  2. Exécutez l'indexation de démonstration :
     ```powershell
     py -3.11 src/recherche_fichiers/service/core.py data/demo
     ```
  3. Relancez ensuite l'interface Gradio et testez un mot-clé comme *"algorithme"* ou *"boucle"*.

---

## 🧪 6. Isoler un problème avec les tests unitaires

Chaque composant peut être testé individuellement de manière 100% isolée (ne sollicite ni Ollama ni le réseau grâce aux mocks) :

```powershell
# Tester la communication de base Ollama
py -3.11 tests/test_ollama.py

# Tester la vectorisation et le MRL
py -3.11 tests/test_embedding.py

# Tester le LLM (reformulation, synthèse, thèmes)
py -3.11 tests/test_llm.py

# Tester le stockage ChromaDB
py -3.11 tests/test_storage.py

# Tester le pipeline de service et le chunking
py -3.11 tests/test_core.py
py -3.11 tests/test_utils.py
```
