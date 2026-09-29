"""Application settings, read from environment variables (and .env when present)."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str = "INFO"
    grid_width: int = 20
    grid_height: int = 12


def load_settings(environ: Optional[Mapping[str, str]] = None) -> Settings:
    if environ is None:
        load_dotenv()
        environ = os.environ

    database_url = environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )

    return Settings(
        database_url=database_url,
        log_level=environ.get("LOG_LEVEL", "INFO").upper(),
        grid_width=int(environ.get("GRID_WIDTH", "20")),
        grid_height=int(environ.get("GRID_HEIGHT", "12")),
    )
