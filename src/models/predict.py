import joblib
import numpy as np
from sentence_transformers import SentenceTransformer


# Configure les chemins pour le modèle entraîné et le modèle NLP.
MODEL_PATH = "models/resolution_time_model.pkl"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Ordre exact des 5 colonnes de ton dataset (384 + 5 = 389 features)
AUTHOR_CATEGORIES = [
    "COLLABORATOR",
    "CONTRIBUTOR",
    "MEMBER",
    "NONE",
    "OWNER"
]

class IssueTimePredictor:
    def __init__(self):
        print("Chargement du modèle NLP et du modèle LightGBM...")
        self.nlp_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.ml_model = joblib.load(MODEL_PATH)

    def predict(self, title: str, body: str, author_association: str = "NONE") -> float:
        """Prédit le temps de résolution en heures pour une nouvelle issue."""
        # 1. Préparation et vectorisation du texte (identique à cleaning.py + embeddings.py)
        full_text = f"{title} {body}".strip()
        embedding = self.nlp_model.encode(
            [full_text],
            normalize_embeddings=True
        )  # Shape: (1, 384)

        # 2. Encodage One-Hot de author_association dans l'ordre exact
        author_upper = author_association.upper()
        cat_features = np.zeros((1, len(AUTHOR_CATEGORIES)))
        if author_upper in AUTHOR_CATEGORIES:
            idx = AUTHOR_CATEGORIES.index(author_upper)
            cat_features[0, idx] = 1.0

        # 3. Fusion des features : 384 (NLP) + 5 (Catégorielles) = 389
        X = np.hstack((embedding, cat_features))

        # 4. Prédiction
        predicted_hours = self.ml_model.predict(X)[0]
        return max(0.5, float(predicted_hours))

if(__name__ == "__main__"):
    predictor = IssueTimePredictor()

    # --- Test 1 : Un bug critique ---
    titre_1 = "Crash when connecting to PostgreSQL with invalid SSL certificate"
    desc_1 = "The application throws an unhandled Segmentation Fault when SSL mode is set to verify-full."
    temps_1 = predictor.predict(titre_1, desc_1, author_association="CONTRIBUTOR")
    print(f"\n[Test 1 - Bug critique] Temps estimé : {temps_1:.1f} heures (~{temps_1/24:.1f} jours)")

    # --- Test 2 : Une petite correction de documentation ---
    titre_2 = "Fix typo in README.md installation guide"
    desc_2 = "Changed 'pyhton' to 'python' in the quickstart section."
    temps_2 = predictor.predict(titre_2, desc_2, author_association="NONE")
    print(f"[Test 2 - Typo Doc]     Temps estimé : {temps_2:.1f} heures (~{temps_2/24:.1f} jours)")