from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tools.release import prepare_release as prepare_release_module

PrepareReleaseError = prepare_release_module.PrepareReleaseError
main = prepare_release_module.main
prepare_changelog = prepare_release_module.prepare_changelog
prepare_readme = prepare_release_module.prepare_readme
prepare_release = prepare_release_module.prepare_release

_CHANGELOG_WITH_UNRELEASED_CONTENT = """\
# Changelog

## [Unreleased]

### Added
- something in flight

## [1.0.10] — 2026-08-25

### Added
- prior release notes
"""

_CHANGELOG_WITH_EMPTY_UNRELEASED = """\
# Changelog

## [Unreleased]

## [1.0.10] — 2026-08-25

### Added
- prior release notes
"""

_README_SNIPPET = """\
The Git-subdirectory install below is a source/development install path — it
installs the code at a specific tag rather than a released wheel. Replace `v1.0.4`
with the tag you want; omitting the `@<tag>` ref (not recommended) installs
whatever the default branch head currently is:

```bash
uv tool install "git+https://github.com/SergioLacerda/providence@v1.0.4#subdirectory=packages/interfaces/providence_cli"
```
"""


def test_prepare_changelog_inserts_header_and_moves_body(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG_WITH_UNRELEASED_CONTENT, encoding="utf-8")

    inserted = prepare_changelog(changelog, "1.0.11", today=date(2026, 8, 25))

    assert inserted is True
    text = changelog.read_text(encoding="utf-8")
    assert "## [Unreleased]\n\n## [1.0.11] — 2026-08-25\n" in text
    # the body that was under [Unreleased] moved under the new version header
    lines = text.splitlines()
    new_header_idx = lines.index("## [1.0.11] — 2026-08-25")
    assert lines[new_header_idx + 1 : new_header_idx + 4] == [
        "",
        "### Added",
        "- something in flight",
    ]
    # [Unreleased] itself is now empty (no body between it and the new header)
    unreleased_idx = lines.index("## [Unreleased]")
    assert lines[unreleased_idx + 1] == ""
    assert lines[unreleased_idx + 2] == "## [1.0.11] — 2026-08-25"


def test_prepare_changelog_rejects_empty_unreleased(tmp_path: Path) -> None:
    """Regression test: release.yml's changelog-extraction step rejects a
    version section with no content between it and the next header, even
    though the header itself exists — this bit a real v1.0.11 release
    attempt (empty [Unreleased] produced an empty [1.0.11] section)."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG_WITH_EMPTY_UNRELEASED, encoding="utf-8")

    with pytest.raises(PrepareReleaseError, match="no entries"):
        prepare_changelog(changelog, "1.0.11", today=date(2026, 8, 25))

    # rejected before any write
    assert changelog.read_text(encoding="utf-8") == _CHANGELOG_WITH_EMPTY_UNRELEASED


def test_prepare_changelog_is_idempotent_for_existing_version(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(_CHANGELOG_WITH_EMPTY_UNRELEASED, encoding="utf-8")

    inserted = prepare_changelog(changelog, "1.0.10", today=date(2026, 8, 25))

    assert inserted is False
    # file is untouched — no duplicate "## [1.0.10]" section
    text = changelog.read_text(encoding="utf-8")
    assert text.count("## [1.0.10]") == 1


def test_prepare_changelog_missing_unreleased_header_raises(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [1.0.10] — 2026-08-25\n", encoding="utf-8")

    with pytest.raises(PrepareReleaseError, match="Unreleased"):
        prepare_changelog(changelog, "1.0.11", today=date(2026, 8, 25))


def test_prepare_readme_replaces_prose_and_install_tag(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(_README_SNIPPET, encoding="utf-8")

    updated = prepare_readme(readme, "1.0.11")

    assert updated is True
    text = readme.read_text(encoding="utf-8")
    assert "Replace `v1.0.11`" in text
    assert "@v1.0.11#subdirectory=packages/interfaces/providence_cli" in text
    assert "v1.0.4" not in text


def test_prepare_readme_is_noop_when_already_current(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(_README_SNIPPET.replace("1.0.4", "1.0.11"), encoding="utf-8")

    updated = prepare_readme(readme, "1.0.11")

    assert updated is False


def test_prepare_readme_missing_anchor_raises(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# No install snippet here\n", encoding="utf-8")

    with pytest.raises(PrepareReleaseError, match="anchors not found"):
        prepare_readme(readme, "1.0.11")


def test_prepare_release_rejects_invalid_version(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    readme = tmp_path / "README.md"
    changelog.write_text(_CHANGELOG_WITH_EMPTY_UNRELEASED, encoding="utf-8")
    readme.write_text(_README_SNIPPET, encoding="utf-8")

    with pytest.raises(PrepareReleaseError, match="invalid version"):
        prepare_release(
            "v1.0.11",  # 'v' prefix not allowed — version must be bare
            changelog_path=changelog,
            readme_path=readme,
        )
    # rejected before any write
    assert changelog.read_text(encoding="utf-8") == _CHANGELOG_WITH_EMPTY_UNRELEASED
    assert readme.read_text(encoding="utf-8") == _README_SNIPPET


def test_prepare_release_updates_both_files(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    readme = tmp_path / "README.md"
    changelog.write_text(_CHANGELOG_WITH_UNRELEASED_CONTENT, encoding="utf-8")
    readme.write_text(_README_SNIPPET, encoding="utf-8")

    result = prepare_release(
        "1.0.11",
        changelog_path=changelog,
        readme_path=readme,
        today=date(2026, 8, 25),
    )

    assert result.changelog_header_inserted is True
    assert result.readme_updated is True
    assert "## [1.0.11] — 2026-08-25" in changelog.read_text(encoding="utf-8")
    assert "v1.0.11" in readme.read_text(encoding="utf-8")


def test_main_reports_error_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    readme = tmp_path / "README.md"
    changelog.write_text("# Changelog\n\nno unreleased header\n", encoding="utf-8")
    readme.write_text(_README_SNIPPET, encoding="utf-8")

    monkeypatch.setattr(prepare_release_module, "REPO_ROOT", tmp_path)

    rc = main(["--version", "1.0.11"])

    assert rc == 1
    assert "ERROR" in capsys.readouterr().err
