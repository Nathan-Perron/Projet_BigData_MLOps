import os
import psycopg2
from dotenv import load_dotenv
from github import Github, Auth

# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Liste des dépôts cibles.
TARGET_REPOS = [
    "apache/airflow",
    "pandas-dev/pandas",
    "scikit-learn/scikit-learn",
    "fastapi/fastapi",
    "psf/requests"
]

# Nombre d'issues à viser par dépôt.
ISSUES_PER_REPO = 300

# Connexion à l'API GitHub.
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)

# Connexion à la base de données PostgreSQL.
conn = psycopg2.connect(
    dbname="github_database",
    user="admin",
    password="admin123",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Collecte des issues pour chaque dépôt cible.
for repo_name in TARGET_REPOS:
    print(f"\n--- Collecte pour {repo_name} ---")

    try:
        # Connexion au dépôt GitHub.
        repo = g.get_repo(repo_name)
        issues_paginated = repo.get_issues(state="all")
        
        count = 0

        # Parcours des issues récupérées.
        for issue in issues_paginated:

            # Limite le nombre d'issues collectées par dépôt.
            if(count >= ISSUES_PER_REPO):
                break
                
            # Exclusion des Pull Requests.
            if(issue.pull_request is None):
                labels = [label.name for label in issue.labels]

                query = """
                INSERT INTO issues (
                    issue_id, repo_name, title, body_clean, author_association, 
                    labels, created_at, closed_at, state_reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issue_id) DO NOTHING;
                """

                cur.execute(query, (
                    issue.id,
                    repo.full_name,
                    issue.title,
                    issue.body or "",
                    issue.author_association,
                    labels,
                    issue.created_at,
                    issue.closed_at,
                    issue.state_reason
                ))

                count += 1

                # Affichage d'un message tous les 50 issues collectées.
                if(count % 50 == 0):
                    conn.commit()
                    print(f"  -> {count} issues enregistrées...")

        # Commit final après la collecte de toutes les issues pour le dépôt.
        conn.commit()

        print(f"Collecte terminée pour {repo_name} ({count} issues collectées).")

    except Exception as e:
        print(f"Erreur lors de la collecte de {repo_name} : {e}")

# Fermeture de la connexion à la base de données.
cur.close()
conn.close()

print("\nCollecte globale terminée !")