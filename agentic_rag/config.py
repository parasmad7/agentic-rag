import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "sample.db"
CHROMA_DIR = DATA_DIR / "chromadb"
PDF_DIR = BASE_DIR / "agentic_rag" / "sample_data" / "pdfs"
CATALOG_PATH = BASE_DIR / "agentic_rag" / "catalog" / "catalog.yaml"

IMAGE_DIR = DATA_DIR / "images"
IMAGE_DIR.mkdir(exist_ok=True)
IMAGE_DESCRIPTION_CACHE_DIR = DATA_DIR / "image_descriptions"
IMAGE_DESCRIPTION_CACHE_DIR.mkdir(exist_ok=True)
IMAGE_COLLECTION = "pdf_images"
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = "agentic_rag"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
EVAL_JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "gemini-2.5-pro")

SERVICE_ACCOUNT_KEY = BASE_DIR / "gradesmith-777-f3bddd865f41.json"
GCP_PROJECT = "gradesmith-777"
GCP_LOCATION = "us-central1"

SQL_QUERY_LIMIT = 500
SQL_QUERY_TIMEOUT = 10
