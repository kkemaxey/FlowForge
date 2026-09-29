"""Reads the application version from GitVersion.yaml so there is one source of truth."""
from pathlib import Path

import yaml


def _find_gitversion() -> Path:
    for directory in Path(__file__).resolve().parents:
        candidate = directory / "GitVersion.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("GitVersion.yaml not found in any parent directory")


GITVERSION_PATH = _find_gitversion()


def read_version(path: Path = GITVERSION_PATH) -> str:
    data = yaml.safe_load(path.read_text())
    return str(data["next-version"])
