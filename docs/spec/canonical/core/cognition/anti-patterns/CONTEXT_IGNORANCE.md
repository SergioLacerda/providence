# 🚫 ANTI-PATTERN — Context Ignorance

## 🎯 Description

Agent executes without loading runtime context.

---

## ❌ Behavior

- Skips `.providence/source/`
- Uses only prompt memory
- Ignores search indices

---

## 🔥 Impact

- inconsistent results
- broken assumptions
- loss of governance

---

## ✅ Prevention

Agent MUST:

1. Load runtime context
2. Use indices
3. Validate state before execution
