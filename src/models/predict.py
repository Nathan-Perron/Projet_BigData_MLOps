import pickle
import numpy as np
from sentence_transformers import SentenceTransformer


# Configure les chemins pour le modèle entraîné et le modèle NLP.
MODEL_PATH = "models/resolution_time_model.pkl"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Catégories d'association d'auteur pour le one-hot encoding.
AUTHOR_CATEGORIES = [
    "COLLABORATOR",
    "CONTRIBUTOR",
    "MEMBER",
    "NONE",
    "OWNER"
]

#
# Classe qui estime le temps de résolution d'une issue en heures à partir du titre, du corps et de l'association de l'auteur.
#
class IssueTimePredictor:

    #
    # Initialise la classe en chargeant le modèle NLP et le modèle LightGBM.
    #
    def __init__(self):
        print("Chargement du modèle NLP et du modèle LightGBM...")

        self.nlp_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.ml_model = pickle.load(open(MODEL_PATH, "rb"))


    #
    # Prédit le temps de résolution en heures pour une nouvelle issue.
    #
    def predict(self, title, body, author_association="NONE"):  

        # Prépare les données pour la prédiction en suivant le même ordre que lors de l'entraînement du modèle.

        full_text = f"{title} {body}".strip()

        embedding = self.nlp_model.encode(
            [full_text],
            normalize_embeddings=True
        )

        # Encode l'association de l'auteur en one-hot encoding.

        author_upper = author_association.upper()
        features = np.zeros((1, len(AUTHOR_CATEGORIES)))

        # Si l'association de l'auteur est reconnue, on met à 1 la colonne correspondante.
        if(author_upper in AUTHOR_CATEGORIES):
            idx = AUTHOR_CATEGORIES.index(author_upper)
            features[0, idx] = 1.0

        # Fusionne les embeddings et les features catégorielles pour la prédiction.
        X = np.hstack((embedding, features))

        # Prédit le temps de résolution en heures en utilisant le modèle LightGBM.
        predicted_log = self.ml_model.predict(X)[0]
        predicted_hours = np.expm1(predicted_log)

        return max(0.5, float(predicted_hours))
    

if(__name__ == "__main__"):
    predictor = IssueTimePredictor()

    tests = [
        # 3 tests en anglais.

        {
            "label": "EN 1 - Bug critique SSL (CONTRIBUTOR)",
            "title": "Crash when connecting to PostgreSQL with invalid SSL certificate",
            "body": "The application throws an unhandled Segmentation Fault when SSL mode is set to verify-full.",
            "author": "CONTRIBUTOR"
        },
        {
            "label": "EN 2 - Typo documentation (NONE)",
            "title": "Fix typo in README.md installation guide",
            "body": "Changed 'pyhton' to 'python' in the quickstart section.",
            "author": "NONE"
        },
        {
            "label": "EN 3 - Refonte architecture lourde (OWNER)",
            "title": "Migrate authentication layer from session cookies to OAuth2 + JWT",
            "body": "We need to deprecate legacy session storage, add refresh token rotation, and update all API middlewares and unit tests.",
            "author": "OWNER"
        },

        # 2 tests en français.

        {
            "label": "FR 1 - Problème performance API (MEMBER)",
            "title": "Temps de réponse supérieur à 8 secondes sur l'endpoint /predict",
            "body": "Le modèle NLP est rechargé à chaque requête HTTP au lieu d'être mis en cache au démarrage du serveur.",
            "author": "MEMBER"
        },
        {
            "label": "FR 2 - Bug UI mineur mobile (COLLABORATOR)",
            "title": "Le bouton de validation est masqué sur petit écran mobile",
            "body": "Sur iPhone SE, la barre de navigation recouvre le bas du formulaire d'inscription et empêche de cliquer sur Envoyer.",
            "author": "COLLABORATOR"
        }
    ]

    print("\nTests de prédiction du temps de résolution pour des issues fictives :\n")

    for test in tests:
        prediction = predictor.predict(test["title"], test["body"], author_association=test["author"])
        print(f"[{test["label"]:<42}] -> {prediction:6.1f} heures (~{prediction/24:4.1f} jours)")