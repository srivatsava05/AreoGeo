import os
from pathlib import Path

_runtime = Path(__file__).resolve().parents[1] / ".testdata"
_runtime.mkdir(exist_ok=True)
os.environ["DATA_DIR"] = str(_runtime)
os.environ["DATABASE_URL"] = f"sqlite:///{_runtime.as_posix()}/files.db"

