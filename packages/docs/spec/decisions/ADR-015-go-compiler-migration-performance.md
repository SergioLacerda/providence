# ADR-015: Python-to-Go Compiler Migration — Performance Comparison

## Status

- **Accepted** ✅
- Proposed: 2026-07-01
- Accepted: 2026-07-01

---

## Context

`packages/core/sdd_compiler` (the Python DSL/governance compiler) was replaced by
`tools/sdd-compile` (a Go binary) in commit `d48706d` ("refactor: replace Python-based
sdd_compiler package with new Go-based sdd-compile tool"). The rationale for the
migration is recorded in `tools/sdd-compile/DECISIONS.md`, which cites parsing/validation
performance on large mandate/guideline sets as the primary motivation.

No document compared actual performance between the two implementations. The only
published numbers, in `docs/spec/guides/PERFORMANCE.md` §5.3.C, do not measure the real
Python compiler — see below.

## Prior Benchmark Was a Placeholder, Not a Measurement

`tests/perf/benchmark_performance.py` (`CompileTimeBenchmark.run()`) is the source of the
1K/5K/10K mandate numbers published in `PERFORMANCE.md`. Its compile step is:

```python
# Simulate compilation (placeholder since dsl_compiler has issues)
start_time = time.perf_counter()
lines = spec.split("\n")
mandate_count = len([line for line in lines if line.startswith("- [")])
end_time = time.perf_counter()
```

It never calls `sdd_compiler.dsl_compiler.compile_string` (or any compiler code) — it
times a `str.split()` and a list comprehension. The 1,100×/200×/100× "speedup vs target"
figures in `PERFORMANCE.md` describe this placeholder, not the real Python compiler. This
ADR replaces those figures with a real measurement.

## Measurement Method

Both implementations were run on the same machine (Intel i5-4460 @ 3.20GHz), against the
same synthetic input: 400 mandates, matching the existing Go regression test
(`tools/sdd-compile/tests/perf_test.go::TestCompile400MandatesUnder50ms`).

- **Go**: `go test ./tests/ -bench BenchmarkCompile400Mandates -benchtime=20x`, calling
  `internal/compiler.Compile` directly.
- **Python**: the deleted `sdd_compiler` source was checked out from the parent of the
  deletion commit (`git worktree add <path> d48706d^`) and `sdd_compiler.dsl_compiler.compile_string`
  was called directly (5 runs, after 1 warmup run), with no other dependency (`sdd_compiler`'s
  compiler module has no runtime dependency on `providence_core`/`providence_telemetry`).

## Results

| Implementation | Input | Result |
|---|---|---|
| Python (`compile_string`, real) | 400 mandates | avg 4.76ms, min 4.68ms (5 runs) |
| Go (`compiler.Compile`) | 400 mandates | 3.27ms/op (20 iterations) |

**Go is ~1.45× faster than the real Python compiler** at this scale — a real, modest gain,
not the 2–3 orders of magnitude implied by the old placeholder-derived figures.

This does not contradict the migration decision: `tools/sdd-compile/DECISIONS.md` also
cites signing without an OpenSSL subprocess, msgpack number fidelity, and consolidation
with other Go tooling as reasons for the migration, independent of raw compile throughput.

## Decision

- Treat the `PERFORMANCE.md` §5.3.C figures as superseded by this ADR for anything
  comparing compiler implementations.
- Any future compiler benchmark suite must exercise the real compile path (Go: call
  `internal/compiler.Compile`; historically, Python: call `compile_string`), not a
  string-splitting placeholder.

## Consequences

**Positive:**

- Establishes an honest, reproducible baseline for the Go compiler's performance relative
  to what it replaced.
- Documents the placeholder defect in `tests/perf/benchmark_performance.py` so it is not
  mistaken for a real compiler benchmark in the future.

**Negative:**

- `tests/perf/benchmark_performance.py` itself was not fixed or removed as part of this
  ADR (out of scope for this mission) — it remains a placeholder and should not be relied
  upon for compiler performance claims until addressed.

## References

- `tools/sdd-compile/DECISIONS.md` — migration rationale
- `tools/sdd-compile/tests/perf_test.go` — Go compile benchmark
- `tests/perf/benchmark_performance.py` — placeholder benchmark (not fixed by this ADR)
- `docs/spec/guides/PERFORMANCE.md` §5.3.C — superseded figures
- Commit `d48706d` — Python→Go migration
