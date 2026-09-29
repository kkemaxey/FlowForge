"""Reads the application version from GitVersion.yaml so there is one source of truth."""
from pathlib import Path

import yaml

GITVERSION_PATH = Path(__file__).resolve().parent.parent / "GitVersion.yaml"


def read_version(path: Path = GITVERSION_PATH) -> str:
    data = yaml.safe_load(path.read_text())
    return str(data["next-version"])
