"""Module availability checks for governed Python interpreters."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def check_module_available(python_exe: str | Path, module: str) -> bool:
    """Return True if `module` can be imported by `python_exe`.

    Avoids `python -c` (blocked by governance policy) by writing a temporary
    import script and executing it via SafeProcessRunner.
    """
    script = f"import {module}\n"
    # delete=False + manual cleanup: on Windows, a NamedTemporaryFile opened
    # with delete=True keeps an exclusive lock for the life of the `with`
    # block, so the subprocess spawned below can't open the same path.
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 -- closed early, see below
        mode="w", suffix="_sdd_import_check.py", delete=False
    )
    try:
        handle.write(script)
        handle.flush()
        handle.close()
        from providence_core.utils._process_runner import SafeProcessRunner

        runner = SafeProcessRunner()
        result = runner.run([str(python_exe), handle.name], capture_output=True)
        return result.success
    finally:
        os.unlink(handle.name)
