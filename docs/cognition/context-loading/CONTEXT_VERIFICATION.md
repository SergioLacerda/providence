## ❓ The Two-Question Quiz (Mandatory)

Before requesting ANY additional context or performing research, the agent must ask:

1. **Do the Governance Rules (`spec/canonical/`) already solve this?**
    * *If YES:* Apply the rule and return. Do NOT proceed with more research.
    * *If NO:* Proceed to the next question.

2. **Does the Local Cache (`.providence-cache.md`) already solve my doubt?**
    * *If YES:* Use the cached information and return.
    * *If NO:* Only now is it permitted to expand context or perform new research.

---

## ✅ Pre-Flight Verification

Before writing the first line of code, the agent must pass this checklist:

### 1. The Anchor Test

* [ ] Can I locate the exact line/function where the change starts?
* [ ] Do I have the `spec/canonical/` rules for that specific module?

### 2. The Dependency Test

* [ ] Do I have the interfaces for all direct dependencies of the code I'm touching?
* [ ] Do I have the `pyproject.toml` or equivalent to check package versions?

### 3. The Validation Test

* [ ] Do I know which test command to run to verify my change?
* [ ] Do I have the context of the existing test suite layout?

---

## 🔍 The "Blind Spot" Search

Actively look for what's missing:

* **Missing ADRs**: Is there a "Why" behind this complex code that I haven't read yet? Check `spec/decisions/`.
* **Missing Boundaries**: Am I about to touch a file that belongs to a different package? Check `PROJECT_BOUNDARY.md`.
* **Missing Patterns**: Am I inventing a new way to do something that is already solved? Check `spec/reference/templates/`.

---

## 🔁 The Expansion Trigger

If during implementation a "Blind Spot" is hit:

1. **Pause** execution.
2. **Identify** the missing piece of context.
3. **Load** only that piece.
4. **Log** the expansion: *"Expanded context to include [File X] because [Reason]."*

---

## 📏 Benchmark

If you have to stop execution more than twice to load missing context:
→ Your initial PATH classification was too low. Upgrade from PATH B to PATH C.

---

## References

* Confidence model: [`../decision-models/CONFIDENCE_THRESHOLD.md`](../decision-models/CONFIDENCE_THRESHOLD.md)
* Routing: [`path-routing.md`](./path-routing.md)
