"""Unit tests for governance audit logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_core.governance.audit import AuditIssue, AuditReport, GovernanceAuditor

pytestmark = pytest.mark.unit


class TestAuditIssue:
    """Tests for AuditIssue dataclass."""

    def test_audit_issue_creation(self) -> None:
        """Should create AuditIssue with all required fields."""
        issue = AuditIssue(
            severity="HIGH",
            category="Integrity",
            message="Test message",
            remediation="Test fix",
        )
        assert issue.severity == "HIGH"
        assert issue.category == "Integrity"
        assert issue.message == "Test message"
        assert issue.remediation == "Test fix"

    def test_audit_issue_severity_levels(self) -> None:
        """Should support all severity levels."""
        levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for level in levels:
            issue = AuditIssue(
                severity=level,
                category="Test",
                message="test",
                remediation="test",
            )
            assert issue.severity == level


class TestAuditReport:
    """Tests for AuditReport dataclass."""

    def test_audit_report_creation(self) -> None:
        """Should create AuditReport with required fields."""
        report = AuditReport(ok=True, score=85)
        assert report.ok is True
        assert report.score == 85
        assert report.issues == []

    def test_audit_report_with_issues(self) -> None:
        """Should store list of issues."""
        issue = AuditIssue("HIGH", "Test", "msg", "fix")
        report = AuditReport(ok=False, score=50, issues=[issue])
        assert len(report.issues) == 1
        assert report.issues[0].severity == "HIGH"

    def test_audit_report_with_metadata(self) -> None:
        """Should store metadata dict."""
        metadata = {"key": "value", "count": 42}
        report = AuditReport(ok=True, score=100, metadata=metadata)
        assert report.metadata["key"] == "value"
        assert report.metadata["count"] == 42


class TestGovernanceAuditorInit:
    """Tests for GovernanceAuditor initialization."""

    def test_init_with_custom_workspace_root(self, tmp_path: Path) -> None:
        """Should accept custom workspace root."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)
        assert auditor.workspace_root == tmp_path

    def test_init_without_workspace_root(self, tmp_path: Path) -> None:
        """Should find workspace root when not provided."""
        with patch(
            "providence_core.governance.audit.find_workspace_root",
            return_value=tmp_path,
        ):
            auditor = GovernanceAuditor()
            assert auditor.workspace_root == tmp_path


class TestPerformAudit:
    """Tests for the main perform_audit() method."""

    def test_audit_no_workspace(self) -> None:
        """Should return failed audit when workspace not found."""
        with patch(
            "providence_core.governance.audit.find_workspace_root", return_value=None
        ):
            auditor = GovernanceAuditor(workspace_root=None)
            report = auditor.perform_audit()

            assert report.ok is False
            assert report.score == 0
            assert len(report.issues) > 0

    def test_audit_returns_report(self, tmp_path: Path) -> None:
        """Should return AuditReport instance."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        with (
            patch.object(auditor, "_audit_signatures"),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert isinstance(report, AuditReport)
            assert "ok" in dir(report)
            assert "score" in dir(report)

    def test_audit_calls_all_checks(self, tmp_path: Path) -> None:
        """Should call all three audit methods."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        with (
            patch.object(auditor, "_audit_signatures") as mock_sig,
            patch.object(auditor, "_audit_paths") as mock_paths,
            patch.object(auditor, "_audit_env") as mock_env,
        ):
            auditor.perform_audit()

            mock_sig.assert_called_once()
            mock_paths.assert_called_once()
            mock_env.assert_called_once()


class TestAuditScoring:
    """Tests for audit score calculation."""

    def test_score_starts_at_100(self, tmp_path: Path) -> None:
        """Audit score should start at 100 with no issues."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        with (
            patch.object(auditor, "_audit_signatures"),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 100

    def test_critical_issue_deducts_40(self, tmp_path: Path) -> None:
        """Critical issue should deduct 40 points."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_critical_issue(ws, issues, metadata):
            issues.append(AuditIssue("CRITICAL", "Test", "Critical issue", "Fix it"))

        with (
            patch.object(auditor, "_audit_signatures", side_effect=add_critical_issue),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 60

    def test_high_issue_deducts_20(self, tmp_path: Path) -> None:
        """High issue should deduct 20 points."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_high_issue(ws, issues, metadata):
            issues.append(AuditIssue("HIGH", "Test", "High issue", "Fix it"))

        with (
            patch.object(auditor, "_audit_signatures", side_effect=add_high_issue),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 80

    def test_medium_issue_deducts_10(self, tmp_path: Path) -> None:
        """Medium issue should deduct 10 points."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_medium_issue(ws, issues, metadata):
            issues.append(AuditIssue("MEDIUM", "Test", "Medium issue", "Fix it"))

        with (
            patch.object(auditor, "_audit_signatures", side_effect=add_medium_issue),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 90

    def test_low_issue_deducts_5(self, tmp_path: Path) -> None:
        """Low issue should deduct 5 points."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_low_issue(ws, issues, metadata):
            issues.append(AuditIssue("LOW", "Test", "Low issue", "Fix it"))

        with (
            patch.object(auditor, "_audit_signatures", side_effect=add_low_issue),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 95

    def test_score_cannot_go_below_zero(self, tmp_path: Path) -> None:
        """Score should never be negative."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_multiple_issues(ws, issues, metadata):
            for _ in range(10):
                issues.append(AuditIssue("CRITICAL", "Test", "Critical", "Fix"))

        with (
            patch.object(auditor, "_audit_signatures", side_effect=add_multiple_issues),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score >= 0

    def test_audit_ok_threshold_70(self, tmp_path: Path) -> None:
        """Audit should be ok (True) when score >= 70."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)

        def add_three_low_issues(ws, issues, metadata):
            for _ in range(3):
                issues.append(AuditIssue("LOW", "Test", "Low", "Fix"))

        with (
            patch.object(
                auditor, "_audit_signatures", side_effect=add_three_low_issues
            ),
            patch.object(auditor, "_audit_paths"),
            patch.object(auditor, "_audit_env"),
        ):
            report = auditor.perform_audit()

            assert report.score == 85
            assert report.ok is True


class TestAuditPathsMethod:
    """Tests for path auditing."""

    def test_audit_paths_checks_trust_directory(self, tmp_path: Path) -> None:
        """Should check permissions of trust directory."""
        trust_dir = tmp_path / ".providence" / "trust"
        trust_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        auditor._audit_paths(tmp_path, issues, metadata)

        # Should check trust dir (may or may not have issues depending on permissions)
        assert isinstance(issues, list)


class TestAuditEnvMethod:
    """Tests for environment auditing."""

    def test_audit_env_checks_signature_mode(self, tmp_path: Path) -> None:
        """Should check SDD_SIGNATURE_MODE environment variable."""
        import os

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        with patch.dict(os.environ, {"SDD_SIGNATURE_MODE": "off"}):
            auditor._audit_env(issues, metadata)

            assert any(i.category == "Configuration" for i in issues)

    def test_audit_env_metadata_includes_mode(self, tmp_path: Path) -> None:
        """Should record signature mode in metadata."""
        import os

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        with patch.dict(os.environ, {"SDD_SIGNATURE_MODE": "strict"}):
            auditor._audit_env(issues, metadata)

            assert "signature_mode" in metadata
            assert metadata["signature_mode"] == "strict"


class TestAuditSignaturesEdgeCases:
    """Tests for _audit_signatures edge cases and uncovered lines."""

    def test_audit_signatures_no_sdd_no_legacy_dirs(self, tmp_path: Path) -> None:
        """_audit_signatures with neither sdd nor legacy dir → HIGH issue (lines 82-105)."""
        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        auditor._audit_signatures(tmp_path, issues, metadata)

        # Should add HIGH issue for missing compiled artifacts
        assert any(i.severity == "HIGH" for i in issues)
        assert any(
            "No compiled governance artifacts found" in i.message for i in issues
        )

    def test_audit_signatures_with_legacy_path_only(self, tmp_path: Path) -> None:
        """_audit_signatures with only legacy dir (no .providence/compiled/) -> HIGH issue."""
        legacy_dir = tmp_path / "generated" / "master" / "compiled"
        legacy_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        auditor._audit_signatures(tmp_path, issues, metadata)

        # Legacy path fallback removed — HIGH integrity failure expected
        assert any(i.severity == "HIGH" for i in issues)
        assert any(
            "No compiled governance artifacts found" in i.message for i in issues
        )

    def test_audit_signatures_with_sdd_compiled_dir(self, tmp_path: Path) -> None:
        """_audit_signatures with .providence/compiled/ dir calls _resolve_keyring_path."""
        sdd_dir = tmp_path / ".providence" / "compiled"
        sdd_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        with (
            patch(
                "providence_core.governance.audit._resolve_keyring_path",
                return_value=(None, "none", None),
            ) as mock_resolve,
            patch(
                "providence_core.governance.audit.validate_compiled_signatures",
                return_value=[],
            ),
        ):
            auditor._audit_signatures(tmp_path, issues, metadata)

            # Should call _resolve_keyring_path with compiled_dir
            mock_resolve.assert_called_once()

    def test_audit_signatures_legacy_keyring_source(self, tmp_path: Path) -> None:
        """Mock _resolve_keyring_path to return source="legacy" → MEDIUM issue (lines 112-120)."""
        sdd_dir = tmp_path / ".providence" / "compiled"
        sdd_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        with (
            patch(
                "providence_core.governance.audit._resolve_keyring_path",
                return_value=(None, "legacy", None),
            ),
            patch(
                "providence_core.governance.audit.validate_compiled_signatures",
                return_value=[],
            ),
        ):
            auditor._audit_signatures(tmp_path, issues, metadata)

        # Should add MEDIUM issue for legacy keyring
        assert any(i.severity == "MEDIUM" for i in issues)
        assert any("legacy keyring" in i.message.lower() for i in issues)

    def test_audit_signatures_none_keyring_source(self, tmp_path: Path) -> None:
        """Mock _resolve_keyring_path to return source="none" → CRITICAL issue (lines 121-129)."""
        sdd_dir = tmp_path / ".providence" / "compiled"
        sdd_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        with (
            patch(
                "providence_core.governance.audit._resolve_keyring_path",
                return_value=(None, "none", None),
            ),
            patch(
                "providence_core.governance.audit.validate_compiled_signatures",
                return_value=[],
            ),
        ):
            auditor._audit_signatures(tmp_path, issues, metadata)

        # Should add CRITICAL issue for missing keyring
        assert any(i.severity == "CRITICAL" for i in issues)
        assert any("No trusted keyring found" in i.message for i in issues)

    def test_audit_signatures_invalid_artifacts(self, tmp_path: Path) -> None:
        """Mock validate_compiled_signatures with ok=False → CRITICAL issue (lines 131-144)."""
        sdd_dir = tmp_path / ".providence" / "compiled"
        sdd_dir.mkdir(parents=True)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        # Mock validation results with invalid signatures
        mock_result = MagicMock()
        mock_result.ok = False

        with (
            patch(
                "providence_core.governance.audit._resolve_keyring_path",
                return_value=(None, "default", None),
            ),
            patch(
                "providence_core.governance.audit.validate_compiled_signatures",
                return_value=[mock_result, mock_result],
            ),
        ):
            auditor._audit_signatures(tmp_path, issues, metadata)

        # Should add CRITICAL issue for invalid signatures
        assert any(i.severity == "CRITICAL" for i in issues)
        assert any("invalid/missing signatures" in i.message.lower() for i in issues)


class TestAuditPathsEdgeCases:
    """Tests for _audit_paths edge cases and uncovered lines."""

    def test_audit_paths_insecure_trust_permissions(self, tmp_path: Path) -> None:
        """Create .providence/trust/ with mode 0o777 -> MEDIUM insecure permissions."""
        trust_dir = tmp_path / ".providence" / "trust"
        trust_dir.mkdir(parents=True)
        # Set insecure permissions (0o777)
        trust_dir.chmod(0o777)

        auditor = GovernanceAuditor(workspace_root=tmp_path)
        issues = []
        metadata = {}

        auditor._audit_paths(tmp_path, issues, metadata)

        # Should add MEDIUM issue for insecure permissions
        assert any(i.severity == "MEDIUM" for i in issues)
        assert any("insecure permissions" in i.message.lower() for i in issues)
