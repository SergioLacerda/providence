"""Contract tests for subprocess execution policy in runtime skills engine."""

from pathlib import Path


def test_skills_runtime_does_not_fallback_to_subprocess_run() -> None:
    executor_dir = Path(
        "packages/core/providence_runtime/src/providence_runtime/_skill_executor"
    )
    executor_content = "\n".join(
        module.read_text(encoding="utf-8") for module in executor_dir.glob("*.py")
    )
    assert "SafeProcessRunner" in executor_content
    assert "subprocess.run(" not in executor_content
