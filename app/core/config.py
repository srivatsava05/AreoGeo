import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/files.db")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "100")) * 1024 * 1024
    max_features: int = int(os.getenv("MAX_FEATURES", "100000"))
    api_prefix: str = "/api"


settings = Settings()
