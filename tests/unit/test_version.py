from app.version import GITVERSION_PATH, read_version


def test_read_version_returns_next_version(tmp_path):
    gitversion_file = tmp_path / "GitVersion.yaml"
    gitversion_file.write_text("mode: ContinuousDelivery\nnext-version: 1.2.3\n")

    assert read_version(gitversion_file) == "1.2.3"


def test_changelog_has_entry_for_current_version():
    version = read_version(GITVERSION_PATH)
    changelog = (GITVERSION_PATH.parent / "CHANGELOG.md").read_text()

    assert f"## [{version}]" in changelog
