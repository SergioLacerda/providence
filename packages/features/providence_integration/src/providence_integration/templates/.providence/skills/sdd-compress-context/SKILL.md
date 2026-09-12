---
name: sdd-compress-context
description: Reduce context footprint while preserving governance context.
risk: low
---

# compress-context

## Purpose

Reduce the token footprint of the current session context while preserving all governance-critical information. Applies token economy policies to identify and summarize or discard low-value context segments.

## When to use

- Token usage is high (approaching budget ceiling)
- Session has grown long with accumulated context
- Before starting a new complex task requiring full context budget
- When `sdd runtime status` reports context above compression threshold

## Required protocol

1. Load `.providence/agent-instructions.md`
2. Confirm skill is registered in `.providence/skills/registry.json` as `sdd-compress-context`
3. Check current status: `sdd runtime status`
4. Apply compression: identify and summarize low-value context
5. Preserve: governance mandates, active task state, critical decisions
6. Return `policy_result` and compressed context summary

## Allowed CLI

- `sdd runtime status`

## Output format

Return YAML with:
- `policy_result`: PASS | WARN
- `tokens_before`: estimated token count before compression
- `tokens_after`: estimated token count after compression
- `preserved`: list of preserved context segments
- `discarded`: list of discarded context segments

## Non-compliance

- Do not discard active governance mandates or policy constraints
- Do not discard the current task state or uncommitted decisions
- Do not compress below the governance context floor
