"""App settings, read from environment variables (and backend/.env locally)."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./flowforge.db")
        self.cors_origins: list[str] = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        ]
        self.firebase_credentials: str = os.getenv("FIREBASE_CREDENTIALS", "")
        # Background assigner pass. Off unless enabled; docker-compose.yml turns it on.
        self.assigner_loop_enabled: bool = os.getenv("ASSIGNER_LOOP_ENABLED", "false").lower() in ("1", "true", "yes")
        self.assigner_interval_seconds: float = float(os.getenv("ASSIGNER_INTERVAL_SECONDS", "2"))


settings = Settings()
