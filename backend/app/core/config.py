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


settings = Settings()
