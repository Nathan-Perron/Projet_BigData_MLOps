import os
import psycopg2
from dotenv import load_dotenv
from github import Github, Auth


# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Vérifier la présence des variables nécessaires
required_vars = [
    "GITHUB_TOKEN",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Variables manquantes dans .env : {missing_vars}")

# Connexion à l'API GitHub.
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
github = Github(auth=auth)

# Connexion à Azure PostgreSQL.
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    sslmode="require"
)
cursor = conn.cursor()

# Requête de recherche pour récupérer les issues fermées avec le label "bug" et plus de 500 étoiles.
search_query = "is:issue is:closed label:bug stars:>500"
MAX_ISSUES = 50

print(f"Extraction de {MAX_ISSUES} issues pour via : \"{search_query}\"...")

# Récupération de 5 issues correspondant à la requête de recherche.
issues = github.search_issues(query=search_query, sort="created", order="desc")

processed = 0
inserted = 0

try:
    # Insertion des issues dans la base de données.
    for issue in issues:

        # Arrêt dès qu'on a atteint les 50 issues souhaitées
        if processed >= MAX_ISSUES:
            break

        # Exclut les Pull Requests des issues.
        if(issue.pull_request is not None):
            continue

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

        processed += 1

        if cursor.rowcount == 1:
            inserted += 1
        
        # Affichage d'un message tous les 50 issues collectées.
        if(processed % 10 == 0):
            conn.commit()
            print(f"  -> {processed}/{MAX_ISSUES} issues enregistrées...")

    conn.commit()

    print("\nCollecte terminée !")
    print(f"Issues traitées : {processed}")
    print(f"Nouvelles issues insérées : {inserted}")
    print(f"Issues déjà présentes : {processed - inserted}")

except Exception:
    conn.rollback()
    raise

finally:
    cursor.close()
    conn.close()
    github.close()