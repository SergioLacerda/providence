---
governance_source:
  id: HBK-RUNBOOK-CONSULTATION
  type: handbook
  kind: decision_model
  status: active
  title: Runbook Consultation
  refs: [M003, M005]
  task_types: [planning, implementation, diagnosis]
  operation_phases: [context_loading, planning]
  load_policy:
    mode: selective
    max_tokens: 900
    require_relevance_reason: true
  summary: How agents select one operational runbook without loading the whole runbook corpus.
---

# Runbooks

Reusable operational procedures for Providence maintainers and agents.

Runbooks are not the same as guides. `docs/guides/` contains tutorials,
references, onboarding material, and topic guides. `docs/runbooks/` contains
repeatable procedures for recognized operational situations: symptoms,
diagnosis, resolution, rollback, and post-incident follow-up.

`docs/` is the authored source of truth. `.providence/` is generated runtime output.
Do not edit `.providence/` directly to publish or change runbooks; change authored docs
first, then regenerate runtime artifacts when a runtime task explicitly requires
it.

## Start Here

| Situation | Runbook |
|---|---|
| Authored governance docs disagree with generated runtime output | [Governance Runtime Drift](governance-runtime-drift.md) |
| Local development uses the wrong `sdd` executable | [Client Bootstrap PATH Shadowing](client-bootstrap-path-shadowing.md) |
| Standalone Windows compiler metadata/version skew | [Windows Standalone Compiler Skew](windows-standalone-compiler-skew.md) |
| Docs site or selector publication fails | [Docs Site Selector Publish](docs-site-selector-publish.md) |
| Strict MkDocs build fails on stale links | [Docs Link Rot Strict MkDocs](docs-link-rot-strict-mkdocs.md) |
| Standalone compiler release assets are missing | [Release Asset Recovery](release-asset-recovery.md) |
| Context budget is breached or near breach | [Context Budget Breach](context-budget-breach.md) |
| A GitHub Actions job fails and the failure looks familiar | [CI Known Failure Triage](ci-known-failure-triage.md) |
| Container Trivy scan reports stale Python package CVEs | [Container Trivy Vulnerability Remediation](container-trivy-vulnerability-remediation.md) |
| Need to confirm whether a `pending/`/`refined/` package was actually implemented before closing it | [Verifying Implemented Demands](verifying-implemented-demands.md) |

## Existing Operational References

- [Incident Response Playbooks](../incidents/PLAYBOOKS.md)
- [Failure Ledger](../incidents/FAILURE_LEDGER.md)
- [Landing / Site Maintenance Runbook](../maintenance/landing-site-runbook.md)
- [Runbook Hardening Protocol](../guides/operations/RUNBOOK_HARDENING_PROTOCOL.md)

## Existing Canonical Spec Runbooks

These remain in `docs/spec/canonical/specifications/runbooks/` and are linked
here as source paths because that canonical subtree is excluded from the published
MkDocs site:

- `docs/spec/canonical/specifications/runbooks/vector-search-down.md`
- `docs/spec/canonical/specifications/runbooks/db-slow-queries.md`
- `docs/spec/canonical/specifications/runbooks/llm-rate-limited.md`
- `docs/spec/canonical/specifications/runbooks/memory-leak.md`

## Runtime Use

This index is an authored handbook source. Runtime generation emits it to
`.providence/source/handbook/runbooks/index.yaml`; direct `.providence/` edits remain
forbidden.

Runtime agents use this file as a selector, not as a bulk-load target:

- load the index when the task mentions operational failure, diagnosis, hotfix,
  repeated failure, release recovery, generated-runtime drift, or context-budget
  breach;
- choose one matching runbook leaf from the table above and record the relevance
  reason;
- load the selected leaf only after the reason is explicit;
- fall back to `docs/incidents/PLAYBOOKS.md` when no existing runbook matches an
  active incident.
