from __future__ import annotations

from pathlib import Path


DEFAULT_DATA_DIR = Path.cwd() / "data"
DEFAULT_ACCOUNT_DATA_DIR = Path.cwd() / "account_data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "genshin.sqlite3"
DEFAULT_ACCOUNT_DB_PATH = DEFAULT_ACCOUNT_DATA_DIR / "cache" / "account.sqlite3"
DEFAULT_CACHE_DIR = DEFAULT_DATA_DIR / "cache" / "characters"
DEFAULT_WEAPON_CACHE_DIR = DEFAULT_DATA_DIR / "cache" / "weapons"
DEFAULT_ARTIFACT_CACHE_DIR = DEFAULT_DATA_DIR / "cache" / "artifacts"
GENSHIN_DB_API_BASE_URL = "https://genshin-db-api.vercel.app/api/v5"


def ensure_data_dirs(
    db_path: Path = DEFAULT_DB_PATH,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
