# Projet BigData/MLOps

## 1. Contexte et Objectif

Le sujet qui a été choisit est la **prédiction de résolution d'issues**.

L'objectif de ce projet est de prédire si et en combien de temps une issue sera résolue, à partir du texte de l'issue, des labels, de l'auteur et des PR liées.

- Utilité : aider les mainteneurs à prioriser. 
- Modèle : classification/régression (gradient boosting + embeddings de texte).
- Streaming : nouvelles issues scorées à l'arrivée.

## 2. Installation

### Cloner le dépôt git :

git clone https://github.com/Nathan-Perron/Projet_BigData_MLOps.git

### Création de l'environnement Conda :

- conda create --name nomEnvironnement
- conda activate nomEnvironnement
- pip install pygithub python-dotenv psycopg2-binary pgvector polars connectorx pyarrow

## Membres du groupe

| Nom | Contact |
| :--- | :--- |
| **Bossard Guilian** | Guilian.Bossard.Etu@univ-lemans.fr |
| **Perron Nathan** | Nathan.Perron.Etu@univ-lemans.fr |
