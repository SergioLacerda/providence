"""Delegate to the repository-root pytest write guard.

`packages/pyproject.toml` carries its own `[tool.pytest.ini_options]` block
(needed so package-scoped test runs still resolve `../tests` correctly).
When pytest is invoked with args under `packages/` (e.g.
`pytest packages/core/...`), that makes `packages/pyproject.toml` the
closest ini file, so pytest sets `rootdir`/`confcutdir` to `packages/` for
that invocation — which excludes the repository-root `conftest.py` from
conftest discovery entirely, even though it is a real ancestor directory.

Loading the root guard here by absolute file path (rather than duplicating
its ~140 lines) keeps a single source of truth while still registering the
`.providence/` write-guard fixture for every test tree under `packages/**`
regardless of which pyproject.toml pytest picked as rootdir for a given
invocation. See `../conftest.py` for the actual guard implementation and
`.analysis/refined/20260912-m015-handshake-runtime-drift/` for why it exists.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT_CONFTEST_PATH = Path(__file__).resolve().parent.parent / "conftest.py"
_spec = importlib.util.spec_from_file_location(
    "_repo_root_conftest_guard", _ROOT_CONFTEST_PATH
)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(
        f"could not load repository-root conftest: {_ROOT_CONFTEST_PATH}"
    )
_root_conftest_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_conftest_guard)

# Re-bind the already `@pytest.fixture`-decorated callable in this module's
# namespace: pytest discovers autouse fixtures by name in each conftest.py
# it loads, not by where the function object was originally defined. Listed
# in __all__ so static analysis recognizes this as the module's intentional
# export rather than an unused global (pytest never references it by a
# direct name lookup in this file's own code — only by module attribute).
_forbid_repo_sdd_writes = _root_conftest_guard._forbid_repo_sdd_writes

__all__ = ["_forbid_repo_sdd_writes"]
