"""SQLAlchemy engine, session factory and declarative Base shared by all modules."""
from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Column types that render as the MySQL schema wants but still work on SQLite (tests, local dev).
# SQLite only auto-increments INTEGER primary keys, so BIGINT ids fall back to INTEGER there.
BigId = BigInteger().with_variant(Integer(), "sqlite")
UnsignedInt = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
TinyInt = SmallInteger().with_variant(mysql.TINYINT(), "mysql")
Timestamp3 = DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")


def utcnow() -> datetime:
    """Naive UTC timestamp; all DATETIME(3) columns store UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    with SessionLocal() as session:
        yield session
