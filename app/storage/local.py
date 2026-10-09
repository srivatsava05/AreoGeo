from pathlib import Path
from uuid import UUID

from app.core.config import settings


def file_directory(file_id: str) -> Path:
    # Validate IDs before using them to construct any filesystem path.
    UUID(file_id)
    return settings.data_dir / file_id
