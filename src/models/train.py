import os
import pickle
import psycopg2
import numpy as np
import polars as pl
from dotenv import load_dotenv
from lightgbm import LGBMRegressor, early_stopping
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    root_mean_squared_error,
)


# Charger les variables d'environnement depuis le fichier .env.
load_dotenv()

# Configuration des chemins pour les fichiers Parquet et le modèle entraîné.
PARQUET_PATH = "data/issues_cleaned.parquet"
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

    # Transforme les colonnes catégorielles en variables indicatrices (one-hot encoding).
    df_encoded = df.to_dummies(columns=["author_association"])
    
    # Récupère la variable cible (temps de résolution en heures).
    y = df_encoded["resolution_time_hours"].to_numpy()
    
    # Crée une matrice numpy pour les embeddings en utilisant l'ordre des issue_id dans le DataFrame.
    X_embeddings = np.array([embeddings[i_id] for i_id in df_encoded["issue_id"]])
    
    # Caractérise les colonnes catégorielles pour la fusion avec les embeddings.
    categorical_cols = sorted([col for col in df_encoded.columns if col.startswith("author_association_")])
    X_categorical = df_encoded[categorical_cols].to_numpy()

    # Fusionne les features vectorielles (NLP) et tabulaires.
    X = np.hstack((X_embeddings, X_categorical))

    print(f"\nDataset prêt : {X.shape[0]} issues et {X.shape[1]} caractéristiques")

    return X, y


#
# Calcule les 4 métriques d'évaluation en heures réelles et en échelle logarithmique.
#
def calculate_metrics(y_true, y_true_log, y_pred_log):
    y_pred = np.maximum(0.0, np.expm1(y_pred_log))

    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "MdAE": median_absolute_error(y_true, y_pred),
        "RMSE": root_mean_squared_error(y_true, y_pred),
        "RMSLE": root_mean_squared_error(y_true_log, y_pred_log),
    }


#
# Entraîne, compare sur Dev, et évalue le meilleur modèle sur Test.
#
def train_model():
    X, y = load_data_and_features()

    # Découpe les données en Train (70%), Dev (15%) et Test (15%) pour l'entraînement et l'évaluation.
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42)
    X_dev, X_test, y_dev, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42)

    print(f"\nDécoupage des données :\n\t- Train : {X_train.shape[0]} issues\n\t- Dev   : {X_dev.shape[0]} issues\n\t- Test  : {X_test.shape[0]} issues")

    # Transforme les cibles en échelle logarithmique pour la stabilisation de la variance et la réduction de l'impact des valeurs extrêmes.
    y_train_log = np.log1p(y_train)
    y_dev_log = np.log1p(y_dev)
    y_test_log = np.log1p(y_test)

    # Définition des modèles candidats pour l'entraînement et la sélection.
    models = {
        "Ridge": Ridge(alpha=10.0, random_state=42),

        "RandomForest": RandomForestRegressor(
            n_estimators=150,
            max_depth=12,
            n_jobs=-1,
            random_state=42
        ),

        "LightGBM": LGBMRegressor(
            objective="huber",
            n_estimators=600,
            learning_rate=2e-2,
            max_depth=5,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1
        )
    }

    best_model = None
    best_name = None
    best_dev_mdae = float("inf")

    print("\n--- Entraînement via Train et sélection de la meilleure configuration sur Dev ---")

    for name, model in models.items():

        # Ajoute un early stopping pour LightGBM afin d'éviter le surapprentissage.
        if(name == "LightGBM"):
            model.fit(
                X_train,
                y_train_log,
                eval_X=X_dev,
                eval_y=y_dev_log,
                callbacks=[early_stopping(stopping_rounds=30, verbose=False)]
            )

        else:
            model.fit(X_train, y_train_log)

        # Evalue sur le jeu Dev pour comparer les modèles.
        y_dev_pred_log = model.predict(X_dev)
        dev_metrics = calculate_metrics(y_dev, y_dev_log, y_dev_pred_log)

        print(f"\n[Modèle {name} - Évaluation sur Dev]")
        print(f"\t- MAE   (Erreur Absolue Moyenne)               : {dev_metrics["MAE"]:.2f} heures")
        print(f"\t- MdAE  (Erreur Absolue Médiane)               : {dev_metrics["MdAE"]:.2f} heures")
        print(f"\t- RMSE  (Racine de l'Erreur Quadratique Moyenne) : {dev_metrics["RMSE"]:.2f} heures")
        print(f"\t- RMSLE (Erreur Logarithmique Quadratique)     : {dev_metrics["RMSLE"]:.4f}")

        # Récupère le meilleur modèle basé sur la métrique MdAE (Erreur Absolue Médiane) sur le jeu Dev.
        if(dev_metrics["MdAE"] < best_dev_mdae):
            best_dev_mdae = dev_metrics["MdAE"]
            best_name = name
            best_model = model

    # Évaluation finale unique sur le jeu Test resté totalement vierge.
    y_test_pred_log = best_model.predict(X_test)
    test_metrics = calculate_metrics(y_test, y_test_log, y_test_pred_log)

    # Affiche les métriques finales sur le jeu Test pour le meilleur modèle sélectionné.
    print(f"\n--- Évaluation finale sur Test (modèle : {best_name}) ---")
    print(f"\t- MAE   (Erreur Absolue Moyenne)               : {test_metrics["MAE"]:.2f} heures")
    print(f"\t- MdAE  (Erreur Absolue Médiane)               : {test_metrics["MdAE"]:.2f} heures")
    print(f"\t- RMSE  (Racine de l'Erreur Quadratique Moyenne) : {test_metrics["RMSE"]:.2f} heures")
    print(f"\t- RMSLE (Erreur Logarithmique Quadratique)     : {test_metrics["RMSLE"]:.4f}")

    # Exporte le meilleur modèle entraîné dans un fichier .pkl.

    os.makedirs("models", exist_ok=True)

    with open(MODEL_OUTPUT_PATH, "wb") as f:
        pickle.dump(best_model, f)

    print(f"\nModèle sauvegardé dans : {MODEL_OUTPUT_PATH}")


if(__name__ == "__main__"):
    train_model()