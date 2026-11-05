import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connexion Azure PostgreSQL.
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    sslmode="require"
)
cursor = conn.cursor()

# Vérification du nombre total d'issues dans la base de données.
cursor.execute("SELECT COUNT(*) FROM issues;")
count = cursor.fetchone()[0]

# Récupération d'un échantillon de 5 issues pour vérification.
cursor.execute("SELECT issue_id, title, created_at, closed_at FROM issues LIMIT 5;")
rows = cursor.fetchall()

print(f"Total d'issues en base : {count}\n")

print("Aperçu des données :")

# Affichage des issues récupérées pour vérification.
for row in rows:
    print(f"- [ID {row[0]}] {row[1][:40]}... (Créée le : {row[2]})")

# Vérification de la taille de la base de données.
cursor.execute("SELECT pg_size_pretty(pg_database_size('github_database'));")
db_size = cursor.fetchone()[0]

# Vérification de la taille de la table issues.
cursor.execute("SELECT pg_size_pretty(pg_total_relation_size('issues'));")
issues_table_size = cursor.fetchone()[0]

# Affichage des tailles de la base de données et de la table issues.
print(f"\nTaille totale de la base : {db_size}")
print(f"Taille de la table 'issues' : {issues_table_size}")

# Fermeture de la connexion à la base de données.
cursor.close()
conn.close()
