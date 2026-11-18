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
- pip install pygithub python-dotenv psycopg2-binary pgvector polars connectorx pyarrow sentence-transformers lightgbm scikit-learn

## 3. Critères de notation pour l'aspect Big Data du projet :
- Collecte des données
- Streaming de nouvelles données et scoring en temps réel
- Prétraitement des données
- Modélisation et évaluation des performances
- Visualisation des résultats

## 4. Critères de notation pour l'aspect MLOPS du projet :
- Architecture du pipeline
- Conteneurisation
- Orchestration
- Monitoring (visualisation de l'état des composants et du pipeline dans sa globalité)
- Data drifting (possibilités de détécter des erreurs et de relancer un entraînement)

## Membres du groupe

| Nom | Contact |
| :--- | :--- |
| **Bossard Guilian** | Guilian.Bossard.Etu@univ-lemans.fr |
| **Perron Nathan** | Nathan.Perron.Etu@univ-lemans.fr |





Étape A — API FastAPI + Logging & Métriques (src/api/main.py) :
Ajouter l'enregistrement de chaque prédiction dans une table PostgreSQL predictions_log (indispensable pour nourrir le Data Drift) et exposer un endpoint /metrics pour Prometheus.

Étape B — Data Drifting (src/monitoring/drift_detector.py) :
Créer le script Evidently AI qui compare les données reçues en prod (predictions_log) au jeu d'entraînement (issues_cleaned.parquet) et déclenche train.py en cas de dérive.

Étape C — Streaming (src/streaming/producer.py & consumer.py) : 
Brancher Redpanda (Kafka) pour ingérer un flux continu d'issues GitHub et générer des prédictions à la volée.

Étape D — Orchestration (src/orchestration/pipeline_flow.py) :
Envelopper tout ton pipeline dans Prefect pour visualiser l'état des tâches et automatiser les relances.

Étape E — Conteneurisation & Monitoring (Dockerfile + docker-compose.yml + Grafana) :
Assembler tous les conteneurs dans un docker-compose.yml prêt à démarrer en une seule commande (docker compose up -d).
