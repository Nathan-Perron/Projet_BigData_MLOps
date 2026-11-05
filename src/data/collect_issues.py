import os
import psycopg2
from dotenv import load_dotenv
from github import Github, Auth


# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Connexion à l'API GitHub.
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
github = Github(auth=auth)

# Connexion à la base de données PostgreSQL.
conn = psycopg2.connect(
    dbname="github_database",
    user="admin",
    password="admin123",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Requête de recherche pour récupérer les issues fermées avec le label "bug" et plus de 500 étoiles.
search_query = "is:issue is:closed label:bug stars:>500"
MAX_ISSUES = 500

print(f"Extraction de {MAX_ISSUES} issues pour via : \"{search_query}\"...")

# Récupération de 5 issues correspondant à la requête de recherche.
issues = github.search_issues(query=search_query, sort="created", order="desc")

count = 0

# Insertion des issues dans la base de données.
for issue in issues:

    # Arrêt dès qu'on a atteint les 500 issues souhaitées
    if(count >= MAX_ISSUES):
        break

    # Exclut les Pull Requests des issues.
    if(issue.pull_request is None):
        labels = [label.name for label in issue.labels]

        # Récupère le nom du dépôt à partir de l'URL du dépôt.
        repo_name = "/".join(issue.repository_url.split("/")[-2:])

        query = """
        INSERT INTO issues (
            issue_id, repo_name, title, body_clean, author_association, 
            labels, created_at, closed_at, state_reason
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (issue_id) DO NOTHING;
        """

        cursor.execute(query, (
            issue.id,
            repo_name,
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
            print(f"  -> {count}/{MAX_ISSUES} issues enregistrées...")

# Commit des changements et fermeture de la connexion à la base de données.
conn.commit()
cursor.close()
conn.close()

print("\nCollecte réussie ! Les issues sont stockées dans PostgreSQL.")