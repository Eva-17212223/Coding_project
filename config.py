# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

# -------------------------------------------------------------
# ENVIRONNEMENT
# -------------------------------------------------------------
load_dotenv()  # charge les variables du fichier .env si présent

PROJECT_ROOT = Path(__file__).resolve().parent

# -------------------------------------------------------------
# CHEMINS PRINCIPAUX
# -------------------------------------------------------------
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
ANNOTATED_DIR = OUTPUT_DIR / "annotated"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Création automatique des dossiers requis
for d in [INPUT_DIR, OUTPUT_DIR, ANNOTATED_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# PARAMÈTRES DE PRÉTRAITEMENT & SEGMENTATION
# -------------------------------------------------------------
TARGET_SIZE = (1536, 1024)      # (width, height) pour normaliser les images
CLAHE_CLIP = 2.0
CLAHE_TILEGRID = (8, 8)
MORPH_KERNEL = (5, 5)
MIN_COMPONENT_AREA = 250
BORDER_CROP_PCT = 0.02
THRESH_STRATEGY = "otsu"
ADAPTIVE_BLOCK_SIZE = 75
ADAPTIVE_C = -2

# -------------------------------------------------------------
# INTERPRÉTATION DES SCORES (RAPPORT)
# -------------------------------------------------------------
LOW_DENSITY_PCT   = 10.0
MID_DENSITY_PCT_L = 10.0
MID_DENSITY_PCT_H = 30.0

# -------------------------------------------------------------
# LLM (Mistral ou OpenAI)
# -------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-tiny")
LLM_API_KEY = (
    os.getenv("MISTRAL_API_KEY")
    or os.getenv("OPENAI_API_KEY", "")
)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 600))

# -------------------------------------------------------------
# GESTION DE LA MÉMOIRE
# -------------------------------------------------------------
MEMORY_FILE = PROJECT_ROOT / "memory.json"
MEMORY_THRESHOLD_KB = 256
MEMORY_KEEP_LAST_N = 50

# -------------------------------------------------------------
# SANITY CHECKS
# -------------------------------------------------------------
MIN_SUSPICIOUS_RATIO = 0.01
MAX_SUSPICIOUS_RATIO = 0.80
REPEATABILITY_TOL = 1e-6

# -------------------------------------------------------------
# CHARGEMENT DES PROMPTS
# -------------------------------------------------------------
def load_prompts():
    """Charge les prompts depuis le fichier prompts.yaml."""
    path = PROJECT_ROOT / "prompts.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
