import pytest

from app.config import Settings, load_settings


def test_load_settings_reads_values_from_environment():
    settings = load_settings({
        "DATABASE_URL": "sqlite://",
        "LOG_LEVEL": "debug",
        "GRID_WIDTH": "30",
        "GRID_HEIGHT": "15",
    })

    assert settings == Settings(
        database_url="sqlite://", log_level="DEBUG", grid_width=30, grid_height=15
    )


def test_load_settings_applies_defaults():
    settings = load_settings({"DATABASE_URL": "sqlite://"})

    assert settings.log_level == "INFO"
    assert settings.grid_width == 20
    assert settings.grid_height == 12


def test_load_settings_requires_database_url():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        load_settings({})
