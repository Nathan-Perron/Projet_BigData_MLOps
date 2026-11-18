import os
import time
import psycopg2
from dotenv import load_dotenv
from github import Github, Auth, RateLimitExceededException


# Charge les variables d'environnement depuis le fichier .env.
load_dotenv()

# Connexion à l'API GitHub.
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
github = Github(auth=auth, timeout=15,per_page=100)

# Connexion à la base de données PostgreSQL.
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    sslmode="require"
)
cursor = conn.cursor()


# Requête de recherche pour récupérer les issues fermées avec le label "bug" et plus de 250 étoiles.
base_query = "is:issue is:closed label:bug stars:>250"
MAX_ISSUES = 2500

print(f"Extraction de {MAX_ISSUES} issues via : \"{base_query}\"...")

processed = 0
inserted = 0
last_date = None

try:

    while(inserted < MAX_ISSUES):

        # Détermine la requête de recherche en fonction de la date de la dernière issue traitée.
        if(last_date):
            search_query = f"{base_query} created:<{last_date}"
        else:
            search_query = base_query

        try:
            issues = github.search_issues(query=search_query, sort="created", order="desc")

            for issue in issues:

                if(inserted >= MAX_ISSUES):
                    break

                if(issue.pull_request is not None):
                    continue

                labels = [label.name for label in issue.labels]
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

                # Met à jour la date de la dernière issue traitée pour la prochaine itération.
                last_date = issue.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

                if(cursor.rowcount == 1):
                    inserted += 1

                    if(inserted % 50 == 0):
                        conn.commit()
                        print(f"  -> {inserted}/{MAX_ISSUES} issues enregistrées...")

        except RateLimitExceededException:
            conn.commit()
            print("Limite de requêtes atteinte, pause de 60 secondes...")
            time.sleep(60)

    conn.commit()

    print("\nCollecte terminée !")
    print(f"Issues traitées : {processed}")
    print(f"Nouvelles issues insérées : {inserted}")
    print(f"Issues déjà présentes : {processed - inserted}")

except Exception as e:
    conn.rollback()
    print(f"Une erreur est survenue lors de la collecte des issues : {e}")

finally:
    cursor.close()
    conn.close()
    github.close()