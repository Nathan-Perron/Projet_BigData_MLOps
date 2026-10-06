# Projet_BigData_MLOps

## Premières idées :

### 1. Prédiction de résolution d'issues
Prédire si et en combien de temps une issue sera résolue, à partir du texte de l'issue, des labels, de l'auteur et des PR liées. Utilité : aider les mainteneurs à prioriser. Modèle : classification/régression (gradient boosting + embeddings de texte). Streaming : nouvelles issues scorées à l'arrivée.

### 8. Détection de dépôts à risque ou abandonnés
Prédire l'abandon d'un projet (baisse d'activité des commits, issues sans réponse) pour aider les entreprises qui dépendent de bibliothèques open source. Original et facile à justifier métier.
