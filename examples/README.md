# Providence — Examples

Runnable demos showing SDD governance enforcement with popular agentic frameworks.

Each demo uses real framework code with optional dependencies. They are not part of the CI test suite — run them locally after installing the relevant extras.

---

## LangGraph — Tool Guardrail

**What it shows:** An agent declares a tool (`send_email`) that is not authorized in the active SDD mandate. The SDD runtime API blocks execution before the graph runs.

```bash
uv run --extra examples-langgraph python examples/langgraph/demo_tool_guardrail.py
```

Expected output: `BLOCKED` with the violated mandate reference.

---

## CrewAI — Spec Drift Detection

**What it shows:** A CrewAI crew is initialized, then the governance fingerprint is tampered (simulating artifact drift). SDD detects the mismatch before the crew runs.

```bash
uv run --extra examplescrewai python examples/crewai/demo_spec_drift.py
```

Expected output: `DRIFT_DETECTED` with expected vs found fingerprint diff.

---

## Security — Governance Enforcement & Drift Regression

**What it shows:** Seven enforcement mechanism demos (unauthorized skill, token budget breach, session drift scoring, artifact missing/corrupt, reflection cap, telemetry enforcement, handshake failure) plus a deterministic drift accuracy battery for regression testing across features.

```bash
# Run all enforcement demos
for demo in examples/security/demo_*.py; do
    echo "=== $demo ===" && uv run python "$demo"
done

# Drift accuracy battery (before/after a feature)
uv run python examples/security/drift_battery.py --label "before-my-feature"
# ... implement feature, providence governance compile ...
uv run python examples/security/drift_battery.py --label "after-my-feature"
```

See [examples/security/README.md](security/README.md) for full documentation.

---

## Notes

- All demos exit with code `0` — the block/detection is the expected, correct behavior.
- Demos read from `.providence/` in the repo root. Run them from the repo root directory.
- Optional framework extras are defined in `pyproject.toml` under `[project.optional-dependencies]`.
- `examples/security/drift_battery_snapshot.json` is local state — do not commit it.
