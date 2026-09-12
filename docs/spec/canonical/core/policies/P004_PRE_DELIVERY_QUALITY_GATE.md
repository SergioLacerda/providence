# Policy: Pre-Delivery Quality Gate (PDQG)

**Type:** IMMUTABLE CORE
**ID:** P004
**Category:** Quality / Delivery

---

## 🎯 Objective

Ensure every agent delivery is quality-validated BEFORE handoff to human review,
regardless of project maturity or tooling stack.

The agent MUST NOT declare work "done" without first detecting and applying the
project's quality tooling. This policy is **self-adaptive**: it detects what exists
and enforces what is available.

---

## 🔍 Step 1 — Detect Quality Infrastructure

Before declaring work done, scan the project for available quality tooling:

| Signal to detect | Tool to run if detected |
|---|---|
| `Makefile` has `lint` target | `make lint` |
| `Makefile` has `test` target | `make test` |
| `providence lint` available (Providence projects) | `providence lint spec --validate-all-anchors` |
| `[tool.ruff]` in `pyproject.toml` | `ruff check --fix .` then `ruff check .` |
| `[tool.mypy]` in `pyproject.toml` | `mypy .` |
| `[tool.pytest]` in `pyproject.toml` | `pytest` |
| `.pre-commit-config.yaml` exists | `pre-commit run --all-files` |
| `package.json` has `lint` script | `npm run lint` |
| `package.json` has `test` script | `npm test` |

> **Detection rule:** Prefer `make` targets when available — they aggregate tooling
> and represent the project maintainer's intent. Fall back to individual tools only
> when no Makefile target exists.

---

## 🏷️ Step 2 — Classify Project Quality Level

Based on detection, classify the project:

### ✅ EQUIPPED

**Condition:** 2 or more quality tools detected.
**Action:** All detected tools are **MANDATORY**. Run all of them. Do not skip.

### ⚠️ PARTIAL

**Condition:** Exactly 1 quality tool detected.
**Action:** That tool is **MANDATORY**. In the delivery message, signal the gap:

```
[PDQG] ⚠️ PARTIAL infrastructure — only [tool] detected.
Recommend: Add [missing tools] to strengthen quality gates.
```

### 🚧 LEGACY

**Condition:** Zero quality tools detected.
**Action:** This project lacks quality infrastructure. The agent MUST:

1. Signal this explicitly in the delivery
2. NOT silently skip quality validation
3. Recommend tooling to the architect (cost-benefit decision is theirs)

```
[PDQG] 🚧 LEGACY — No quality tooling detected.
Impact: Cannot validate lint/tests before delivery.
Recommendation: Add ruff + pytest + mypy to pyproject.toml.
Decision: Architect must accept this risk explicitly.
```

---

## ⚙️ Step 3 — Execute and Enforce

For each **mandatory** tool:

1. **Run** the command
2. **If PASS** → record ✅ in the delivery note
3. **If FAIL** → **DO NOT DELIVER**:
   - Fix the issues, OR
   - If pre-existing failures unrelated to this change, signal explicitly:

     ```
     [PDQG] ⛔ BLOCKED — pre-existing failure in [file/tool].
     This failure is NOT caused by this change.
     Options: (a) fix now, (b) accept and note in delivery.
     ```

   - Never silently ignore failures

### Remediation-First Pipeline (Strict)

When linting/format tooling is available, the agent MUST execute:

1. `ruff check --fix .`
2. Format step (`ruff format .` or `black .`, when configured)
3. `ruff check .`
4. `mypy .` (if detected)
5. `pytest` (if detected)

`ruff check .` alone does NOT satisfy this policy when auto-fix is available.
The agent MUST provide evidence of a re-run after auto-fix.

---

## 📋 Step 4 — Include PDQG Status in Every Delivery

Every agent handoff message MUST include a PDQG status block:

### Example — EQUIPPED, all passing

```
[PDQG STATUS] ✅ Pre-Delivery Quality Gate PASSED
  Auto-fix:  ✅ ruff check --fix .
  Format:    ✅ ruff format .
  Lint:      ✅ ruff check . (re-run after fix)
  Types:     ✅ mypy .
  Tests:     ✅ pytest (42 passed, 0 failed)
  Coverage:  ✅ 87% overall
```

### Example — PARTIAL infrastructure

```
[PDQG STATUS] ⚠️ PARTIAL
  Auto-fix:  ✅ ruff check --fix .
  Lint:      ✅ ruff check . (re-run after fix)
  Tests:     ⚠️ No test runner detected
  Recommend: Add pytest to pyproject.toml
```

### Example — EQUIPPED, blocked

```
[PDQG STATUS] ⛔ BLOCKED — delivery withheld
  Auto-fix:  ✅ ruff check --fix .
  Lint:      ❌ ruff check . — 3 remaining errors in src/foo.py (E501, F401, I001)
  Action required: Fix lint errors before human review.
```

---

## 🗂️ For This Project (providence)

Detected tooling class: **EQUIPPED**

| Tool | Command | Status |
|---|---|---|
| Lint | `make lint` | MANDATORY |
| Tests | `make test` | MANDATORY |
| Pre-delivery (combined) | `make pre-delivery` | MANDATORY |
| Providence governance | `providence lint spec` | MANDATORY (included in `make lint`) |

- [ ] Ran `make pre-delivery` (or `make lint` + `make test`) — zero errors
- [ ] Applied auto-fix pipeline (`ruff check --fix .` + format + re-run)
- [ ] Included `[PDQG STATUS]` block in handoff message

### 🚩 The Agentic Boundary

The completion and reporting of the **PDQG Status** marks the absolute boundary of AI Agent autonomy.

- No Git mutations (commits, pushes, merges) are permitted after this point.
- The agent must hand over control to the human reviewer immediately after delivering the status block.

---

## ⚖️ Rationale

Pre-commit hooks only fire at `git commit` — which agents do not perform (P003).
CI runs after human handoff — too late. The quality gate must be **agent-owned**,
running before the handoff even starts. This policy closes the loop that existed
between governance validation (Step 9 of AGENT_ENTRYPOINT) and actual code quality.

**Reference:** `docs/spec/canonical/core/generated/AGENT_ENTRYPOINT.md` (Step 9)
**Reference:** `docs/spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW.md`
