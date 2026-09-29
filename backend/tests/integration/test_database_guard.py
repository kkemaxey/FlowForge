import pytest

from tests.integration.database_guard import is_disposable_database


@pytest.mark.parametrize("database_url", [
    "sqlite://",
    "sqlite:///:memory:",
    "sqlite:///./flowforge_test.db",
    "mysql+pymysql://app:secret@127.0.0.1:3306/flowforge_test",
    "mysql+pymysql://app:secret@127.0.0.1:3306/TEST_flowforge",
])
def test_throwaway_databases_are_allowed(database_url):
    assert is_disposable_database(database_url) is True


@pytest.mark.parametrize("database_url", [
    "mysql+pymysql://app:secret@127.0.0.1:3306/flowforge",
    "sqlite:///./flowforge.db",
    "mysql+pymysql://app:secret@127.0.0.1:3306",
])
def test_real_databases_are_refused(database_url):
    assert is_disposable_database(database_url) is False
