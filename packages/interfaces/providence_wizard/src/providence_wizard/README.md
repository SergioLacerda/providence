# SDD Wizard

`providence_wizard` is the wizard interface package used by the SDD CLI to bootstrap
and generate governed workspace artifacts.

## Current entrypoints

The supported runtime entrypoints are:

- CLI: `providence wizard run`
- Repo-local CLI: `uv run providence wizard run`
- Python contract boundary: `providence_wizard.contracts`

The CLI must not import orchestration internals directly. Production callers use
`WizardInvocation` and `run_wizard()` from `providence_wizard.contracts`.

## Public contract

The canonical boundary lives in `contracts.py`.

```python
from pathlib import Path

from providence_wizard.contracts import WizardInvocation, run_wizard

result = run_wizard(
    WizardInvocation(
        project_root=Path.cwd(),
        output_path=None,
    )
)
```

Contract types:

- `WizardInvocation`
- `GeneratedManifest`
- `WizardResult`

## Package layout

```text
providence_wizard/
 contracts.py
 main.py
 application/
    session_bootstrap.py
    preferences_flow.py
    phase_runtime.py
    generation_runtime.py
    seedling_bridge.py
    workspace_runtime.py
    operator_state.py
    finalization.py
    interactive_wizard.py
 orchestration/
    phase_4_5_6_generator.py
    phase4_governance_loader.py
    phase5_artifact_compiler.py
    phase6_output_validator.py
    phase6_seedlings_orchestrator.py
    deployer/
    seedlings/
    wizard/
    writers/
 templates/
```

## Architectural responsibilities

### `contracts.py`

- defines the stable public API consumed by `providence_cli`
- lazy-loads the application bootstrap boundary

### `main.py`

- provides the thin package entrypoint
- delegates to `contracts.run_wizard`

### `application/`

- owns shell-level flow and session lifecycle
- isolates prompt handling, phase dispatch, workspace setup, seedling bridging,
  and final handoff behavior

### `orchestration/wizard/`

- contains governance parsing, compilation, selection, and rendering helpers

### `orchestration/writers/`

- writes mandates, guidelines, README artifacts, and generation manifests

### `orchestration/deployer/`

- applies template deployment and seedling injection concerns

### `orchestration/seedlings/`

- generates governance and IDE seed artifacts used by the wizard pipeline

## Execution model

At a high level the wizard flow is:

1. CLI or caller creates a `WizardInvocation`
2. `contracts.run_wizard()` loads `application.session_bootstrap`
3. `SessionBootstrap` prepares runtime state
4. application runtimes delegate generation work into orchestration modules
5. the run returns a `WizardResult` and, when successful, a `GeneratedManifest`

## Performance intent

The refactored boundary keeps the startup path narrow:

- `providence_wizard.contracts` stays lightweight
- shell-level imports avoid pulling orchestration and prompt dependencies until needed
- `providence wizard run --help` should not import the heavy orchestration graph

Relevant regression coverage:

- `packages/interfaces/providence_wizard/tests/test_startup_performance.py`
- `packages/interfaces/providence_wizard/tests/test_contracts.py`
- `packages/interfaces/providence_wizard/tests/test_application_boundary.py`
- `packages/interfaces/providence_wizard/tests/test_full_pipeline_performance.py`

## Development notes

When changing this package:

- preserve `providence_wizard.contracts` as the only supported production boundary
- keep `main.py` thin
- prefer command-local or runtime-local imports in shell-facing paths
- avoid reintroducing legacy direct CLI orchestration surfaces
- update this README if package topology or entrypoints change

## Validation commands

Useful repo-local checks:

```bash
uv run providence governance validate
uv run python -m pytest -q packages/interfaces/providence_wizard/tests/test_contracts.py
uv run python -m pytest -q packages/interfaces/providence_wizard/tests/test_startup_performance.py
```
