import psycopg2

# Connexion à la base de données PostgreSQL.
conn = psycopg2.connect(
    dbname="github_database",
    user="admin",
    password="admin123",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Vérification du nombre total d'issues dans la base de données.
cur.execute("SELECT COUNT(*) FROM issues;")
count = cur.fetchone()[0]

# Récupération d'un échantillon de 5 issues pour vérification.
cur.execute("SELECT issue_id, title, created_at, closed_at FROM issues LIMIT 5;")
rows = cur.fetchall()

print(f"Total d'issues en base : {count}\n")

print("Aperçu des données :")

# Affichage des issues récupérées pour vérification.
for row in rows:
    print(f"- [ID {row[0]}] {row[1][:40]}... (Créée le : {row[2]})")

# Fermeture de la connexion à la base de données.
cur.close()
conn.close()