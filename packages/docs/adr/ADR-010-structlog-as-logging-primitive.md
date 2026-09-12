# ADR-010 — structlog as the Logging Primitive

**Status:** Accepted
**Date:** 2026-05-21
**Deciders:** Sergio Lacerda
**Supersedes:** N/A

---

## Context

The codebase had ~599 raw `print()` calls across 6 production packages with no structured
output, no log levels, and no machine-readable format. The observability plan required
structured JSON logging compatible with the existing `OtelBridge` and the `providence telemetry`
sink. A single shared configuration was needed to prevent each package from making
independent formatting decisions.

---

## Decision

**`structlog` is the logging primitive for all production packages. A single configuration
module in `providence_core` is the only place structlog is configured.**

```python
# packages/core/providence_core/src/providence_core/logging.py
import structlog


def configure_logging(level: str = "INFO") -> None:
    """Called once at process startup (CLI entrypoint or __main__)."""
    ...
```

All packages obtain a logger via:

```python
import structlog

logger = structlog.get_logger(__name__)
```

No package calls `structlog.configure()` directly.

### Renderer selection

| Context | Renderer |
|---|---|
| `SDD_ENV=production` | `JSONRenderer` |
| Non-TTY stdout | `JSONRenderer` |
| Dev / interactive TTY | `ConsoleRenderer` |

### Log level mapping

| `print()` context | structlog level |
|---|---|
| Progress/status output | `logger.info()` |
| Debug/trace output | `logger.debug()` |
| Warnings, degraded paths | `logger.warning()` |
| Errors, exceptions | `logger.error()` |
| Interactive CLI output (stdout IS the interface) | `print()` + `# noqa: T201` |

Interactive CLI output — where stdout is the user-facing interface (e.g., `providence telemetry dump`
streaming JSONL, `providence ask` response text) — keeps `print()` with an explicit `# noqa: T201`.
These are not logging calls.

### Migration gate

`ruff T201` is added to each package's lint `select` list after its migration phase
completes. A package with T201 active blocks new `print()` in CI.

---

## Rationale

- **stdlib `logging` rejected:** the configuration API is more complex, handlers must be
  managed explicitly, and structured output requires additional setup per handler.
- **loguru rejected:** non-standard API surface; less composable with OpenTelemetry
  processor chains.
- **structlog accepted:** processors compose naturally with the existing `OtelBridge`;
  `ConsoleRenderer`/`JSONRenderer` switching requires no application code change.
- **Single config module:** prevents renderer drift across packages and ensures
  `cache_logger_on_first_use=True` is set exactly once.

---

## Consequences

- Packages may not call `structlog.configure()` — only `providence_core.logging.configure_logging()`.
  A direct `structlog.configure()` call outside `providence_core/logging.py` is a policy violation.
- Interactive stdout output is exempt from T201; callers must add `# noqa: T201` with intent.
- Adding a new log processor (e.g., sampling, redaction) requires changing only
  `providence_core/logging.py` — all packages pick it up automatically.

---

## Links

- Implementation: `packages/core/providence_core/src/providence_core/logging.py`
- Related: M007 (Telemetry Enforcement), ADR-008 (trace_id propagation)
