import os
import psycopg2
from dotenv import load_dotenv
from github import Github, Auth

# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Connexion à l'API GitHub.
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)
repo = g.get_repo("apache/airflow")

# Connexion à la base de données PostgreSQL.
conn = psycopg2.connect(
    dbname="github_database",
    user="admin",
    password="admin123",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

print(f"Extraction des issues pour {repo.full_name}...")

# Récupération des 50 premières issues.
issues = repo.get_issues(state="all")[:50]

# Insertion des issues dans la base de données.
for issue in issues:

    # Exclut les Pull Requests des issues.
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

# Commit des changements et fermeture de la connexion à la base de données.
conn.commit()
cur.close()
conn.close()

print("Collecte réussie ! Les issues sont stockées dans PostgreSQL.")