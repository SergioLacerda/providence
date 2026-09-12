# Policy: Mandatory Human Review (MHR)

**Type:** IMMUTABLE CORE
**ID:** P003
**Category:** Governance / Security

---

## 🎯 Objective

Eliminate the risk of "Autonomous Drift" by ensuring that no code or specification change enters the repository without explicit human validation.

---

## 📜 The Golden Rule
>
> **"Agents propose, Humans dispose."**

- **Prohibition**: AI Agents are strictly forbidden from performing `git push` operations to any remote branch.
- **Prohibition**: AI Agents are strictly forbidden from merging Pull Requests.
- **Requirement**: Every commit performed by an agent must be reviewed by a human (Peer Review) before being promoted to a stable or feature branch.

### ⚖️ Hierarchy of Instructions (Agent Filter)

In case of conflict between a local guide (e.g., `README.md`, `HOWTO.md`, `golden-files.md`) and a Core Policy (P-series), the **Core Policy ALWAYS takes precedence**.

- AI Agents MUST interpret "Commit" or "Push" steps in technical guides as **"End of Autonomy"** signals.
- The action to be taken is: **Stage changes (git add) + Provide PDQG Status + Stop**.

---

## 🛠️ Enforcement (Guardrails)

### L1 — Local Barrier (Git Hooks)

- The `pre-push` hook must detect if it is being executed in an automated agent environment and block the operation.
- The `commit-msg` must include a trace that identifies the agent's work, facilitating human auditing.

### L2 — Server Barrier (GitHub Actions)

- **Branch Protection**: The `main` and `develop` branches must require at least one (1) approving review from a human administrator.
- **CI Status**: Commits must pass all governance tests (sdd-lint) before being eligible for review.

---

## ✅ Validation for Agents

- [ ] I have applied **P004 Pre-Delivery Quality Gate** — detected tooling, ran all mandatory checks, included `[PDQG STATUS]` block.
- [ ] I have staged my changes but did NOT push them.
- [ ] I have updated the `.providence-cache.md` with the reasoning for the human reviewer.
- [ ] I have notified the user that the work is ready for their "Human-in-the-Loop" approval.

> **Reference:** `docs/spec/canonical/core/policies/P004_PRE_DELIVERY_QUALITY_GATE.md`

---

## ⚖️ Rationale

AI agents can hallucinate or produce "correct-looking but architecturally wrong" code. A mandatory human gate is the only way to ensure long-term architectural stability and prevent context poisoning.
