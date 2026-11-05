import os
import psycopg2
import polars as pl
from sentence_transformers import SentenceTransformer


# Configuration des paramètres pour la génération d'embeddings.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PARQUET_PATH = "data/processed/issues_cleaned.parquet"

# 
# Fonction pour générer et stocker les embeddings des issues.
#
def generate_and_store_embeddings():

    # Vérifie si le fichier Parquet existe avant de continuer.
    if(not os.path.exists(PARQUET_PATH)):
        raise FileNotFoundError(f"Le fichier {PARQUET_PATH} n'existe pas.")

    print(f"Chargement des données nettoyées depuis : {PARQUET_PATH}...")

    df = pl.read_parquet(PARQUET_PATH)

    # Prépare les données pour la génération d'embeddings.
    issue_ids = df["issue_id"].to_list()
    full_texts = df["full_text"].to_list()

    print(f"\nNombre d'issues à vectoriser : {len(full_texts)}")

    print(f"\nChargement du modèle NLP ({MODEL_NAME})...")

    # Charge le modèle de génération d'embeddings.
    model = SentenceTransformer(MODEL_NAME)

    print("\nCalcul des embeddings sémantiques (384-d)...")

    # Calcule les embeddings pour le texte complet des issues.
    embeddings = model.encode(
        full_texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("\nMise à jour des vecteurs dans PostgreSQL (pgvector)...")

    conn = psycopg2.connect(
        dbname="github_database",
        user="admin",
        password="admin123",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # Requête SQL pour mettre à jour les embeddings dans la base de données.
    update_query = """
    UPDATE issues
    SET title_body_embedding = %s::vector
    WHERE issue_id = %s AND title_body_embedding IS NULL;
    """

    # Formate les données pour l'insertion.
    updates = [(embedding.tolist(), int(issue_id)) for issue_id, embedding in zip(issue_ids, embeddings)]

    # Insert les embeddings dans la base de données.
    cursor.executemany(update_query, updates)
    conn.commit()

    print(f"\nSuccès ! {len(updates)} vecteurs insérés dans 'title_body_embedding'.")

    cursor.close()
    conn.close()


if(__name__ == "__main__"):
    generate_and_store_embeddings()