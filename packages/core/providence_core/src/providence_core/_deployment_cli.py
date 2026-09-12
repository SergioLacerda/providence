from __future__ import annotations

from providence_core._deployment_types import DeploymentResult


def _write_line(text: str = "") -> None:
    print(text)  # noqa: T201


def print_deployment_result(result: DeploymentResult) -> None:
    """Render the deployment summary for standalone CLI execution."""
    if result.get("success"):
        _write_line()
        _write_line("=" * 70)
        _write_line("🎉 PHASE 4: DEPLOYMENT COMPLETE")
        _write_line("=" * 70)
        _write_line()
        _write_line("📋 Deployment Checklist:")
        for check, status in result.get("checklist", {}).items():
            _write_line(f"  {'✅' if status else '❌'} {check}")
        _write_line()
        _write_line("📦 Deployment Location:")
        _write_line(f"  {result.get('deployment_location')}")
        _write_line()
        _write_line("📄 Artifacts Deployed:")
        for name, path in result.get("manifest", {}).get("artifacts", {}).items():
            _write_line(f"  - {name}: {path}")
        _write_line()
        _write_line("🔗 Next Steps:")
        for step in result.get("next_steps", []):
            _write_line(f"  {step}")
        _write_line()
        status_value = result.get("manifest", {}).get("status")
        _write_line(
            f"✅ Status: {status_value.upper() if isinstance(status_value, str) else 'UNKNOWN'}"
        )
        return
    _write_line()
    _write_line("❌ Deployment failed")
