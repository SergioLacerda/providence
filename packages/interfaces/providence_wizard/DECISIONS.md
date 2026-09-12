# SDD Wizard — Decision Log

**Module:** `packages/interfaces/providence_wizard`
**Purpose:** Interactive setup wizard, workspace initialization, user-facing IDE/UI
**Owner:** @SergioLacerda

---

## DEC-2026-001: Wizard as Optional Interface (Not Required) (2026-02-01)

**Decision:** Wizard is convenience layer, not required for core SDD functionality

**Rationale:**
- CLI is primary: providence ask, sdd compile, providence runtime work standalone
- Wizard is optional: IDE users, onboarding, setup automation
- Independence: Wizard can evolve separately
- Accessibility: Users who prefer terminal not forced to use GUI

**Consequence:** Core features tested via CLI, wizard tested separately

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-002: Wizard Uses Artifacts from Integration (2026-02-15)

**Decision:** Wizard reads pre-built artifacts from generated/master/compiled/, doesn't build own

**Rationale:**
- Delegation: Compiler owns artifact build, wizard owns UI
- Consistency: Same artifacts everywhere (CLI, wizard, CI)
- Speed: Wizard doesn't rebuild on every load
- Testing: Can mock artifacts in wizard tests

**Flow:**
1. Compiler builds artifacts
2. Integration validates + backups
3. Wizard reads from generated/master/compiled/
4. User sees governance context via wizard UI

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-003: Interactive Profile Setup (Init Wizard) (2026-03-01)

**Decision:** `providence init` runs interactive wizard (questions, validation, setup)

**Rationale:**
- UX: New user doesn't need to edit config manually
- Validation: Wizard checks paths, permissions, dependencies
- Guidance: Explains what each option means
- Error recovery: Clear instructions if setup fails

**Flow:**
1. `providence init` starts wizard
2. Ask: Master or Client profile?
3. Ask: Workspace name?
4. Ask: Python version?
5. Ask: Install dependencies?
6. Create .providence/profile + initial directories
7. Run basic tests to verify setup

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-004: CLAUDE.md Generator (Wizard Feature) (2026-03-15)

**Decision:** Wizard can generate optimized CLAUDE.md from .providence metadata

**Rationale:**
- Convenience: Users don't write CLAUDE.md manually
- Consistency: Generated from authoritative .providence sources
- Versioning: Regenerate when workspace updates

**Example:**
```bash
providence wizard generate-claude
# Creates: CLAUDE.md (with governance, paths, policies)
```

**Status:** ACTIVE
**Owner:** @SergioLacerda
**Reference:** Wizard gaps & fixes memory note

---

## DEC-2026-005: Status Dashboard (Wizard Display) (2026-04-01)

**Decision:** Wizard shows dashboard: governance status, budget, telemetry, recent activity

**Rationale:**
- Overview: User sees health at a glance
- Observability: Quick checks without digging logs
- UX: Pretty display, not raw JSON
- Actionable: Links to fix common issues

**Dashboard shows:**
- ✅ Workspace initialized? Profile type?
- ✅ Artifacts present? (governance-core, governance-client)
- ✅ Metadata valid? (version, compile timestamp)
- ✅ Budget status: X/Y tokens (%) used
- ✅ Cache stats: hits/misses, hit rate
- ✅ Recent queries: top 5 by frequency
- ✅ Errors: any warnings/failures

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-006: Lazy Loading (Don't Load Everything on Startup) (2026-04-10)

**Decision:** Wizard loads artifacts on-demand, not all at startup

**Rationale:**
- Speed: Wizard launches instantly
- Memory: Large artifacts only loaded if needed
- UX: Responsive, not hanging during load

**Example:**
- Startup: Just load workspace metadata
- Click "View Governance": Load artifacts
- Click "Run Query": Run query, cache result

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-007: Error Boundaries (Don't Crash on Artifact Issues) (2026-04-15)

**Decision:** If artifact load fails, show helpful error (not crash)

**Rationale:**
- UX: User understands what went wrong
- Recovery: Error message shows fix (rebuild, restore backup, etc.)
- Resilience: Wizard stays responsive even if data broken

**Example:**
```
Error: Governance artifact corrupted
  File: generated/master/compiled/governance-core.msgpack
  Hash mismatch: expected abc123..., got def456...

Recovery:
  1. Rebuild: python -m sdd_compiler
  2. Or restore backup: cp .backup/governance-core.msgpack generated/...
  3. Verify: providence runtime status --verify
```

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-008: Wizard State (Session Persistence) (2026-05-01)

**Decision:** Wizard remembers user preferences (theme, layout, expanded sections)

**Rationale:**
- UX: User customizes view once, not repeatedly
- Personalization: Different users, different preferences
- State file: ~/.providence/runtime/wizard-state.json

**Persisted:**
- Theme: dark/light
- Layout: sidebar width, split ratio
- Expanded sections: which sections open by default
- Recent queries: history for quick access

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-009: Query History & Favorites (2026-05-05)

**Decision:** Wizard tracks query history and allows marking favorites

**Rationale:**
- Convenience: Common queries one-click
- Insights: Trending queries show user patterns
- Discoverability: See what others frequently query

**Features:**
- History: Last 100 queries (with timestamps, results)
- Favorites: Pin frequent queries to top
- Export: Save history as JSON/CSV for analysis

**Status:** ACTIVE
**Owner:** @SergioLacerda

---

## DEC-2026-010: Responsive Design (Mobile, Tablet, Desktop) (2026-05-10)

**Decision:** Wizard UI adapts to screen size (responsive CSS)

**Rationale:**
- Accessibility: Work from any device
- Future-proof: Support tablets, phones (if Wizard becomes web app)
- Professional: Modern UX expectations

**Breakpoints:**
- Mobile: <600px (stacked layout, single column)
- Tablet: 600-1024px (2-column with fold)
- Desktop: >1024px (full dashboard)

**Status:** PENDING (not yet implemented, design placeholder)
**Owner:** @SergioLacerda
**Priority:** Phase 6 (nice-to-have)

---
