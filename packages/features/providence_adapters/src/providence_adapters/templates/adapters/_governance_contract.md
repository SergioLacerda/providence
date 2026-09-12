## Hard-Mode Governance Fields

When command output includes governance fields, preserve and report them by name:

- `execution_gate`
- `gate_reason`
- `intake_index_mode`
- `intake_chunks`
- `governance_mode`
- `delegation_status`
- `delegation_executed`
- `provider_bound`

If `execution_gate: blocked`, stop and report `gate_reason`.
If `execution_gate: allowed`, continue only within the command or skill contract.
`intake_index_mode: none` is independent from `execution_gate`; surface it by
name and value, and do not describe it as a blocked gate unless
`execution_gate: blocked` is also present.
