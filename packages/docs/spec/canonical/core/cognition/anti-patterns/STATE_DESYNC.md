# Anti-Pattern: State Desynchronization

## Definition

Operating on stale, incomplete, or contradictory execution state, leading to decisions and implementations that are based on assumptions no longer true about the current workspace or project condition.

---

## Symptoms

- "This worked yesterday, but now it's broken"
- `.providence-cache.md` is not updated or reflects old task
- Making decisions based on memory of previous session (not current state)
- `.providence/source/` files are missing or out-of-date
- Changes made by previous task/agent not reflected in current understanding
- Executing Phase N work on top of incomplete Phase M-1 state

---

## Examples

- ❌ Making architectural changes without reading `.providence-cache.md` first
- ❌ Assuming "we always do X this way" without checking current rules
- ❌ Implementing a feature on top of another task's half-finished work
- ❌ Ignoring drift detection warnings from `providence runtime status`
- ❌ Using local knowledge from previous session instead of current `.providence/source/`
- ❌ Skipping handshake protocol (PHASE 0) and jumping directly to implementation

---

## Root Cause

- Skipping PHASE 0 context verification (mandated in AGENT_RUNTIME_PROTOCOL)
- Not reading `.providence-cache.md` at task start
- Assuming state hasn't changed since previous work
- Not running `providence runtime status` to detect drift
- Working in parallel without synchronization (violates PATH D safety rules)
- Ignoring workspace alerts/warnings

---

## Impact

- ❌ Implementing on stale assumptions (rework required)
- ❌ Violating M003 (Context Awareness) — `.providence-cache.md` not read/updated
- ❌ Introducing bugs from incomplete previous work
- ❌ Conflicting changes if working in parallel without coordination
- ❌ Audit trail breaks (state history becomes incoherent)
- ❌ Potential data loss or state corruption

---

## Prevention

1. **Always start with PHASE 0** — Run handshake protocol from [AGENT_RUNTIME_PROTOCOL.md](../../generated/AGENT_RUNTIME_PROTOCOL.md)
2. **Read `.providence-cache.md`** — First action in every session (mandated by M003)
3. **Check workspace state** — Run `providence runtime status --verbose` to detect drift
4. **Verify no parallel mutations** — If PATH D (parallel work), use `.providence-cache.md` coordination
5. **Load `.providence/source/`** — Use project runtime state, not session memory

---

## Cure

**Immediate (if detected during execution):**

1. **Stop.** Do not proceed with current assumptions.
2. **Synchronize:** Read `.providence-cache.md` and run `providence runtime status`
3. **Detect drift:** Check for `governance.drift.detected` events
4. **Re-assess:** Update your understanding of current state
5. **Restart PHASE 0** if needed
6. **Resume** with accurate state

**After detection:**

1. Commit any partial work with clear checkpoint comment
2. Update `.providence-cache.md` with current state
3. Run full validation: `providence governance validate`
4. Document what drifted and why

---

## Related

- [M003: Context Awareness](../../mandates/M003_CONTEXT_AWARENESS.md) — `.providence-cache.md` requirement
- [AGENT_RUNTIME_PROTOCOL.md](../../generated/AGENT_RUNTIME_PROTOCOL.md) — PHASE 0 handshake (mandatory)
- [execution-budget.md](../../economy/execution-budget.md) — Drift detection and circuit breaker rules
- [DriftDetector](../../../../../../../../../packages/core/providence_runtime/) — How drift is detected
