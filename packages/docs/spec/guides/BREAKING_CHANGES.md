# Breaking Changes — Request for Comments (RFC) Process

Any change that could require users to update their code or governance artifacts must follow this RFC process.

---

## What Constitutes a Breaking Change?

### CLI/Commands

- Removing a command (e.g., `providence governance compile` deleted)
- Renaming a command (e.g., `providence ask` → `sdd query`)
- Removing a required flag
- Changing output format without `--format` backward-compat option
- Changing exit code behavior

### Governance/Schema

- Removing a field from `RuntimeEvent` (telemetry schema)
- Removing a field from compiled governance artifacts
- Adding a new mandatory field without default value
- Changing the semantics of existing fields (e.g., `tokens_total` now means something different)
- Changing event names (e.g., `governance.ask` → `governance.query`)

### API/Packages

- Removing a public function or class
- Changing a function signature (parameter name, type, order)
- Removing an import/module
- Changing return type of a public function

### Mandates/Governance

- Adding a new mandatory compliance requirement (e.g., M006)
- Making a soft policy enforcement strict
- Changing the definition of a breach condition

### Policies

- Changing storage paths (e.g., `.providence/` directory moved to `.providence/runtime/`)
- Changing artifact serialization format (e.g., JSON → msgpack without backwards compat)

---

## What Is NOT a Breaking Change?

- Adding a new optional flag or field (default to `None` or falsy)
- Adding a new command
- Adding a new public function/class
- Improving error messages
- Improving performance
- Fixing bugs (even if behavior changes unexpectedly)
- Adding new event types
- Deprecating a feature (if removal doesn't happen yet)

---

## RFC Process (7 Steps)

### Step 1: Open RFC Issue

**Before coding**, open a GitHub issue titled:

```
[RFC] Breaking Change: <short description>

Example:
[RFC] Breaking Change: Remove --verbose flag from providence governance compile
```

**Required in issue body:**

```markdown
## Summary
One-paragraph description of the breaking change.

## Motivation
Why is this breaking change necessary? What problem does it solve?

## Impact Analysis
- Affected components: [CLI / API / Schema / Mandates]
- Number of users likely impacted: [estimate]
- Estimated migration effort: [low / medium / high]

## Migration Path
How will existing users migrate? Provide step-by-step instructions.

Example:
```bash
# Old (v0.1.0):
providence governance compile --verbose

# New (v1.0.0):
providence governance compile
providence runtime status --verbose  # use the new command instead
```

## Deprecation Window

If applicable, propose deprecation timeline:

- v0.2.0 (next minor): Add deprecation warning, keep feature working
- v1.0.0 (next major): Remove feature

## Alternatives Considered

What other approaches were considered? Why is this the best option?

Example: Could we add a `--legacy` flag instead? (No, because...)

```

### Step 2: Community Discussion (7-14 Days)

- **Assignee:** Label with `breaking-change`, `discussion`
- **Comment period:** Minimum 7 days (14 for major changes)
- **Core team review:** @SergioLacerda or governance leads must approve before proceeding
- **Approval criteria:**
  - Migration path is clear and documented
  - No simpler alternative exists
  - Impact is justified by benefit

### Step 3: Decision & Approval

After discussion, core team decides:

- **✅ Approved** → Label `approved-breaking-change`, schedule for release
- **⏸️ Deferred** → Schedule for future major version
- **❌ Rejected** → Close issue with explanation

Approval decision should be made by at least 2 reviewers.

### Step 4: Update Version Plan

Add to CHANGELOG.md under `[Unreleased]` → `Breaking Changes` section:

```markdown
## [Unreleased]

### Breaking Changes
- **CLI:** Removed `--verbose` flag from `providence governance compile`
  - Migration: Use `providence runtime status --verbose` instead (see #123)
```

### Step 5: Implement & Test

Create PR that:

1. References the RFC issue: `Closes #<issue_number>`
2. Includes deprecation warning (if applicable)
3. Updates `CHANGELOG.md` with migration instructions
4. Adds/updates tests for new behavior

### Step 6: Version Bump & Release

Breaking changes **always** trigger a **major version bump** (X.0.0):

- v0.1.0 → v1.0.0 (first breaking change)
- v1.2.3 → v2.0.0 (subsequent breaking changes)

Update `CHANGELOG.md`:

- Rename `[Unreleased]` to `[X.0.0] — YYYY-MM-DD`
- List all breaking changes in dedicated section
- Include migration instructions for each

### Step 7: Document in Release Notes

GitHub Release notes must include:

```markdown
## ⚠️ Breaking Changes

### Removed: `--verbose` flag from providence governance compile
Replaced by `providence runtime status --verbose`.

**Migration:**
```bash
# Before:
providence governance compile --verbose

# After:
providence governance compile
providence runtime status --verbose
```

```

---

## Example: Full RFC Workflow

### Scenario: Remove `--old-format` flag from `providence ask`

**Date:** May 1, 2026

**Step 1:** Open issue

```

Title: [RFC] Breaking Change: Remove --old-format flag from providence ask

Body:

## Summary

Remove --old-format flag. Output will always be JSON.

## Motivation

Simplify CLI; JSON is now the standard. The flag is undocumented.

## Impact Analysis

- Affected: CLI (providence ask command)
- Users likely impacted: ~10% (flag is undocumented)
- Migration effort: Low (1 line change in scripts)

## Migration Path

Users with `providence ask --old-format` should remove the flag:

```bash
# Old: providence ask --old-format <query>
# New: providence ask <query>
```

## Deprecation Window

- v0.2.0: Add warning "Flag --old-format is deprecated"
- v1.0.0: Remove flag entirely

```

**Step 2–3:** 10-day discussion, approved by 2 reviewers

**Step 4:** Update CHANGELOG.md

**Step 5:** PR with changes:
- Remove `--old-format` handling in `ask.py`
- Update tests
- Update help text

---

## Active Timeline: Legacy Path Deprecation (ADR-014)

This repository enforces an explicit timeline for `/legacy/**` references:

- **Q3 2026 (2026-07-01 to 2026-09-30):** deprecation phase
  - Legacy path usage may continue only with structured deprecation warning and migration guidance.
- **Q4 2026 (from 2026-10-01):** removal phase
  - Legacy path usage is treated as blocking error in runtime/CI validation paths.

Any rollout or exception proposal that modifies this timeline must open an RFC issue and reference ADR-014.

**Step 6:** Release v1.0.0 (first major version, triggered by breaking change)

**Step 7:** Release notes clearly state removal

---

## Checklist for Breaking Changes

Before opening RFC issue:

- [ ] Breaking change is truly necessary (not a workaround alternative)
- [ ] Migration path is documented
- [ ] Impact is justified
- [ ] No simpler (non-breaking) alternative exists
- [ ] Core team has been informally consulted

Before merging PR:

- [ ] RFC issue approved
- [ ] CHANGELOG.md updated with migration instructions
- [ ] Tests pass
- [ ] Help text / docs updated
- [ ] Version bumped to next major (X.0.0)

Before releasing:

- [ ] Release notes include breaking change section
- [ ] Migration instructions are clear
- [ ] GitHub Releases include deprecation warnings (if applicable)

---

## FAQ

**Q: Can we make a breaking change without an RFC?**
A: No. All breaking changes must follow this process. No exceptions.

**Q: What if it's an obvious fix?**
A: Even obvious fixes require an RFC issue (can be resolved quickly). This ensures visibility.

**Q: Can we batch multiple breaking changes in one release?**
A: Yes. Discuss in a single RFC issue or link related issues.

**Q: What about internal/private APIs?**
A: If not documented as public, changes are not "breaking" per se. Still open an RFC if impact is significant.

---

## Related

- [Compatibility Matrix](./COMPATIBILITY.md) — Supported versions & semver contract
