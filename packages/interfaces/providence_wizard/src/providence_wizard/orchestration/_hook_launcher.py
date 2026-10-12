"""The one-line launcher commands the agent platforms run for the central hook."""

from __future__ import annotations

import os


# The launcher must run under every shell an agent may use (sh, cmd.exe,
# PowerShell 5.1), so it is a single Python one-liner: only single quotes
# inside, and no `$`, `%`, backtick, `&`, `|` or `^`.  It walks up from the
# cwd (or PROVIDENCE_WORKSPACE_ROOT) to the workspace and runs the central hook
# in-process (stdin/stdout are shared).  A project without a governed workspace
# is left alone; a governed workspace whose hook is missing is named on stderr.
# The walk stops at the first `.git` (the project boundary): a project without
# its own `.providence/` must not inherit governance from a parent directory.
def _launcher_code(*root_envs: str) -> str:
    anchors = "".join(f"os.environ.get('{name}') or " for name in root_envs)
    return (
        "import os,sys,runpy,pathlib as P;"
        f"p=P.Path({anchors}os.getcwd()).resolve();"
        "a=[p,*p.parents];"
        "a=a[:next((i for i,d in enumerate(a) if (d/'.git').exists()),len(a))+1];"
        "r=next((d for d in a if (d/'.providence'/'metadata.json').is_file()),None);"
        "h=r and r/'.providence/runtime/hooks/prompt-submit.py';"
        "h and (h.is_file() and runpy.run_path(str(h),run_name='__main__') "
        "or print('providence-hook: skipped reason=hook_missing',file=sys.stderr))"
    )


_LAUNCHER_CODE = _launcher_code("PROVIDENCE_WORKSPACE_ROOT")


def launcher_command(interpreter: str, extra_root_env: str | None = None) -> str:
    """Return the launcher one-liner for a given Python interpreter name.

    `extra_root_env` names one more documented project-root variable the
    launcher consults after `PROVIDENCE_WORKSPACE_ROOT` (Devin's
    `DEVIN_PROJECT_DIR`), so it never depends on an undocumented cwd.
    """
    if extra_root_env is None:
        return f'{interpreter} -c "{_LAUNCHER_CODE}"'
    code = _launcher_code("PROVIDENCE_WORKSPACE_ROOT", extra_root_env)
    return f'{interpreter} -c "{code}"'


# Windows installs expose `python`/`py`; `python3` is often a Store stub there.
PROMPT_SUBMIT_LAUNCHER_POSIX = launcher_command("python3")
PROMPT_SUBMIT_LAUNCHER_WINDOWS = launcher_command("python")
HOST_LAUNCHER_PYTHON = "python" if os.name == "nt" else "python3"
PROMPT_SUBMIT_LAUNCHER = launcher_command(HOST_LAUNCHER_PYTHON)
CENTRAL_PROMPT_SUBMIT_COMMAND = PROMPT_SUBMIT_LAUNCHER


def central_prompt_submit_command() -> str:
    """Return the relocatable command for the generated central hook.

    The command embeds no path: the wizard consolidates and deploys the output
    into another project location.
    """
    return PROMPT_SUBMIT_LAUNCHER
