"""Tests for CopilotStandaloneGenerator (Soft/Standalone GitHub Copilot governance projection)."""

from __future__ import annotations

from pathlib import Path

from providence_adapters.copilot.generator import CopilotStandaloneGenerator

_TOPICS = (
    "architecture",
    "git-safety",
    "testing",
    "generated-artifacts",
    "go",
    "documentation",
    "token-economy",
)

_EXPECTED_FILES = [".github/copilot-instructions.md"] + [
    f".github/instructions/{topic}.instructions.md" for topic in _TOPICS
]


def test_generate_standalone_writes_full_surface(tmp_path: Path) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True, result.errors
    root = tmp_path / "dist" / "copilot-standalone"
    for rel_path in _EXPECTED_FILES:
        assert (root / rel_path).exists(), f"missing {rel_path}"
        assert (root / rel_path).stat().st_size > 0

    written = {Path(p).relative_to(root).as_posix() for p in result.files_written}
    assert written == set(_EXPECTED_FILES)

    # Never written to the project's real .github/ files.
    assert not (tmp_path / ".github").exists()

    # Python was removed â€” Go-only for now.
    assert not (root / ".github" / "instructions" / "python.instructions.md").exists()


def test_generate_standalone_accepts_custom_dest(tmp_path: Path) -> None:
    custom_dest = tmp_path / "custom-out"

    result = CopilotStandaloneGenerator().generate_standalone(
        output_dir=tmp_path, dest=custom_dest
    )

    assert result.success is True, result.errors
    assert (custom_dest / ".github" / "copilot-instructions.md").exists()


def test_generate_standalone_is_deterministic_for_same_input(tmp_path: Path) -> None:
    generator = CopilotStandaloneGenerator()
    r1 = generator.generate_standalone(output_dir=tmp_path, dest=tmp_path / "a")
    r2 = generator.generate_standalone(output_dir=tmp_path, dest=tmp_path / "b")

    assert r1.success is True
    assert r2.success is True
    for rel_path in _EXPECTED_FILES:
        a = (tmp_path / "a" / rel_path).read_text(encoding="utf-8")
        b = (tmp_path / "b" / rel_path).read_text(encoding="utf-8")
        assert a == b


def test_generate_standalone_overwrites_its_own_prior_output(tmp_path: Path) -> None:
    generator = CopilotStandaloneGenerator()
    r1 = generator.generate_standalone(output_dir=tmp_path)
    r2 = generator.generate_standalone(output_dir=tmp_path)

    assert r1.success is True, r1.errors
    assert r2.success is True, r2.errors


def test_generate_standalone_instructions_have_applyto_frontmatter(
    tmp_path: Path,
) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    instructions_dir = (
        tmp_path / "dist" / "copilot-standalone" / ".github" / "instructions"
    )
    go_content = (instructions_dir / "go.instructions.md").read_text(encoding="utf-8")
    testing_content = (instructions_dir / "testing.instructions.md").read_text(
        encoding="utf-8"
    )
    architecture_content = (
        instructions_dir / "architecture.instructions.md"
    ).read_text(encoding="utf-8")
    token_economy_content = (
        instructions_dir / "token-economy.instructions.md"
    ).read_text(encoding="utf-8")

    assert 'applyTo: "**/*.go"' in go_content
    assert 'applyTo: "**/*.go"' in testing_content  # narrowed per TE-3
    assert 'applyTo: "**"' in architecture_content
    assert 'applyTo: "**"' in token_economy_content


def test_generate_standalone_rule_content_matches_expected_topics(
    tmp_path: Path,
) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    instructions_dir = (
        tmp_path / "dist" / "copilot-standalone" / ".github" / "instructions"
    )
    assert "Red-Green-Refactor" in (
        instructions_dir / "testing.instructions.md"
    ).read_text(encoding="utf-8")
    go_content = (instructions_dir / "go.instructions.md").read_text(encoding="utf-8")
    assert "golangci-lint" in go_content
    assert "govulncheck" in go_content  # CQ-3 dependency version hygiene
    assert "hand-edit" in (
        instructions_dir / "generated-artifacts.instructions.md"
    ).read_text(encoding="utf-8")
    assert (
        "git"
        in (instructions_dir / "git-safety.instructions.md")
        .read_text(encoding="utf-8")
        .lower()
    )
    architecture_content = (
        instructions_dir / "architecture.instructions.md"
    ).read_text(encoding="utf-8")
    assert "Naming" in architecture_content
    assert "Error Handling" in architecture_content  # CQ-1
    assert "Security" in architecture_content  # CQ-2
    assert "WHY" in (instructions_dir / "documentation.instructions.md").read_text(
        encoding="utf-8"
    )
    assert "Context Window Discipline" in (
        instructions_dir / "token-economy.instructions.md"
    ).read_text(encoding="utf-8")


def test_generate_standalone_output_never_mentions_sdd(tmp_path: Path) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    root = tmp_path / "dist" / "copilot-standalone"
    for rel_path in _EXPECTED_FILES:
        content = (root / rel_path).read_text(encoding="utf-8")
        assert "sdd" not in content.lower(), f"{rel_path} mentions sdd"


def test_generate_standalone_discloses_hook_and_config_gaps(tmp_path: Path) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    content = (
        tmp_path / "dist" / "copilot-standalone" / ".github" / "copilot-instructions.md"
    ).read_text(encoding="utf-8")
    assert "hook" in content.lower()
    assert "config" in content.lower() or "permissions" in content.lower()


def test_generate_standalone_root_manifest_has_priority_and_self_check(
    tmp_path: Path,
) -> None:
    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)
    assert result.success is True, result.errors

    content = (
        tmp_path / "dist" / "copilot-standalone" / ".github" / "copilot-instructions.md"
    ).read_text(encoding="utf-8")
    assert "Compliance Priority" in content
    assert "Self-Check" in content


def test_generate_standalone_never_touches_the_network(
    tmp_path: Path, monkeypatch
) -> None:
    import socket

    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access attempted during standalone generation")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    result = CopilotStandaloneGenerator().generate_standalone(output_dir=tmp_path)

    assert result.success is True, result.errors
