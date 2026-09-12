# Thread Lifecycle Ownership (CLI Services)

Date: 2026-05-16

## Scope

This guide defines the lifecycle contract for CLI services that spawn background
threads (current focus: `sdd metrics serve`).

## Ownership Model

- Service command owns all threads it starts.
- Worker threads must not outlive the command scope.
- Shutdown responsibility is explicit in command `finally` blocks.

## Lifecycle Contract

1. Create stop signal (`threading.Event`) before starting worker.
2. Start worker with deterministic loop (`while not stop_event.is_set()`).
3. Use cancelable waits (`stop_event.wait(interval)`) instead of raw `sleep`.
4. In shutdown path, always:
   - `stop_event.set()`
   - close service resources (`server_close`, file handles, sockets)
   - `join()` workers with bounded timeout.
5. Keep worker logic best-effort on transient read/parse errors, but never ignore
   shutdown signals.

## Error Handling Rules

- Worker exceptions should not crash main command by default unless required for
  correctness.
- Reload/observer workers may ignore transient source errors and keep last valid
  state.
- Service command must remain responsive to `KeyboardInterrupt`.

## Test Requirements

- Start/stop deterministic test.
- Restart cycle test (multiple repeated start/stop invocations).
- Shutdown resource cleanup assertion (`server_close`/equivalent called).
- No daemon-only lifecycle assumptions in production path.
- Soak churn test with at least 30 restart cycles.

## CI Soak Gate (Phase 2)

Approve thread lifecycle hardening when all conditions are true:

1. `test_serve_soak_restart_cycles` passes with 30 cycles.
2. `server_close` is called exactly once per cycle.
3. No residual alive worker thread after each stop in reload worker tests.

## Operational Checks

Run:

```bash
uv run pytest -q packages/interfaces/providence_cli/tests/test_metrics_commands.py
uv run pytest -q packages/interfaces/providence_cli/tests/test_metrics_commands.py -k soak
uv run python tools/maintenance/thread_audit_report.py
uv run providence test ci-validate --soak-threads
```

Use `docs/guides/THREAD_AUDIT_REPORT.md` as static hotspot inventory.
