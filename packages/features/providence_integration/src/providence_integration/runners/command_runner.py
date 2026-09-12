"""Command Runner."""

import shlex
from pathlib import Path

from providence_integration.engine.types import CommandExecInputs, RuntimeContext


def run_command_exec(
    inputs: CommandExecInputs, context: RuntimeContext, spec_dir: Path
) -> None:
    """Run Command Exec."""
    del spec_dir
    working_dir = context.get("working_dir", Path.cwd())
    command = inputs.command

    if not command:
        return

    # Use shlex.split to safely parse command into arguments and disable shell=True
    args = shlex.split(command)

    from providence_core.utils.process import SafeProcessRunner

    runner = SafeProcessRunner()

    result = runner.run(
        args,
        cwd=working_dir,
        timeout=120,
    )
    context["last_exit_code"] = result.returncode
    context["last_stdout"] = result.stdout
    context["last_stderr"] = result.stderr
