import os
import re
import polars as pl


# Définition de la chaîne de connexion à la base de données PostgreSQL.
DATABASE_URI = "postgresql://admin:admin123@localhost:5432/github_database"

#
# Fonction pour nettoyer le texte des issues.
#
def clean_text_py(text: str) -> str:

    if(not text):
        return ""
    
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
def process_features():
    # Récupération des issues fermées depuis la base de données PostgreSQL.
    query = """
    SELECT issue_id, repo_name, title, body_clean, author_association, labels, created_at, closed_at
    FROM issues
    WHERE closed_at IS NOT NULL
    """
    
    # Lecture des données depuis la base de données en utilisant Polars.
    df = pl.read_database_uri(query=query, uri=DATABASE_URI)

    print(f"Issues fermées récupérées : {len(df)}")

    # Calcul du temps de résolution en heures et nettoyage du texte des issues.
    df_processed = (
        df.with_columns([
            # Calcul du temps de résolution en heures.
            ((pl.col("closed_at") - pl.col("created_at")).dt.total_milliseconds() / (1000 * 3600)).alias("resolution_time_hours")
        ])
        # Filtrage des issues avec un temps de résolution supérieur à 0.01 heures (36 secondes).
        .filter(pl.col("resolution_time_hours") >= 0.01)
        # Nettoyage du texte des issues en utilisant la fonction clean_text_py.
        .with_columns([
            pl.col("body_clean").map_elements(clean_text_py, return_dtype=pl.Utf8).alias("body_cleaned")
        ])
        # Création d'une colonne combinée pour le texte complet de l'issue.
        .with_columns([
            (pl.col("title") + " " + pl.col("body_cleaned")).alias("full_text")
        ])
    )

    # Sauvegarde du dataset nettoyé dans un fichier Parquet.
    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/issues_cleaned.parquet"
    df_processed.write_parquet(output_path)
    
    print(f"Dataset nettoyé sauvegardé avec succès dans : {output_path}")

    print("\nShape du dataset nettoyé :", df_processed.shape)
    print("\nAperçu des données nettoyées :")
    print(df_processed.head(5))
    print("\nAperçu des données avec les colonnes spécifiques :")
    print(df_processed.select(["issue_id", "repo_name", "resolution_time_hours"]).head(5))


    return df_processed


if __name__ == "__main__":
    process_features()