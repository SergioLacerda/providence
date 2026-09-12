# SDD CLI — Decision Log

**Module:** `packages/interfaces/providence_cli`
**Purpose:** Command-line interface (providence ask, sdd compile, providence governance, etc.)
**Owner:** @SergioLacerda

---

## DEC-2026-001: Typer for CLI Framework (2026-01-15)

**Decision:** Use Typer library for CLI (not argparse, Click, or custom)

**Rationale:**
- Modern: Built on Click, adds type hints support
- Intuitive: Function signature = CLI interface
- Automatic: --help, subcommands, type checking
- Minimal: Less boilerplate than Click
- Python 3.6+: Good typing integration

**Trade-off:**
- Pro: Clean, modern Python
- Con: Adds dependency (but lightweight)

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Main CLI entry point in src/providence_cli/main.py

---

## DEC-2026-002: Rich for Terminal Output (2026-01-20)

**Decision:** Use Rich library for formatting (colors, tables, progress bars)

**Rationale:**
- Pretty: User-friendly output (not raw text)
- Observable: Progress indicators for long operations
- Tables: Structured output (metadata, lists)
- Portable: Works on Linux/Mac/Windows

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-003: Structured Output Option (--json, --yaml) (2026-02-01)

**Decision:** Add --output/-o flag for JSON/YAML output (not just pretty tables)

**Rationale:**
- Scripting: Piping sdd output to jq/yq
- Integration: Other tools can parse output
- Automation: CI/CD doesn't need to parse tables
- Flexibility: User chooses format per command

**Example:**
```bash
providence ask "mandate" --output json | jq '.items[0]'
providence runtime status --output yaml
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-004: Quiet Mode (--quiet/-q) (2026-02-15)

**Decision:** Add --quiet flag to suppress non-essential output

**Rationale:**
- Scripting: No status messages, only results
- Pipelines: Clean output for downstream processing
- Batch: Running many commands, minimal noise

**Behavior:**
- Normal: Status messages, progress bars, headers
- Quiet: Only results (errors still shown)

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-005: Verbose Logging (--verbose/-v) (2026-03-01)

**Decision:** Add --verbose flag for debugging (show all steps, timings, cache stats)

**Rationale:**
- Debugging: User can diagnose slow/broken queries
- Observability: Show cache hits, network calls, timeouts
- Support: Help desk can ask for --verbose output

**Example:**
```bash
providence ask "test" --verbose
# Output:
# [DEBUG] Loading artifact: governance-core.msgpack
# [DEBUG] Query: "test" (case-insensitive)
# [DEBUG] Cache check: MISS
# [DEBUG] Matching: 15 items found
# [DEBUG] Truncating to 5 items
# [DEBUG] Latency: 2.5ms
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: Exit Codes (Semantic) (2026-03-10)

**Decision:** Use meaningful exit codes (0 = success, 1 = error, 2 = usage, etc.)

**Rationale:**
- Scripts: Can check `$?` to decide next step
- CI/CD: Different recovery for different errors
- Automation: Standard UNIX convention

**Exit codes:**
- 0: Success
- 1: General error (artifact missing, query failed, etc.)
- 2: Usage error (bad flag, missing arg)
- 100: BudgetBreachError (quota exhausted)
- 101: Governance violation

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-007: Command Hierarchy (ask, governance, runtime, cache, telemetry) (2026-03-15)

**Decision:** Organize commands into logical groups, not flat list

**Rationale:**
- Discoverability: `providence governance --help` groups related commands
- Mental model: User understands module organization
- Extensibility: New features go in appropriate group

**Hierarchy:**
- `providence ask <query>`: Query governance context
- `providence governance compile`: Compile specs to artifacts
- `providence governance validate`: Validate spec syntax
- `providence runtime status`: Check runtime state
- `sdd cache clear/stats`: Manage cache
- `providence telemetry dump/query`: Export telemetry data
- `providence init`: Initialize workspace
- `providence version`: Show version

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-008: Workspace Auto-Detection (Walk-Up) (2026-03-20)

**Decision:** CLI auto-detects workspace by walking up from CWD looking for .providence/

**Rationale:**
- UX: User doesn't specify workspace path, just works
- Standard: Like git (find .git directory)
- Multi-workspace: Each subdirectory can have own workspace

**Consequence:** Can run `sdd` from any subdirectory of workspace

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** resolve_profile() in providence_core.environment

---

## DEC-2026-009: Profile Override via --profile or $SDD_PROFILE (2026-04-01)

**Decision:** CLI respects --profile master/client flag and SDD_PROFILE env var

**Rationale:**
- CI/CD: Export SDD_PROFILE=master for automated builds
- Development: `sdd --profile master` to switch temporarily
- Scripts: Easy to embed profile in shebang

**Example:**
```bash
SDD_PROFILE=client providence ask "mandate"
# Uses client profile, not master
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-010: No Dangerous Flags (--force, --yes, --assume-yes) (2026-04-10)

**Decision:** Don't add --force or auto-confirmation flags

**Rationale:**
- Safety: Prevent accidental data loss
- Explicitness: User must read and confirm
- Discoverability: Interactive prompts teach about options

**Consequence:** Destructive operations (delete, reset) require user interaction

**Alternative:** Use scripting (echo "" | sdd command) if automation needed

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-011: Help Text Generation (Auto from Docstrings) (2026-05-01)

**Decision:** Generate --help from function docstrings (Typer auto-docs)

**Rationale:**
- Maintainability: Docs don't get stale (colocated with code)
- Consistency: Every command has help text
- Auto: No manual --help writer needed

**Example:**
```python
def ask(query: str, max_items: int = 5):
    """
    Query governance context by name or keyword.

    Args:
        query: Search term (e.g., "mandate", "security")
        max_items: Max results to return (default: 5)
    """
    ...
```

becomes:

```
$ providence ask --help
Query governance context by name or keyword.

Arguments:
  QUERY                     Search term (e.g., "mandate", "security")

Options:
  --max-items INTEGER       Max results to return (default: 5)
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-012: Canonical JSON Envelope Hard-Cut (2026-05-21)

**Decision:** Standardize command JSON outputs on a canonical envelope and
enforce it as the only supported JSON contract.

**Canonical envelope:**
- `status` (`ok|error`)
- `command`
- `ok` (bool)
- `error` (`null` or `{code,message}`)
- `data` (authoritative payload)

**Contract policy:**
- `data` is the sole authoritative payload location.
- No top-level mirroring of payload fields is allowed.
- Errors must also follow the same envelope shape.

**Rationale:**
- Removes contract ambiguity across commands.
- Eliminates transition debt and strict-flag complexity.
- Preserves predictable machine interfaces for long-lived automations.

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-013: Ask Backend Hard-Cut (2026-05-21)

**Decision:** Remove `commands/ask.py` compatibility facade and use
`commands/_ask_backend.py` as the single ask implementation path.

**Rationale:**
- Eliminate dual entrypoint maintenance and patch-point drift.
- Reduce legacy compatibility surface during big-bang refactor.
- Keep guardrails and tests aligned to the real command backend.

**Consequence:**
- `ask_entry.py` and `ask_full_entry.py` import command functions directly from
  `_ask_backend.py`.
- Tests and code-quality guardrails reference `_ask_backend.py` for ask behavior assertions.

**Status:** ACTIVE
**Owner:** @SergioLacerda

---
