# Providence Profile and Brand Refinement Implementation Plan

> **REQUIRED SUB-SKILL:** Use executing-plans to implement this plan task-by-task.

**Goal:** Make the compact governance footer's `profile=` field display a Providence-branded label (e.g. `providence-diagnose`) derived from the actual skill being run, while every legacy `sdd-*` registry ID keeps working unchanged.

**Architecture:** Add a single pure function `resolve_profile_label()` in `providence_skills` that maps any `sdd-*` string to `providence-*` (identity for everything else). Apply it inside `format_governance_footer()` so every caller gets the branded display for free. Fix the one CLI call site that currently hardcodes `profile="default"` for `providence skills run <id>` so it passes the real skill id through, then run a scoped residual-branding audit (report, not blind renames), update tests/docs mirrors, regenerate `.providence/` runtime artifacts, and record the design decision in an ADR.

**Tech Stack:** Python 3.10, pytest (`--import-mode=importlib`), Typer CLI, existing `providence_skills` / `providence_runtime` / `providence_cli` packages.

---

## Grounding: what the current code actually does (verified, not assumed)

The refined `.analysis/` package (`proposal.md`/`design.md`/`tasks.md`) assumes `profile=sdd-diagnose` is already emitted somewhere today. **It is not.** Verified by reading the code and grepping the whole repo (source, tests, generated docs, `.providence/compiled`):

- `format_governance_footer()` (`formatter.py:6-22`, `packages/features/providence_skills/src/providence_skills/formatter.py`) already emits the `PROVIDENCE GOVERNANCE` prefix. Good, no change needed there beyond adding the resolver call.
- `providence skills run <name>` hardcodes `profile="default"` — `skills.py:162` (`packages/interfaces/providence_cli/src/providence_cli/commands/skills.py`): `engine.run_skill(name, execute=execute, profile="default")`. `name` (the real skill id, e.g. `"sdd-diagnose"`) is never passed as `profile`.
- `profile` threads unchanged from `SkillEngine.run_skill` → `SkillExecutor.run_skill` → `run_skill_flow` → every result builder (`build_execution_result`, `build_missing_skill_result`, `build_policy_blocked_result`) and every pipeline stage in `run_composed_skill` (`_executor_pipeline.py`, `packages/core/providence_runtime/src/providence_runtime/_skill_executor/_executor_pipeline.py`). **One call-site fix at `skills.py:162` propagates everywhere else for free** — nothing else needs to change to get `result.profile` / `result.governance_footer` to reflect the skill id.
- `providence ask`'s `profile` is a *different* concept entirely: the workspace type (`client`/`master`) read from `.providence/profile` via `get_profile_state()` (`_ask_backend/_helpers.py`, `packages/interfaces/providence_cli/src/providence_cli/commands/_ask_backend/_helpers.py`). It is not a skill id and must **not** be forced through the `sdd-*` resolver rename — a workspace type like `client` doesn't start with `sdd-` so the resolver is a no-op there anyway, but do not add any new code path that tries to brand it as a skill.
- `emit_pipeline_required()` (`_skills_command_support.py:88-114`, `packages/interfaces/providence_cli/src/providence_cli/commands/_skills_command_support.py`) hardcodes `"profile": "default"` in the JSON it emits when `sdd-correct` is blocked by policy before `run_skill` is even called. Same fix applies here for consistency (the blocked skill's name is already the `name` parameter in scope).
- Existing tests were checked and **none break** from this change: tests that assert `profile=default` in output either (a) mock `SkillEngine.run_skill` directly (so the real call-site argument is irrelevant — `test_skills_run_command.py`), or (b) call `run_skill_flow`/executor internals directly with an explicit `profile="default"` argument (`test_skill_executor_pipeline.py`, `test_skills_sync_contract.py`), or (c) test the unrelated `ask` workspace-profile fallback (`test_ask_context_service.py`). Real, non-mocked `skills run` tests only assert `governance_footer.startswith("PROVIDENCE GOVERNANCE:")`, which still holds.

## Design decisions (record in the ADR — Task 6)

1. **Profile labels are display-only.** `format_governance_footer()` applies the resolver internally to whatever `profile` string it receives. Callers keep passing raw IDs (`sdd-diagnose`, `default`, `client`, ...); only the rendered footer text shows the Providence label. Structured JSON fields (`data["profile"]`, `result.profile`) keep the raw id — this is what "keep JSON contract stable" means in `design.md`: field names and value semantics (still "whatever profile was used to run this") are unchanged, only its *value* becomes meaningful for `skills run` (was always `"default"`, a constant; becomes the real skill id).
2. **Registry IDs are untouched.** No skill/command is renamed. `sdd-diagnose` remains the canonical registry id forever in this change; `providence-diagnose` only ever appears as rendered text.
3. **The resolver is a rule, not a lookup table.** `sdd-<x>` → `providence-<x>` for any `<x>`, everything else passes through unchanged. This covers all current and future `sdd-*` skill ids (there are more than the 6 in `proposal.md`'s table — e.g. `sdd-organize`, `sdd-harness`, `sdd-pipeline`, `sdd-review-architecture`, `sdd-compress-context`) without hardcoding each one and without needing to update the resolver when a new skill is added.
4. **`providence ask`'s workspace-type profile is out of scope.** It is a different axis (deployment profile, not skill identity) and is deliberately left alone.

---

## Task 1: Add the Providence profile-label resolver

**Files:**
- Create: `packages/features/providence_skills/src/providence_skills/profile_labels.py`
- Modify: `packages/features/providence_skills/src/providence_skills/__init__.py`
- Test: `packages/features/providence_skills/tests/test_profile_labels.py`

**Step 1: Write the failing test**

```python
"""Tests for the sdd-* -> providence-* profile label resolver."""

from __future__ import annotations

import pytest

from providence_skills import resolve_profile_label


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sdd-diagnose", "providence-diagnose"),
        ("sdd-ask", "providence-ask"),
        ("sdd-correct", "providence-correct"),
        ("sdd-converge", "providence-converge"),
        ("sdd-stabilize", "providence-stabilize"),
        ("sdd-validate-governance", "providence-validate-governance"),
        ("sdd-organize", "providence-organize"),
    ],
)
def test_resolves_legacy_sdd_id_to_providence_label(raw: str, expected: str) -> None:
    assert resolve_profile_label(raw) == expected


@pytest.mark.parametrize("raw", ["default", "client", "master", "", "providence-diagnose"])
def test_non_sdd_values_pass_through_unchanged(raw: str) -> None:
    assert resolve_profile_label(raw) == raw


def test_resolver_is_idempotent() -> None:
    once = resolve_profile_label("sdd-diagnose")
    assert resolve_profile_label(once) == once
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest packages/features/providence_skills/tests/test_profile_labels.py -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_profile_label'`

**Step 3: Write minimal implementation**

```python
"""Resolve legacy sdd-* skill/route IDs to Providence-branded display labels.

Display-only: registry IDs are never renamed. See ADR-018.
"""

from __future__ import annotations

_LEGACY_PREFIX = "sdd-"
_PROVIDENCE_PREFIX = "providence-"


def resolve_profile_label(value: str) -> str:
    """Return the Providence-branded display label for a profile/skill id.

    Any string starting with ``sdd-`` becomes ``providence-<suffix>``.
    Everything else (``default``, workspace types like ``client``/``master``,
    already-resolved ``providence-*`` labels, empty strings) passes through
    unchanged.
    """
    if value.startswith(_LEGACY_PREFIX):
        return _PROVIDENCE_PREFIX + value[len(_LEGACY_PREFIX):]
    return value
```

Add to `packages/features/providence_skills/src/providence_skills/__init__.py`:

```python
from .profile_labels import resolve_profile_label
```

and add `"resolve_profile_label"` to `__all__`.

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest packages/features/providence_skills/tests/test_profile_labels.py -v`
Expected: PASS (9 tests)

**Step 5: Commit**

```bash
git add packages/features/providence_skills/src/providence_skills/profile_labels.py \
        packages/features/providence_skills/src/providence_skills/__init__.py \
        packages/features/providence_skills/tests/test_profile_labels.py
git commit -m "feat: add sdd-* to providence-* profile label resolver"
```

---

## Task 2: Wire the resolver into the footer and the real skill-run call site

**Files:**
- Modify: `packages/features/providence_skills/src/providence_skills/formatter.py`
- Modify: `packages/interfaces/providence_cli/src/providence_cli/commands/skills.py:162`
- Modify: `packages/interfaces/providence_cli/src/providence_cli/commands/_skills_command_support.py` (the `"profile": "default"` in `emit_pipeline_required`, ~line 95)
- Test: `packages/features/providence_skills/tests/test_formatter.py` (new)
- Test: `packages/interfaces/providence_cli/tests/test_skills_run_command.py` (extend)

**Step 1: Write the failing test (formatter)**

```python
"""Tests for governance footer formatting."""

from __future__ import annotations

from providence_skills import format_governance_footer


def test_footer_renders_providence_label_for_legacy_skill_id() -> None:
    footer = format_governance_footer(drift="none", governance="ok", profile="sdd-diagnose")
    assert footer == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=providence-diagnose"


def test_footer_leaves_non_sdd_profile_unchanged() -> None:
    footer = format_governance_footer(drift="none", governance="ok", profile="default")
    assert footer == "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default"


def test_footer_still_appends_root_seed_drift() -> None:
    footer = format_governance_footer(
        drift="none", governance="ok", profile="sdd-ask", root_seed_drift="none"
    )
    assert footer.endswith("profile=providence-ask | root_seed_drift=none")
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest packages/features/providence_skills/tests/test_formatter.py -v`
Expected: FAIL — first assertion shows `profile=sdd-diagnose` instead of `profile=providence-diagnose`.

**Step 3: Write minimal implementation**

Edit `formatter.py`:

```python
from __future__ import annotations

from .profile_labels import resolve_profile_label


def format_governance_footer(
    *,
    drift: str,
    governance: str,
    profile: str,
    root_seed_drift: str | None = None,
) -> str:
    """Build the canonical compact governance footer.

    `profile` is resolved through `resolve_profile_label` so legacy `sdd-*`
    skill/route ids render as Providence-branded display labels without
    renaming the underlying registry id (see ADR-018).

    `root_seed_drift` is a separate, optional field — distinct from `drift`
    (which reflects in-session cached-state drift). It is only appended when
    explicitly provided, so existing callers are unaffected.
    """
    label = resolve_profile_label(profile)
    footer = f"PROVIDENCE GOVERNANCE: drift={drift} | governance={governance} | profile={label}"
    if root_seed_drift is not None:
        footer += f" | root_seed_drift={root_seed_drift}"
    return footer
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest packages/features/providence_skills/tests/test_formatter.py -v`
Expected: PASS (3 tests)

**Step 5: Write the failing test (real skill-run call site)**

Add to `packages/interfaces/providence_cli/tests/test_skills_run_command.py`:

```python
def test_skills_run_footer_uses_providence_label_for_skill_id() -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = runner.invoke(app, ["--json", "skills", "run", "sdd-diagnose"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)
    assert data["profile"] == "sdd-diagnose"
    assert "profile=providence-diagnose" in data["governance_footer"]
```

Run it first to confirm it fails (`data["profile"]` will be `"default"`, footer will say `profile=default`).

**Step 6: Write minimal implementation**

`skills.py:162`:

```python
result = engine.run_skill(name, execute=execute, profile=name)
```

`_skills_command_support.py`, inside `emit_pipeline_required`, change:

```python
"profile": "default",
```

to:

```python
"profile": name,
```

**Step 7: Run test to verify it passes**

Run: `.venv/bin/python -m pytest packages/interfaces/providence_cli/tests/test_skills_run_command.py -v`
Expected: all PASS, including the new test.

**Step 8: Run the full focused suite for touched packages**

Run: `.venv/bin/python -m pytest packages/features/providence_skills packages/core/providence_runtime packages/interfaces/providence_cli -q`
Expected: PASS, 0 failures. (Confirms the grounding analysis above — no other test hardcodes `profile=default` against a real, non-mocked `skills run` invocation.)

**Step 9: Commit**

```bash
git add packages/features/providence_skills/src/providence_skills/formatter.py \
        packages/features/providence_skills/tests/test_formatter.py \
        packages/interfaces/providence_cli/src/providence_cli/commands/skills.py \
        packages/interfaces/providence_cli/src/providence_cli/commands/_skills_command_support.py \
        packages/interfaces/providence_cli/tests/test_skills_run_command.py
git commit -m "feat: render Providence profile labels for real skill-run footers"
```

---

## Task 3: Audit residual SDD / sdd-* occurrences (report, not blind rename)

This task produces a **classification report**, not file edits — `design.md`'s explicit "Do Not" list forbids blind renames, and a preliminary scan already found 60+ files matching loose `SDD` patterns, most of which are legitimate (package names, historical ADRs, compatibility command ids). Renaming those blind would break things.

**Files:**
- Create: `docs/spec/decisions/2026-09-12-sdd-branding-audit.md` (or fold into the ADR in Task 6 as an appendix — decide when you see the volume of results)

**Step 1: Run the scoped scan**

```bash
rg -n --hidden -g '!.venv' -g '!.git' -g '!.analysis' -g '!*.pyc' \
   '\bSDD\b|sdd-[a-z-]+' packages docs AGENTS.md GEMINI.md .providence \
   > /tmp/sdd_audit_raw.txt
wc -l /tmp/sdd_audit_raw.txt
```

**Step 2: Classify each distinct occurrence**

For each unique string/context, assign one of the five buckets from `design.md` Decision 3:

| Bucket | Action |
| --- | --- |
| `branding_drift` | User-facing prose that says "SDD" where it now means Providence governance (e.g. "SDD skill contract" in a docstring/description) — candidate for a follow-up rename PR. |
| `compatibility_alias` | A real `sdd-*` command/skill id kept on purpose — leave, document in the compatibility matrix (SQ-002 in `analysis.md`). |
| `internal_legacy_path` | A file/package/variable name containing `sdd` that would require a breaking rename to touch — leave with a note. |
| `historical_reference` | ADRs, incident docs, changelogs describing past decisions — never edit. |
| `unrelated` | False positive from the regex (e.g. "SDD" inside an unrelated acronym) — no action. |

**Step 3: Write the report**

One table per bucket, each row: file path, line, snippet, one-line rationale. Do **not** edit any source file in this task — that happens in Task 4, and only for rows classified `branding_drift`.

**Step 4: Commit the report only**

```bash
git add docs/spec/decisions/2026-09-12-sdd-branding-audit.md
git commit -m "docs: audit residual SDD/sdd-* branding surfaces"
```

---

## Task 4: Apply branding_drift fixes and sync docs mirrors

**Files:** whatever Task 3's report lists under `branding_drift` — expect this to touch `docs/**` and its mirror `packages/docs/**` (verified identical today via `diff`), plus a handful of docstrings/descriptions in `packages/**/src`.

**Step 1:** For each `branding_drift` row, edit the source location (under `docs/`, not `packages/docs/` — that's the generated mirror).

**Step 2:** Re-sync mirrors. Check whether a sync command exists:

```bash
grep -rn "packages/docs" tools/maintenance/*.py mk/*.mk
```

If a sync script exists, run it. If not, mirror the same edit by hand into `packages/docs/<same relative path>` (confirmed today via `diff -q` that the trees are byte-identical, so a matching manual edit keeps them in sync).

**Step 3:** Run the focused suite for any package touched, plus a final residual scan restricted to the rows just fixed, to confirm they no longer match:

```bash
rg -n '<exact string that was fixed>' docs packages/docs
```

Expected: no hits (or only hits in files intentionally left as `historical_reference`).

**Step 4: Commit**

```bash
git commit -m "docs: rebrand residual SDD strings classified as branding drift"
```

---

## Task 5: Regenerate `.providence/` runtime artifacts

**Step 1:** Run the compiler:

```bash
.venv/bin/python -m providence_cli governance compile
```

(Confirm exact invocation — `compile` is defined in `packages/interfaces/providence_cli/src/providence_cli/commands/governance.py:95`; check `--help` if the above doesn't match the installed CLI entry point, e.g. it may be `providence governance compile` once installed.)

**Step 2:** Check what changed:

```bash
git status --porcelain .providence AGENTS.md GEMINI.md
```

**Step 3:** Review the diff is limited to the expected footer/branding text (no unrelated fingerprint churn), then commit:

```bash
git add .providence AGENTS.md GEMINI.md
git commit -m "chore: regenerate governance artifacts after profile-label migration"
```

If regeneration surfaces unrelated drift, stop and report it rather than committing — that's outside this change's scope.

---

## Task 6: Add ADR-018

**Files:**
- Create: `docs/spec/decisions/ADR-018-profile-label-vs-route-id.md`
- Mirror: `packages/docs/spec/decisions/ADR-018-profile-label-vs-route-id.md` (identical content — see Task 4's mirror note)

**Content outline** (fill in using the Design decisions section above and Task 3's final compatibility-alias list):

1. Context: footer already says `PROVIDENCE GOVERNANCE`, but `profile=` showed either a constant `"default"` or the workspace type — never which skill ran.
2. Decision: decouple the public profile *label* (Providence-branded, resolved via `resolve_profile_label`) from the internal route/skill *id* (unchanged `sdd-*`, kept indefinitely as of this ADR — no removal date set).
3. Consequences: `skills run <id>` footers and JSON `profile` field now show the real skill id/label instead of a constant; no other command's `profile` semantics changed; a future ADR is needed before any `sdd-*` id is ever removed (see `analysis.md` SQ-001).

**Step: Commit**

```bash
git add docs/spec/decisions/ADR-018-profile-label-vs-route-id.md \
        packages/docs/spec/decisions/ADR-018-profile-label-vs-route-id.md
git commit -m "docs: add ADR-018 for profile label vs route id decoupling"
```

---

## Acceptance checks (from tasks.md, re-verified against this plan)

- [ ] `providence skills run sdd-diagnose` (dry-run, `--json`) → `data["governance_footer"]` contains `profile=providence-diagnose`; `data["profile"]` still equals `"sdd-diagnose"` (raw id preserved in structured output).
- [ ] `sdd-diagnose` and every other legacy id still resolves and executes exactly as before (no registry change).
- [ ] `rg -n '\bSDD\b|sdd-[a-z-]+' packages docs` residual output matches Task 3's classification report exactly (nothing new, nothing missing).
- [ ] Full focused suite (`packages/features/providence_skills`, `packages/core/providence_runtime`, `packages/interfaces/providence_cli`) passes.
- [ ] `.providence/` regeneration is either committed (Task 5) or explicitly reported as pending with a reason.
