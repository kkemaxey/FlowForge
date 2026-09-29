import re

import pytest

from app.core.version import read_version

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_repository_version_is_semver():
    assert SEMVER.match(read_version())


def test_changelog_has_an_entry_for_the_current_version():
    from app.core.version import GITVERSION_FILE
    changelog = (GITVERSION_FILE.parent / "CHANGELOG.md").read_text()
    assert f"## [{read_version()}]" in changelog


def test_missing_next_version_is_an_error(tmp_path):
    config = tmp_path / "GitVersion.yaml"
    config.write_text("mode: ContinuousDelivery\n")
    with pytest.raises(ValueError):
        read_version(config)
