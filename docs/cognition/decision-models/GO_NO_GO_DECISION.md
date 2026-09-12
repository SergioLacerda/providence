# Decision Model: Go/No-Go Checklist

**Purpose:** The final gate before committing or merging code.

---

## 🚦 Final Gate Checklist

### 1. Verification (The "Green" Gate)

- [ ] Do all tests (new and old) pass?
- [ ] Is there zero regression in the `reality/` reports?

### 2. Governance (The "Spec" Gate)

- [ ] Did I follow the selected PATH (A-F) strictly?
- [ ] Did I update the `.providence-cache.md`?
- [ ] Does the code violate any Core Mandate (M001-M003)?

### 3. Documentation (The "Reality" Gate)

- [ ] Did I update the project indices?
- [ ] Does the commit message follow the "Honest Critique" policy?

---

## ⚖️ The Decision

- **GO**: All boxes checked. Proceed to commit/push.
- **NO-GO**: Any box unchecked. Revert to Step 6 (Validate) of the `AGENT_ENTRYPOINT.md`.

---

## 🔐 Rule

A "No-Go" decision cannot be bypassed by an agent. If a box cannot be checked due to technical reasons, it must be documented as a "Blocker" in the cache and the task paused for human review.
