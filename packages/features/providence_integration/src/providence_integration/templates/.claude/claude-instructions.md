# Claude — SDD Governance Bootstrap
<!-- Governance fingerprint: {FINGERPRINT} -->
<!-- Drift check: fingerprint must match .providence/metadata.json → governance_fingerprint -->

You are operating in a workspace governed by **Spec Driven Development (SDD)**.

## Critical Instruction

Read and adhere to the canonical governance rules in:
```
.providence/agent-instructions.md
```

This file is the **single source of truth** for all governance policies in this workspace.

## Quick Reference

- **Mandate enforcement**: Non-negotiable rules — see `.providence/source/mandates/mandates.md`
- **Governance status**: Run `providence runtime status` to check workspace health
- **Validation**: Run `providence governance validate` before commits
- **Activation**: Governance activates automatically on project load via `.providence/seedlings/`

## For Questions

All governance documentation lives in `.providence/source/`:
- `mandates/mandates.md` — Mandate descriptions and enforcement rules
- `guidelines/` — Customizable guidelines by category
- `README.md` — Onboarding guide for agents

## Safe Fallback

If `.providence/` is missing or incomplete, do not proceed — ask the human to run `providence wizard`
to regenerate the governance template.
