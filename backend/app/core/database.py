"""SQLAlchemy engine and session management."""
import logging
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger("flowforge.database")


class Base(DeclarativeBase):
    pass


class Database:
    """Owns one engine and hands out sessions to request handlers."""

    def __init__(self, database_url: str):
        engine_options = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
        self.engine: Engine = create_engine(database_url, **engine_options)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def is_reachable(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            logger.exception("database connectivity check failed")
            return False

    def session(self) -> Iterator[Session]:
        """Yield a session that commits on success and rolls back on error."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
