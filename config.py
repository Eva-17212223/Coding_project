# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml

# -------------------------------------------------------------
# ENVIRONMENT
# -------------------------------------------------------------
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent

# -------------------------------------------------------------
# MAIN PATHS
# -------------------------------------------------------------
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
ANNOTATED_DIR = OUTPUT_DIR / "annotated"
REPORTS_DIR = OUTPUT_DIR / "reports"

for d in [INPUT_DIR, OUTPUT_DIR, ANNOTATED_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# PREPROCESSING PARAMETERS
# -------------------------------------------------------------
TARGET_SIZE = (1536, 1024)
CLAHE_CLIP = 2.0
CLAHE_TILEGRID = (8, 8)
MORPH_KERNEL = (5, 5)
MIN_COMPONENT_AREA = 250
BORDER_CROP_PCT = 0.02
THRESH_STRATEGY = "otsu"
ADAPTIVE_BLOCK_SIZE = 75
ADAPTIVE_C = -2

# -------------------------------------------------------------
# INTERPRETATION CONSTANTS
# -------------------------------------------------------------
LOW_DENSITY_PCT   = 10.0
MID_DENSITY_PCT_L = 10.0
MID_DENSITY_PCT_H = 30.0

MIN_SUSPICIOUS_RATIO = 0.01
MAX_SUSPICIOUS_RATIO = 0.80
REPEATABILITY_TOL = 1e-6

# -------------------------------------------------------------
# MEMORY MANAGEMENT
# -------------------------------------------------------------
MEMORY_FILE = PROJECT_ROOT / "memory.json"
MEMORY_THRESHOLD_KB = 256
MEMORY_KEEP_LAST_N = 50

# -------------------------------------------------------------
# LLM CONFIGURATION
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
# GMAIL API (OAuth2)
# -------------------------------------------------------------
# The credentials.json file you uploaded
GOOGLE_CREDENTIALS_PATH = PROJECT_ROOT / "client_secret_796590494168-6p357l9pjgm1n7rhbiccutm5nc2p4pkn.apps.googleusercontent.com.json"

# Will be created automatically after first OAuth login
GOOGLE_TOKEN_PATH = PROJECT_ROOT / "token.json"

# Sender email (your Gmail address)
SENDER_EMAIL = "debdeh7@gmail.com"

# -------------------------------------------------------------
# PROMPTS LOADING
# -------------------------------------------------------------
def load_prompts():
    path = PROJECT_ROOT / "prompts.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
