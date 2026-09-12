from __future__ import annotations

from providence_wizard.orchestration.install_snapshot import GovernanceInstallSnapshot


class _FakeCompiler:
    def __init__(self) -> None:
        self.mandates = [{"id": "M001", "title": "Clean Architecture"}]
        self.guidelines = {"G001": {"id": "G001"}}
        self.guidelines_by_category = {"testing": [{"id": "G001"}]}
        self.governance_fingerprint = "abc12345"
        self.generated_at = "2026-07-04T00:00:00Z"


def test_from_compiler_wraps_all_fields_without_recomputation() -> None:
    compiler = _FakeCompiler()

    snapshot = GovernanceInstallSnapshot.from_compiler(compiler)  # type: ignore[arg-type]

    assert snapshot.mandates == compiler.mandates
    assert snapshot.guidelines == compiler.guidelines
    assert snapshot.guidelines_by_category == compiler.guidelines_by_category
    assert snapshot.governance_fingerprint == compiler.governance_fingerprint
    assert snapshot.generated_at == compiler.generated_at


def test_from_compiler_derives_mandate_bookkeeping_with_safe_defaults() -> None:
    compiler = _FakeCompiler()

    snapshot = GovernanceInstallSnapshot.from_compiler(compiler)  # type: ignore[arg-type]

    assert snapshot.mandates_count == 1
    assert snapshot.mandate_ids == ["M001"]
    assert snapshot.fingerprint_source == "compiler.governance_fingerprint"
    assert snapshot.workspace_root == "unknown"
    assert snapshot.handshake_mode == "standard"
    assert snapshot.selected_agents == []
    assert snapshot.hook_agents == []
    assert snapshot.generated_surfaces == []
    assert snapshot.schema_version == "1"


def test_from_compiler_accepts_explicit_wizard_context() -> None:
    compiler = _FakeCompiler()

    snapshot = GovernanceInstallSnapshot.from_compiler(  # type: ignore[arg-type]
        compiler,
        workspace_root="/repo",
        handshake_mode="hook",
        selected_agents=["claude", "codex"],
        hook_agents=["claude", "codex", "gemini"],
        generated_surfaces=["AGENTS.md", "CLAUDE.md"],
    )

    assert snapshot.workspace_root == "/repo"
    assert snapshot.handshake_mode == "hook"
    assert snapshot.selected_agents == ["claude", "codex"]
    assert snapshot.hook_agents == ["claude", "codex", "gemini"]
    assert snapshot.generated_surfaces == ["AGENTS.md", "CLAUDE.md"]


def test_snapshot_is_frozen() -> None:
    snapshot = GovernanceInstallSnapshot()

    try:
        snapshot.governance_fingerprint = "mutated"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("GovernanceInstallSnapshot must be immutable")
