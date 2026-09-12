# REFACTOR_NOTES — providence_cli module decomposition
# Started: 2026-06-08

## Baseline Metrics (Wave 0)

### Test suite
- **Unit tests**: 1347 passed, 14 skipped (tests/unit/)
- **Full suite** (unit + providence_cli): 2001 passed, 15 skipped
- Coverage: not measured at baseline

### Source files > 300 lines

| File | Lines |
|------|-------|
| commands/_ask_backend.py | 1377 |
| commands/governance.py | 1098 |
| commands/audit.py | 951 |
| commands/skills.py | 862 |
| commands/runtime.py | 541 |
| commands/lint.py | 433 |
| commands/telemetry.py | 418 |
| commands/test.py | 412 |
| commands/metrics.py | 395 |
| generators/_prompt_commands.py | 385 |
| extensions/framework/extension_framework.py | 349 |
| services/governance_config_handlers.py | 348 |
| utils/profile.py | 333 |
| generators/_shared.py | 319 |
| main.py | 303 |

**Total source lines: 14787**

### External consumers of providence_cli (public API surface)

Files outside the package that import from `providence_cli.*`:
- packages/core/providence_core/tests/cli/test_ask_command.py
- packages/core/providence_core/tests/cli/test_ask_security.py
- tests/conftest.py
- tests/contract/conftest.py
- tests/contract/test_execution_gate.py
- tests/contract/test_governance_schema.py
- tests/integration/cli/test_onboarding_flow.py
- tests/unit/cli/* (multiple)

## Gaps & Bugs Log

### Wave 1 — ask_backend decomposition

- **Dead code removed**: `services/ask_dispatcher.py` (423 lines) was an abandoned
  parallel rewrite of the ask pipeline (`run_ask(AskArgs)` / `AskArgs`). Neither
  symbol was imported or called anywhere outside the file itself — only a stray
  comment in `ask_renderer.py` referenced "ask_dispatcher". The live entrypoint
  chain is `commands/ask_entry.py` → `commands/_ask_backend.ask_cmd` →
  `_ask_cmd_impl`. Deleted the file; full `providence_cli` test suite (741 tests) still
  green. This both removes a >300-line violation and resolves task 1.5 (no
  dispatcher module is needed — the existing `services/ask_*` modules already
  cover context/filter/renderer concerns from tasks 1.2-1.4).

- **`_ask_backend.py` (1194 lines) decomposition is high-risk and blocked**:
  the test suite contains ~150 `unittest.mock.patch("providence_cli.commands._ask_backend.<name>")`
  call sites across 10+ test files (`test_ask_command.py`,
  `test_ask_telemetry_*.py`, `test_ask_output_snapshots.py`,
  `test_ask_full_json_output.py`, `test_codeql_guardrails.py`, etc.), targeting
  ~25 distinct internal helpers (`_resolve_workspace_root`, `_get_profile_state`,
  `_emit_ask_telemetry`, `_run_organize_intake`, `build_governed_ask_snapshot`,
  `_guard_budget_breach`, `_guard_handshake`, `OtelBridge`, `TelemetrySink`, etc.).
  `unittest.mock.patch` rewrites the attribute in the *module namespace where the
  caller does its global lookup* — so any orchestration function
  (`_ask_cmd_impl` and friends) that calls these helpers must remain in
  `_ask_backend.py` (or the helper must remain imported-by-name into
  `_ask_backend.py`) for the existing patches to keep working. Moving
  `_ask_cmd_impl` itself to a new module would silently break ~150 patches
  (tests would exercise the *unpatched* originals).
  **Recommended path** (not yet executed — needs a strategic decision before
  large edits): move only the ~20 standalone helper *implementations* (the
  thin `_impl`-delegating wrappers, lines ~204-335, plus the
  `_check_fingerprint_drift` / `_render_context_output` / `_collect_learning_signals`
  family) into the relevant `services/ask_*` modules, and re-import them by name
  at the top of `_ask_backend.py` so `_ask_backend.<name>` patch targets keep
  resolving. Keep `_ask_cmd_impl` and its direct call chain in `_ask_backend.py`.
  This can shave the file from 1194 lines to roughly 850-900 — still over 300,
  but the remaining bulk is the orchestrator itself, which cannot move without a
  coordinated rewrite of the ~150 patch sites (a Wave 7-sized test-realignment
  effort in its own right).

## Wave Progress

| Wave | Status | Tests after |
|------|--------|-------------|
| 0 — Baseline | ✅ done | 2001 passed |
| 1 — ask_backend split | ⚠️ partial — dead `ask_dispatcher.py` (423L) removed; `_ask_backend.py` (1194L) decomposition blocked on ~150 mock-patch sites (see Gaps log) | 741 passed (providence_cli) |
| 2 — governance.py split | ✅ done | 723 passed, 1 skipped, 1 pre-existing fail |
| 3 — audit.py split | ✅ done | 723 passed, 1 skipped, 1 pre-existing fail |
| 4 — skills.py split | ✅ done | 719 passed, 1 skipped (providence_cli); 3673 overall |
| 5 — remaining commands (runtime/lint/telemetry/test/metrics) | ✅ done | 735 passed, 1 skipped |
| 6 — generators/extensions/utils/main | ✅ done | providence_cli 741 passed, 1 skipped; core 1979 passed, 1 skipped |
| 7 — test realignment (all test files ≤300L) | ✅ done | green except pre-existing `test_process_runner_adoption` fail |
| 8 — gap remediation | ⚠️ partial — all source/test files ≤300L except documented `_ask_backend.py` (1194L) blocker (see Gaps log) | providence_cli green except pre-existing `test_process_runner_adoption` fail |

### Wave 8 — gap remediation details

Extracted handler/service logic out of the remaining oversized files, keeping
thin Typer command wrappers and preserving `mock.patch` targets via re-exports:

- `main.py` (303→281L): moved `_profile_option_callback` /
  `_json_option_callback` / `_verbose_option_callback` implementations to new
  `utils/cli_callbacks.py`; kept underscore-prefixed aliases in `main.py` for
  direct-import tests.
- `commands/test.py` (324→257L): moved `review_golden`'s body and
  `_load_golden_ast` into `services/test_handler.run_review_golden`.
- `commands/metrics.py` (327→252L): moved JSON/table-building for `summary`
  and the `MetricsHandler` factory for `serve` into
  `services/metrics_handler.py` (`build_summary_json_data`,
  `build_summary_table`, `build_metrics_handler`).
- `services/skills_resolver.py` (347→255L): moved
  `_read_registry_ids` / `_prune_managed_files` / `_prune_antigravity_skills` /
  `_reconcile_root_seed_artifacts` into new `services/skills_seed_reconciler.py`,
  re-exported by name for `test_skills_resolver_bootstrap.py` patches.
- `commands/telemetry.py` (361→296L): moved status/init payload building into
  `services/telemetry_handler.build_status_data` /
  `build_init_result`; deduplicated since/until validation into
  `_abort_invalid_time_filter`.
- `extensions/tests/test_extensions.py` (318→159L): split registry/plugin-loader
  tests into new `extensions/tests/test_extensions_registry.py` (166L).
- `commands/skills.py` (570→300L): moved the six `learning-*` subcommands
  (learning-candidates/approve/reject/impact/rules/status) into a new
  `commands/skills_learning.py` Typer app, merged into `skills.app` via
  `app.registered_commands.extend(...)` so the CLI surface (`providence skills
  learning-*`) is unchanged. Updated the 8 `mock.patch(
  "providence_cli.commands.skills.<resolve_workspace_root|SupervisedLearningStore>")`
  sites in `test_skills_learning_command.py` to target
  `providence_cli.commands.skills_learning.<...>` (the new namespace where these
  names are looked up at call time).

Result: `find src -name "*.py" | xargs wc -l | awk '$1>300'` now reports only
`commands/_ask_backend.py` (1194 lines) — the documented Wave 1 blocker. No
test files exceed 300 lines (the only >300L test file found is a stale,
untracked `build/lib/...` artifact, not source).
