import os
import joblib
import psycopg2
import numpy as np
import polars as pl
from dotenv import load_dotenv
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Configuration des chemins pour les fichiers Parquet et le modèle entraîné.
PARQUET_PATH = "data/processed/issues_cleaned.parquet"
MODEL_OUTPUT_PATH = "models/resolution_time_model.pkl"

#
# Charge les données nettoyées depuis le fichier Parquet et les embeddings depuis PostgreSQL et fusionne les caractéristiques tabulaires et vectorielles.
#
def load_data_and_features():
    print("Chargement des données nettoyées depuis le Parquet...")

    df = pl.read_parquet(PARQUET_PATH)

    print("\nRécupération des embeddings depuis la base de données PostgreSQL...")

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

    # Récupération des embeddings stockés dans la base de données PostgreSQL.
    cursor.execute("SELECT issue_id, title_body_embedding::text FROM issues WHERE title_body_embedding IS NOT NULL;")
    rows = cursor.fetchall()

    # Fermeture de la connexion à la base de données.
    cursor.close()
    conn.close()

    # Transformation des embeddings récupérés en dictionnaire.

    embeddings = {}

    for issue_id, embedding in rows:
        vector = [float(value) for value in embedding.strip("[]").split(",")]
        embeddings[issue_id] = vector

    # Filtre le DataFrame pour ne conserver que les issues ayant des embeddings.
    df = df.filter(pl.col("issue_id").is_in(list(embeddings.keys())))

    # Transformation one-hot basique pour la variable catégorielle author_association
    df_encoded = df.to_dummies(columns=["author_association"])
    
    # Isolation de la cible (Y) et préparation de la matrice de features (X)
    y = df_encoded["resolution_time_hours"].to_numpy()
    
    # Matrice d'embeddings (384 colonnes)
    X_embeddings = np.array([embeddings[i_id] for i_id in df_encoded["issue_id"]])
    
    # Caractéristiques catégorielles encodées
    categorical_cols = [col for col in df_encoded.columns if col.startswith("author_association_")]
    X_categorical = df_encoded[categorical_cols].to_numpy()

    # Fusion des features vectorielles (NLP) et tabulaires
    X = np.hstack((X_embeddings, X_categorical))

    print(f"Dataset prêt : {X.shape[0]} d'issues et {X.shape[1]} caractéristiques")

    return X, y


#
# Entraîne et évalue le modèle de régression LightGBM.
#
def train_model():
    # Chargement des données et des caractéristiques.
    X, y = load_data_and_features()

    # Sépare les données en ensembles d'entraînement et de test (80% train, 20% test).
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("\nEntraînement du modèle LightGBM Regressor...")

    # Configuration et entraînement du modèle LightGBM.
    model = LGBMRegressor(
        n_estimators=150,
        learning_rate=0.03,
        max_depth=5,
        random_state=42,
        verbosity=-1
    )
    model.fit(X_train, y_train)

    # Prédit les temps de résolution sur l'ensemble de test et calcule les métriques d'évaluation.
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = root_mean_squared_error(y_test, predictions)

    print("\n--- Métriques d'Évaluation du Modèle ---")
    print(f"MAE  (Erreur Absolue Moyenne)               : {mae:.2f} heures")
    print(f"RMSE (Racine de l'Erreur Quadratique Moyenne) : {rmse:.2f} heures")

    # Exporte le modèle entraîné dans un fichier .pkl pour une utilisation future.
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_OUTPUT_PATH)

    print(f"\nModèle sauvegardé dans : {MODEL_OUTPUT_PATH}")


if(__name__ == "__main__"):
    train_model()