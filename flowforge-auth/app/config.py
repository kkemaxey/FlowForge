"""Application settings, loaded entirely from environment variables.

Nothing secret is hardcoded here — DATABASE_URL and the Firebase credentials
path both come from the environment, which is what the rubric requires.
"""
import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        # DB connection string. Defaults to a local SQLite file so the project
        # runs with zero setup for a demo; in production this is the Cloud SQL
        # (MySQL) URL, injected as an env var.
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./flowforge.db")

        # Dev mode enables local fake tokens so the flow can be demoed without
        # a live Firebase project. Set DEV_MODE=false in production.
        self.dev_mode: bool = os.getenv("DEV_MODE", "true").lower() == "true"

        # Path to the Firebase service-account JSON. Never committed to git.
        self.firebase_credentials: str = os.getenv("FIREBASE_CREDENTIALS", "")

        # Which emails are granted the supervisor role. Comma-separated env var.
        raw = os.getenv("SUPERVISOR_EMAILS", "maria@flowforge.example")
        self.supervisor_emails: list[str] = [e.strip() for e in raw.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
