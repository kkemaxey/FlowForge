"""Integration tests drop every table when they finish, so they may only run against throwaway databases."""
from sqlalchemy.engine import make_url

IN_MEMORY_SQLITE_URLS = ("sqlite://", "sqlite:///:memory:")


def is_disposable_database(database_url: str) -> bool:
    if database_url in IN_MEMORY_SQLITE_URLS:
        return True
    database_name = make_url(database_url).database or ""
    return "test" in database_name.lower()
