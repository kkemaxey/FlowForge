import pytest

from app.core.config import ConfigurationError, load_settings


def test_reads_database_url_and_log_level():
    settings = load_settings({"DATABASE_URL": "sqlite://", "LOG_LEVEL": "debug"})
    assert settings.database_url == "sqlite://"
    assert settings.log_level == "DEBUG"


def test_missing_database_url_fails_fast():
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        load_settings({})


def test_rejects_unknown_log_level():
    with pytest.raises(ConfigurationError):
        load_settings({"DATABASE_URL": "sqlite://", "LOG_LEVEL": "LOUD"})
