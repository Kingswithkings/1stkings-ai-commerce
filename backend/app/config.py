import os
from functools import lru_cache
from pathlib import Path


def _load_env_file() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    env_path = backend_root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://global-food-webbot-cdaf.vercel.app",
    "https://naija-house-webbot.vercel.app",
    "https://1stkings-ai-commerce.vercel.app",
]


class Settings:
    def __init__(self) -> None:
        cors_origins = os.getenv("CORS_ORIGINS", "")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./store.db").strip()
        self.secret_key = os.getenv(
            "SECRET_KEY",
            "change-this-to-a-long-random-secret",
        ).strip()
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
        self.access_token_expire_hours = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "12").strip()
        )
        self.cors_origins = [
            origin.strip()
            for origin in cors_origins.split(",")
            if origin.strip()
        ] or DEFAULT_CORS_ORIGINS


@lru_cache
def get_settings() -> Settings:
    return Settings()
