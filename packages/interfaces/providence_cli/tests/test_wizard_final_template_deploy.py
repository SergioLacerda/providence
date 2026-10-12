"""`wizard` deploys the final-template through the real deploy function.

Kept apart from `test_wizard_command.py`, whose autouse fixture replaces
`_deploy_final_template` with a mock.
"""

from __future__ import annotations


def test_deploy_final_template_reports_a_stale_build_without_a_traceback(
    tmp_path, monkeypatch, capsys
) -> None:
    """A stale final-template must fail with the diagnostic and exit 1, not a
    traceback, and must write nothing into the project."""
    import json

    import click
    import pytest

    from providence_cli.commands import wizard as wizard_module

    final = tmp_path / "final-template"
    (final / ".providence" / "runtime" / "hooks").mkdir(parents=True)
    (final / ".providence" / "metadata.json").write_text(
        json.dumps({"governance_fingerprint": "abc"}), encoding="utf-8"
    )
    (final / ".providence" / "runtime" / "hooks" / "prompt-submit.py").write_text(
        "# old hook\n", encoding="utf-8"
    )
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    with pytest.raises(click.exceptions.Exit) as excinfo:
        wizard_module._deploy_final_template(final)

    assert excinfo.value.exit_code == 1
    assert "final-template is stale" in capsys.readouterr().out
    assert list(project.iterdir()) == []


def test_direct_deploy_uses_ephemeral_staging_and_runtime_uses_providence(
    tmp_path, monkeypatch
) -> None:
    import json

    from providence_cli.commands.wizard import _run_wizard
    from providence_core.utils.environment import get_sdd_paths
    from providence_wizard.contracts import WizardInvocation, WizardResult
    from providence_wizard.orchestration.phase4_governance_loader import (
        GovernanceLoader,
    )
    from providence_wizard.orchestration.wizard.seedlings_runtime import (
        _resolve_governance_paths,
    )

    project = tmp_path / "project"
    project.mkdir()
    generated_marker = project / "generated" / "keep.txt"
    generated_marker.parent.mkdir(parents=True)
    generated_marker.write_text("customer content\n", encoding="utf-8")
    monkeypatch.chdir(project)

    staging_roots = []

    def _fake_run_wizard(invocation: WizardInvocation) -> WizardResult:
        assert invocation.staging_root is not None
        staging_roots.append(invocation.staging_root)
        source = (
            invocation.staging_root
            / "client"
            / "build"
            / "final-template"
            / ".providence"
            / "source"
        )
        source.mkdir(parents=True)
        (source / "governance-core.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        (source / "governance-client.json").write_text(
            json.dumps({"items": []}), encoding="utf-8"
        )
        (source.parent / "metadata.json").write_text(
            json.dumps({"governance_fingerprint": "test-fingerprint"}),
            encoding="utf-8",
        )
        return WizardResult(success=True)

    monkeypatch.setattr("providence_wizard.contracts.run_wizard", _fake_run_wizard)
    _run_wizard(None, None, False)

    assert staging_roots
    assert not staging_roots[0].exists()
    assert generated_marker.read_text(encoding="utf-8") == "customer content\n"

    paths = get_sdd_paths(repo_root=project, workspace_root=project)
    core_path, client_path = _resolve_governance_paths(paths, project / ".providence")
    loader = GovernanceLoader(core_path, client_path)
    assert loader.load() is True
    assert core_path == project / ".providence" / "source" / "governance-core.json"
