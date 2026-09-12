"""Runners."""

from providence_integration.engine.types import RunnerCallable

from .command_runner import run_command_exec
from .config_runner import run_config_validate
from .filesystem_runner import run_filesystem_copy, run_filesystem_create_structure
from .git_runner import run_git_commit

RUNNER_REGISTRY: dict[str, RunnerCallable] = {
    "filesystem.create_structure": run_filesystem_create_structure,
    "filesystem.copy": run_filesystem_copy,
    "command.exec": run_command_exec,
    "git.commit": run_git_commit,
    "config.validate": run_config_validate,
}
