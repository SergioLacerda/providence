# RFC-NNN: <Title>

**Status:** Draft (this is a template — copy and fill in)

**Instructions:** Copy this file to `RFC-NNN-<slug>.md`, fill in all sections below, and submit as a Pull Request.

---

## Context

### Problem

**One paragraph** describing the problem or limitation you're trying to solve. Examples:

- "The current artifact format is JSON, which is 3x slower to parse than MessagePack and takes 2x more disk space."
- "The runtime policy evaluator runs synchronously, blocking all concurrent queries if one policy takes >100ms."
- "The CLI has no way to filter results by type, forcing users to pipe output to jq."

### Current State

Describe the **status quo**: What is the existing design? What are its limitations?

### Why This Matters

Why should the team care? What is the impact if we don't fix this?

- Performance impact? (e.g., "Queries timeout in production")
- Scaling limitation? (e.g., "Can't support >1000 concurrent users")
- Developer experience? (e.g., "New contributors struggle to onboard")
- Security gap? (e.g., "Path traversal vulnerability in artifact loading")

### Scale / Scope

Which packages or components are affected? How many users would see the change?

Example:

- Affects: sdd_compiler (artifact generation), providence_runtime (artifact loading), providence_cli (output)
- Scope: All users who run `providence ask` or `sdd compile`

---

## Proposed Decision

### The Proposal

**One sentence:** State the decision as an imperative.

Example: "Switch from JSON to MessagePack for artifact serialization."

### Why This Approach?

Explain the **rationale** in 2-3 sentences. Address the problem statement above.

Example:
> MessagePack is a binary serialization format that is:
>
> - 3x faster to parse than JSON (benchmarked at 1000-item artifacts)
> - 50% smaller on disk (saves ~150KB per artifact)
> - Backward compatible with Python 3.10+ (via the `msgpack` library)
>
> This solves the performance bottleneck in artifact loading without changing the public API.

---

## Alternatives Considered

### Alternative 1: <Name> — **Rejected because**: <reason>

Example:
> Use Protobuf instead of MessagePack.
>
> **Rejected because**: Protobuf requires defining a schema (`.proto` file) and code generation step. This adds complexity to the compiler pipeline and makes changes to the governance schema harder to iterate on. MessagePack is simpler and doesn't require pre-compiled schemas.

### Alternative 2: <Name> — **Rejected because**: <reason>

Example:
> Keep JSON but add optional MessagePack support.
>
> **Rejected because**: Supporting two serialization formats doubles testing burden, complicates the artifact loading logic, and doesn't solve the performance problem for existing deployments.

---

## Consequences

### Positive ✅

- <Benefit or improvement>
- <Benefit or improvement>

Example:

- Artifact load time reduces from 15ms to 5ms (benchmark shows 3x speedup)
- Artifact file size reduces by 50%, saving disk space on long-lived deployments
- No public API change; artifact loading is internal to providence_runtime

### Negative ⚠️

- <Trade-off or drawback>
- <Trade-off or drawback>

Example:

- Users cannot directly inspect artifacts with `cat` or text editors (must use `providence runtime inspect`)
- New dependency on `msgpack` library adds ~50KB to the wheel

### Risks 🚨

- <Risk statement — include mitigation>

Example:

- **Risk**: Artifact format change could break old deployments if clients expect JSON.
  - **Mitigation**: Implement version detection in artifact loading; if old format detected, convert or prompt user to regenerate.
- **Risk**: MessagePack library could have security vulnerabilities.
  - **Mitigation**: Use only the official `msgpack` library from PyPI; audit dependencies monthly with `pip-audit`.

---

## Acceptance Criteria

How will we know this decision is correctly implemented? List measurable criteria.

Example:

- [ ] Benchmark shows artifact load time <5ms for 1000-item artifacts
- [ ] All existing tests pass (no behavior change)
- [ ] New test case verifies MessagePack deserialization
- [ ] COMPATIBILITY.md updated to note artifact format change (breaking change in major version)
- [ ] Error handling tested: corrupt artifacts fail gracefully with helpful error message

---

## Implementation Plan (Optional)

If you have a clear implementation strategy, outline it here. This can help reviewers understand the scope.

Example:

1. Create `sdd_compiler/serialization.py` with `serialize_to_msgpack()` and `deserialize_from_msgpack()`
2. Modify `sdd_compiler/integrate.py` to call the new serialization functions
3. Modify `providence_runtime/context.py` to deserialize MessagePack instead of JSON
4. Update tests in `tests/unit/compiler/test_integration.py` and `tests/unit/runtime/test_context.py`
5. Add performance benchmark in `tests/perf/benchmark_*.py`
6. Update COMPATIBILITY.md to document breaking change (move to next major version)

---

## Review Checklist

Before submitting:

- [ ] All sections above are completed
- [ ] No placeholder text remains (remove examples)
- [ ] Alternatives section has at least 2 alternatives
- [ ] Consequences section clearly states risks and mitigations
- [ ] Acceptance criteria are measurable
- [ ] Does not duplicate an existing ADR (check `docs/spec/decisions/`)

---

## Next Steps After Review

1. **Open PR** with this RFC file
2. **Label**: Add `rfc` label
3. **Tag reviewers**: @<package-owner-1>, @<package-owner-2>, @<core-maintainer>
4. **Comment period**: 7 days (14 days if cross-team)
5. **Decision**: Accepted → rename to `ADR-NNN-*`, Rejected → document reason
6. **Implementation**: After acceptance, create implementation PR
7. **Close out**: Update ADR status from `Accepted` to `Implemented` when code is merged

---

## Questions?

Refer to the [RFC/ADR Process Guide](../guides/RFC_PROCESS.md) for more details.
