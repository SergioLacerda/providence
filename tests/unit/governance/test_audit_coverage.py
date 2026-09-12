"""Coverage tests for `providence_core.governance.audit`."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from providence_core.governance.audit import AuditIssue, GovernanceAuditor


def test_init_uses_workspace_root_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "providence_core.governance.audit.find_workspace_root", lambda: tmp_path
    )
    auditor = GovernanceAuditor()
    assert auditor.workspace_root == tmp_path


def test_perform_audit_without_workspace() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "providence_core.governance.audit.find_workspace_root", lambda: None
    )
    try:
        report = GovernanceAuditor(workspace_root=None).perform_audit()
    finally:
        monkeypatch.undo()

    assert report.ok is False
    assert report.score == 0
    assert report.issues
    assert report.issues[0].category == "Workspace"


def test_perform_audit_scores_and_calls_checks(tmp_path: Path) -> None:
    auditor = GovernanceAuditor(workspace_root=tmp_path)

    def _audit_signatures(
        ws: Path, issues: list[AuditIssue], metadata: dict[str, object]
    ) -> None:
        issues.append(AuditIssue("HIGH", "Integrity", "bad sig", "fix"))

    def _audit_paths(
        ws: Path, issues: list[AuditIssue], metadata: dict[str, object]
    ) -> None:
        issues.append(AuditIssue("LOW", "Permissions", "weak perms", "fix"))

    def _audit_env(issues: list[AuditIssue], metadata: dict[str, object]) -> None:
        metadata["signature_mode"] = "strict"

    auditor._audit_signatures = _audit_signatures  # type: ignore[method-assign]
    auditor._audit_paths = _audit_paths  # type: ignore[method-assign]
    auditor._audit_env = _audit_env  # type: ignore[method-assign]

    report = auditor.perform_audit()

    assert report.ok is True
    assert report.score == 75
    assert report.metadata["signature_mode"] == "strict"


def test_perform_audit_score_branches_for_critical_and_medium(tmp_path: Path) -> None:
    auditor = GovernanceAuditor(workspace_root=tmp_path)

    def _audit_signatures(
        ws: Path, issues: list[AuditIssue], metadata: dict[str, object]
    ) -> None:
        issues.append(AuditIssue("CRITICAL", "Integrity", "critical", "fix"))
        issues.append(AuditIssue("MEDIUM", "Permissions", "medium", "fix"))

    auditor._audit_signatures = _audit_signatures  # type: ignore[method-assign]
    auditor._audit_paths = lambda ws, issues, metadata: None  # type: ignore[method-assign]
    auditor._audit_env = lambda issues, metadata: None  # type: ignore[method-assign]

    report = auditor.perform_audit()

    assert report.score == 50
    assert report.ok is False


def test_audit_signatures_legacy_and_none_and_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auditor = GovernanceAuditor(workspace_root=tmp_path)
    compiled_dir = tmp_path / ".providence" / "compiled"
    compiled_dir.mkdir(parents=True)
    issues: list[AuditIssue] = []
    metadata: dict[str, object] = {}

    monkeypatch.setattr(
        "providence_core.governance.audit._resolve_keyring_path",
        lambda compiled_dir, strict=False: (None, "legacy", "warn"),
    )
    monkeypatch.setattr(
        "providence_core.governance.audit.validate_compiled_signatures",
        lambda compiled_dir, strict=False: [
            SimpleNamespace(ok=False),
            SimpleNamespace(ok=True),
        ],
    )

    auditor._audit_signatures(tmp_path, issues, metadata)

    assert metadata["keyring_source"] == "legacy"
    assert metadata["verified_artifacts"] == 1
    assert any(issue.severity == "MEDIUM" for issue in issues)
    assert any(issue.severity == "CRITICAL" for issue in issues)


def test_audit_signatures_none_keyring_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auditor = GovernanceAuditor(workspace_root=tmp_path)
    (tmp_path / ".providence" / "compiled").mkdir(parents=True)
    issues: list[AuditIssue] = []
    metadata: dict[str, object] = {}

    monkeypatch.setattr(
        "providence_core.governance.audit._resolve_keyring_path",
        lambda compiled_dir, strict=False: (None, "none", None),
    )
    monkeypatch.setattr(
        "providence_core.governance.audit.validate_compiled_signatures",
        lambda compiled_dir, strict=False: [],
    )

    auditor._audit_signatures(tmp_path, issues, metadata)

    assert metadata["keyring_source"] == "none"
    assert any(issue.category == "Trust" for issue in issues)
    assert any(issue.severity == "CRITICAL" for issue in issues)


def test_audit_signatures_missing_compiled_dir(tmp_path: Path) -> None:
    auditor = GovernanceAuditor(workspace_root=tmp_path)
    issues: list[AuditIssue] = []
    metadata: dict[str, object] = {}

    auditor._audit_signatures(tmp_path, issues, metadata)

    assert any(
        issue.message == "No compiled governance artifacts found" for issue in issues
    )


def test_audit_paths_and_env_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trust_dir = tmp_path / ".providence" / "trust"
    trust_dir.mkdir(parents=True, exist_ok=True)
    trust_dir.chmod(0o777)

    auditor = GovernanceAuditor(workspace_root=tmp_path)
    issues: list[AuditIssue] = []
    metadata: dict[str, object] = {}

    auditor._audit_paths(tmp_path, issues, metadata)
    assert any(issue.severity == "MEDIUM" for issue in issues)

    monkeypatch.setenv("SDD_SIGNATURE_MODE", "off")
    auditor._audit_env(issues, metadata)
    assert metadata["signature_mode"] == "off"
    assert any(issue.category == "Configuration" for issue in issues)
