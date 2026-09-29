"""Reads the application version from GitVersion.yaml at the repository root."""
from functools import lru_cache
from pathlib import Path

import yaml

GITVERSION_FILE = Path(__file__).resolve().parents[3] / "GitVersion.yaml"


def read_version(path: Path = GITVERSION_FILE) -> str:
    with path.open() as file:
        config = yaml.safe_load(file) or {}
    version = str(config.get("next-version", "")).strip()
    if not version:
        raise ValueError(f"'next-version' is missing from {path}")
    return version


@lru_cache
def app_version() -> str:
    return read_version()
