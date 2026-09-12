from __future__ import annotations

import json
from pathlib import Path

from providence_adapters.claude.generator import ClaudeStandaloneGenerator
from providence_core.utils.text_io import read_text_utf8

_TOPICS = (
    "architecture",
    "git-safety",
    "testing",
    "generated-artifacts",
    "go",
    "documentation",
    "token-economy",
)


def test_generate_standalone_writes_full_surface(tmp_path: Path) -> None:
    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True
    root = tmp_path / "dist" / "claude-standalone"
    assert (root / "CLAUDE.md").exists()
    assert (root / ".claude" / "settings.json").exists()
    for topic in _TOPICS:
        assert (root / ".claude" / "rules" / f"{topic}.md").exists()
    assert len(result.files_written) == 1 + 1 + len(_TOPICS)


def test_generate_standalone_settings_has_permissions_but_no_hooks(
    tmp_path: Path,
) -> None:
    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True

    settings = json.loads(
        read_text_utf8(
            tmp_path / "dist" / "claude-standalone" / ".claude" / "settings.json"
        )
    )
    assert "permissions" in settings
    assert "allow" in settings["permissions"]
    assert "deny" in settings["permissions"]
    assert "hooks" not in settings  # Decision D-2


def test_generate_standalone_is_deterministic_for_same_input(tmp_path: Path) -> None:
    r1 = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    r2 = ClaudeStandaloneGenerator().generate_standalone(
        output_dir=tmp_path, dest=tmp_path / "dist2"
    )

    a = read_text_utf8(tmp_path / "dist" / "claude-standalone" / "CLAUDE.md")
    b = read_text_utf8(tmp_path / "dist2" / "CLAUDE.md")
    assert a == b
    assert r1.success
    assert r2.success


def test_generate_standalone_never_touches_the_network(
    tmp_path: Path, monkeypatch
) -> None:
    import socket

    def _blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted during standalone generation")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = ClaudeStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True


def test_generate_standalone_against_real_repo(tmp_path: Path) -> None:
    # tests/ -> providence_adapters/ -> features/ -> packages/ -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / "pyproject.toml").exists(), (
        "sanity check: adjust the parents[] index above if the package moves"
    )

    result = ClaudeStandaloneGenerator().generate_standalone(
        output_dir=repo_root, dest=tmp_path / "claude-standalone"
    )

    assert result.success is True, result.errors
    assert (tmp_path / "claude-standalone" / "CLAUDE.md").exists()
