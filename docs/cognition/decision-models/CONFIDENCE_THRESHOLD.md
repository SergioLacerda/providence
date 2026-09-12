# Decision Model: Confidence Threshold

**Purpose:** Define when to proceed autonomously, when to pause and validate, and when to escalate. Prevents both analysis paralysis and reckless execution.

---

## 📊 Confidence Scale

| Level | Score | Description | Action |
|---|---|---|---|
| **High** | 80–100% | Fully understand the change, tests exist, impact is clear | Proceed autonomously |
| **Medium** | 50–79% | Understand the core, but some edge cases are unclear | Proceed with extra validation steps |
| **Low** | 20–49% | Missing context, unclear requirements, or no test coverage | Pause — gather information first |
| **Unknown** | < 20% | Can't reason about the change safely | **Stop. Escalate.** |

---

## 🧮 Confidence Self-Assessment

Ask these 5 questions before starting:

1. **Can I describe the expected behavior before and after my change?** (20 pts if YES)
2. **Are there existing tests that cover the affected area?** (20 pts if YES)
3. **Do I understand all callers/consumers of what I'm changing?** (20 pts if YES)
4. **Is the rollback path clear and safe?** (20 pts if YES)
5. **Has this type of change been done before in this codebase?** (20 pts if YES)

Sum = your confidence score.

---

## 🚦 Confidence Gates

### Before writing any code

- Score < 50%? → Read relevant `spec/canonical/` first
- Score < 20%? → Load `cognition/context-loading/path-routing.md` and re-classify the task

### Before merging

- Did the implementation reveal new unknowns? → Re-assess confidence
- New score < 50%? → Write tests for the unknowns before merging

---

## ⚠️ Override Rule

**Never let time pressure override a low confidence score.**
A fast wrong answer is more expensive than a slow right one.

---

## References

- Anti-pattern: [`anti-patterns/PREMATURE_EXECUTION.md`](../anti-patterns/PREMATURE_EXECUTION.md)
- ADR process: [`spec/decisions/`](../../spec/decisions/)
- Providence Governance Gate: [`AGENT_ENTRYPOINT.md`](../../spec/canonical/core/generated/AGENT_ENTRYPOINT.md) — includes the governed bootstrap flow and confidence-aligned execution protocol.
