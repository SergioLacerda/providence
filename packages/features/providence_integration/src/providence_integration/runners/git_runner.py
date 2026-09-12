"""Git Runner."""

from pathlib import Path

from providence_integration.engine.types import GitCommitInputs, RuntimeContext


def run_git_commit(
    inputs: GitCommitInputs, context: RuntimeContext, spec_dir: Path
) -> None:
    """Run Git Commit."""
    del spec_dir
    working_dir = context.get("working_dir", Path.cwd())
    message = inputs.message

    from providence_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()

    def git(*args: str) -> None:
        runner.run(["git", *args], cwd=working_dir)

    # Initialise a fresh repo in the isolated workspace if needed
    git_dir = working_dir / ".git"
    if not git_dir.exists():
        git("init")
        git("config", "user.email", "sdd-doctor@local")
        git("config", "user.name", "SDD Doctor")

    git("add", ".")
    git("commit", "-m", message, "--allow-empty")
