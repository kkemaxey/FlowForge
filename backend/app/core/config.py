"""Application settings, read from environment variables (and a local .env file).

Credentials never live in code: DATABASE_URL must come from the environment.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigurationError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str = "INFO"


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    """Build Settings from the given mapping, or from os.environ plus .env."""
    if environ is None:
        load_dotenv()
        environ = dict(os.environ)

    database_url = environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise ConfigurationError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )

    log_level = environ.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in VALID_LOG_LEVELS:
        raise ConfigurationError(f"LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}")

    return Settings(database_url=database_url, log_level=log_level)
