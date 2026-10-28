"""Environment-backed configuration."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:8000")
    api_token: str = os.getenv("API_TOKEN", "demo-token")
    database_path: str = os.getenv("DATABASE_PATH", "data/ingestion.sqlite")
    raw_dir: str = os.getenv("RAW_DIR", "artifacts/raw")
    quarantine_dir: str = os.getenv("QUARANTINE_DIR", "artifacts/quarantine")
    reports_dir: str = os.getenv("REPORTS_DIR", "artifacts/reports")
    page_size: int = int(os.getenv("PAGE_SIZE", "100"))
    timeout: float = float(os.getenv("REQUEST_TIMEOUT", "5"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    backoff_base: float = float(os.getenv("BACKOFF_BASE", "0.1"))
