name: {{ name }}
version: 1.0.0
category: {{ category }}
description: {{ description }}
when_to_use:
- "{{ when_to_use_0 }}"
outcomes:
- policy_result
- next_actions
allowed_tools:
- sdd runtime status
cli_fallback:
- sdd runtime status
required_permissions:
- workspace-read
execution_path: PATH_A
status: active
deprecated_after: null
sunset_after: null
risk_score: {{ risk_score }}
tags:
- {{ category }}
budget_policy:
  token_budget: {{ token_budget }}
  timeout_seconds: 120
  max_retries: 1
escalation_policy:
  mode: warn
  require_human_on:
  - critical_violation
  - repeat_failure
telemetry_policy:
  emit_runtime_event: true
  otel_required_if_enabled: true
validation_policy:
  require_preflight: true
  require_postcheck: true
schema_version: 1.1.0
deprecation_due: false

# V6 fields — fill in before committing (skillsV6.md §3.2)
triggers: []
forbidden: []
fallback_to: null
idempotent: false
context_policy:
  max_context_tokens: 1800
  default_detail: minimal
