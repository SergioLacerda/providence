# Runbook Authoring Standard

Use this standard for every file in `docs/runbooks/`.

## Required Sections

Each runbook must include:

1. `Symptoms`
2. `Diagnosis`
3. `Resolution Steps`
4. `Rollback`
5. `Post-Incident`
6. `Evidence To Attach`
7. `Sources`

Add `Escalation` when the procedure can affect releases, production,
governance artifacts, security posture, or user data.

## Rules

- Keep the procedure executable without broad rediscovery.
- Name concrete commands when the command is stable.
- Separate diagnosis from resolution.
- Prefer read-only checks before write actions.
- Document rollback or state restoration before risky steps.
- Link the source docs used to derive the runbook.
- State whether `.providence/` is an output to regenerate, not an authored source to edit.

## Verification State

Every runbook should make clear whether it is:

- `documented`: derived from existing docs, not freshly rehearsed;
- `validated`: command sequence recently ran successfully;
- `incident-backed`: derived from a recorded incident or failure ledger entry.
