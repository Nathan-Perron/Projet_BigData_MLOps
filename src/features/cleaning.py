import os
import re
import psycopg2
import polars as pl
from dotenv import load_dotenv


# Charge les variables d'environnement depuis le fichier .env.
load_dotenv()

OUTPUT_PATH = "data/issues_cleaned.parquet"

#
# Fonction pour nettoyer le texte des issues.
#
def clean_text(text):

    # Ignore les textes vides ou nuls.
    if(not text):
        return ""

    # Nettoyage du texte en supprimant les éléments indésirables.
    
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL) # Supprime les blocs de code entre triple backticks.
    text = re.sub(r'`.*?`', '', text) # Supprime les blocs de code entre backticks simples.
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text) # Supprime les images Markdown.
    text = re.sub(r'http\S+', '', text) # Supprime les URLs.
    text = re.sub(r'<.*?>', '', text) # Supprime les balises HTML.
    text = re.sub(r'@\w+', '', text) # Supprime les mentions.
    text = re.sub(r'\s+', ' ', text).strip() # Supprime les espaces multiples et les espaces en début/fin de chaîne.

    return text


#
# Fonction principale pour traiter les features des issues.
#
def clean_features():
    # Connexion à la base de données PostgreSQL.
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )
    
    # Récupération des issues fermées depuis la base de données PostgreSQL.
    query = """
    SELECT issue_id, repo_name, title, body_clean, author_association, labels, created_at, closed_at
    FROM issues
    WHERE closed_at IS NOT NULL
    AND (state_reason = 'completed' OR state_reason IS NULL)
    """
    
    # Lecture des données depuis la base de données en utilisant Polars.
    try:
        df = pl.read_database(query=query, connection=conn)
    finally:
        conn.close()

    print(f"Issues fermées récupérées : {len(df)}")

    # Calcul du temps de résolution en heures et nettoyage du texte des issues.
    df_processed = (
        df.with_columns([
            # Calcul du temps de résolution en heures.
            ((pl.col("closed_at") - pl.col("created_at")).dt.total_milliseconds() / (1000 * 3600)).alias("resolution_time_hours")
        ])
        # Filtrage des issues avec un temps de résolution supérieur à 0.01 heures (36 secondes).
        .filter(pl.col("resolution_time_hours") >= 0.01)
        # Nettoyage du texte des issues.
        .with_columns([
            pl.col("body_clean")
            .fill_null("")
            .str.replace_all(r"(?s)```.*?```", "")   # Blocs de code multi-lignes
            .str.replace_all(r"`.*?`", "")           # Code inline
            .str.replace_all(r"!\[.*?\]\(.*?\)", "") # Images Markdown
            .str.replace_all(r"http\S+", "")         # URLs
            .str.replace_all(r"<.*?>", "")           # Balises HTML
            .str.replace_all(r"@\w+", "")            # Mentions utilisateurs
            .str.replace_all(r"\s+", " ")            # Espaces multiples
            .str.strip_chars()
            .alias("body_cleaned")
        ])
        # Création d'une colonne combinée pour le texte complet de l'issue.
        .with_columns([
            (pl.col("title") + " " + pl.col("body_cleaned")).alias("full_text")
        ])
    )

    # Sauvegarde du dataset nettoyé dans un fichier Parquet.
    os.makedirs("data", exist_ok=True)
    df_processed.write_parquet(OUTPUT_PATH)
    
    print(f"Dataset nettoyé sauvegardé avec succès dans : {OUTPUT_PATH}")

    print("\nShape du dataset nettoyé :", df_processed.shape)
    print("\nAperçu des données nettoyées :")
    print(df_processed.head(5))
    print("\nAperçu des données avec les colonnes spécifiques :")
    print(df_processed.select(["issue_id", "repo_name", "resolution_time_hours"]).head(5))

    return df_processed


if(__name__ == "__main__"):
    clean_features()