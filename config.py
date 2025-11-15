# config.py

from sqlalchemy.engine.url import URL

# --- Paramètres de connexion PostgreSQL ---
DB_NAME = "db_sco"
DB_USER = "postgres"
DB_PASS = "5864"# À VÉRIFIER
DB_HOST = "localhost" 
DB_PORT = 5432
# ----------------------------------------

# --- Chemins vers les fichiers Excel ---
# ⚠️ Nouveau chemin pour les Institutions
INSTITUTION_FILE_PATH = r"C:\Users\OCELOU\Desktop\UF_DSE_DRIVE\UF_datasets\POWERQUERY\Institutions_Base.xlsx"

METADATA_FILE_PATH = r"C:\Users\OCELOU\Desktop\UF_DSE_DRIVE\UF_datasets\PYTHON\Composante_Mention_Parcours_2025.xlsx"
INSCRIPTION_FILE_PATH = r"C:\Users\OCELOU\Desktop\UF_DSE_DRIVE\UF_datasets\POWERQUERY\_UFALLTIME__KEYED.xlsx"
# ----------------------------------------

# --- Chemins vers les dossiers de ressources statiques ---
# 🖼️ Nouveau chemin pour le dossier des logos
LOGO_FOLDER_PATH = r"C:\Users\OCELOU\Desktop\UF_DSE_DRIVE\UF_datasets\POWERQUERY\db_sco\logo"
# ----------------------------------------

# --- URLs de Connexion (avec correction d'encodage) ---
# Ajout de client_encoding=windows-1252 dans la Query String pour la robustesse

# URL pour la BDD cible
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8"

# URL pour la BDD par défaut (utile pour la création de la BDD cible)
DEFAULT_DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/postgres?client_encoding=utf8"