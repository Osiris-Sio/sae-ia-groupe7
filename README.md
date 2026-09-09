# 🔍 Moteur de Recherche Documentaire Hybride (Lexical & Sémantique)

> **SAE S5 — Application IA** | BUT Informatique (3ᵉ année, 2026–2027)  
> **IUT de Calais**

---

## 👥 Équipe & Encadrement

- **Étudiants (TPC) :**
  - Louis AMEDRO (_Osiris Sio_) (responsable)
  - Noé COLIN (_Kiizer861_)
  - Valentin MINNEBO (_Jonedeuf_)
- **Enseignants référents :**
  - M. COZOT
  - Mme PACOU

---

## 📌 Problématique

Les utilisateurs (étudiants, enseignants) stockent leurs documents sous des formats hétérogènes et de manière non structurée (`.pdf`, `.docx`, `.md`, `.txt`, `.csv`).

Face à ce volume documentaire, les méthodes de recherche isolées présentent des faiblesses :

- **Recherche lexicale classique :** échoue en cas de reformulation, de synonymie ou d'expression en langage naturel.
- **Recherche vectorielle (RAG) :** perd en précision sur des termes techniques pointus, des acronymes ou des codes spécifiques.

---

## 🎯 Objectifs du Projet

### Objectif général

Concevoir et développer un **moteur de recherche et d'exploration documentaire hybride**, capable d'exécuter et de comparer en temps réel :

1. **Une recherche lexicale** (BM25 / FTS5).
2. **Une recherche sémantique** (RAG / Embeddings).

### Démonstration attendue

Proposer une **interface interactive** mettant en évidence les apports respectifs de chaque méthode sur des cas concrets de recherche en langage naturel :

- Comparaison en direct des résultats et scores de pertinence (lexical vs sémantique vs hybride).
- Mise en valeur des forces et limites de chaque approche selon la typologie de la requête.

---

## 📂 Formats Documentaires Supportés

| Format                 | Extension | Usage typique                    |
| :--------------------- | :-------- | :------------------------------- |
| **PDF**                | `.pdf`    | Polycopiés, articles, mémoires   |
| **Word**               | `.docx`   | Rapports, synthèses, cours       |
| **Markdown**           | `.md`     | Documentations techniques, notes |
| **Texte brut**         | `.txt`    | Fichiers de notes, logs          |
| **Données tabulaires** | `.csv`    | Jeux de données, exports         |

---

## 📜 Licence

Ce projet est sous licence **[CC BY-SA (Creative Commons Attribution - Partage dans les Mêmes Conditions)](https://creativecommons.org/licenses/by-sa/4.0/)**.
