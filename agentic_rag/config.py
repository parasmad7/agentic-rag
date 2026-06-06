import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "sample.db"
CHROMA_DIR = DATA_DIR / "chromadb"
PDF_DIR = BASE_DIR / "agentic_rag" / "sample_data" / "pdfs"
CATALOG_PATH = BASE_DIR / "agentic_rag" / "catalog" / "catalog.yaml"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = "agentic_rag"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

SERVICE_ACCOUNT_KEY = BASE_DIR / "gradesmith-777-f3bddd865f41.json"
GCP_PROJECT = "gradesmith-777"
GCP_LOCATION = "us-central1"

SQL_QUERY_LIMIT = 500
SQL_QUERY_TIMEOUT = 10
