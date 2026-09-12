import yaml

from providence_integration.engine.integration_engine import IntegrationEngine, Report
from providence_integration.engine.step_executor import StepResult


def make_spec_file(tmp_path, steps=None, context=None):
    spec = {}
    if context:
        spec["context"] = context
    if steps is not None:
        spec["steps"] = steps
    else:
        spec["steps"] = [
            {"id": "s1", "type": "noop", "inputs": {}, "asserts": []},
            {"id": "s2", "type": "noop", "inputs": {}, "asserts": []},
        ]
    file = tmp_path / "spec.yaml"
    file.write_text(yaml.dump(spec), encoding="utf-8")
    return file


def test_report_score_and_pretty():
    steps = [StepResult("a", True, ["ok"]), StepResult("b", False, ["fail"])]
    report = Report(steps)
    assert report.score() == 50
    out = report.pretty()
    assert "SDD Doctor Report" in out
    assert "a ✅ ok" in out
    assert "b ❌ fail" in out
    assert "Score: 50/100" in out


def test_integration_engine_run_success(monkeypatch, tmp_path):
    # Patch StepExecutor to always succeed
    class DummyExecutor:
        def execute(self, step, context):
            return StepResult(step.id or "x", True, ["ok"])

    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.StepExecutor",
        lambda: DummyExecutor(),
    )
    spec_file = make_spec_file(tmp_path)
    engine = IntegrationEngine(str(spec_file))
    report = engine.run()
    assert isinstance(report, Report)
    assert report.score() == 100
    assert all(s.success for s in report.steps)


def test_integration_engine_run_with_context_override(monkeypatch, tmp_path):
    class DummyContext:
        def __init__(self, spec, spec_dir):
            self.data = {"foo": spec.get("context", {}).get("foo")}

        def cleanup(self):
            pass

        @staticmethod
        def from_spec(spec, spec_dir):
            return DummyContext(spec, spec_dir)

    class DummyExecutor:
        def execute(self, step, context):
            return StepResult(step.id or "x", True, [str(context.data.get("foo"))])

    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.ExecutionContext",
        DummyContext,
    )
    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.StepExecutor",
        lambda: DummyExecutor(),
    )
    spec_file = make_spec_file(tmp_path, context={"foo": "bar"})
    engine = IntegrationEngine(str(spec_file), context_overrides={"foo": "baz"})
    report = engine.run()
    # Context override should take precedence
    assert any("baz" in s.details for s in report.steps)


def test_integration_engine_run_cleanup(monkeypatch, tmp_path):
    cleanup_called = {}

    class DummyContext:
        def __init__(self, spec, spec_dir):
            self.data = {}

        def cleanup(self):
            cleanup_called["yes"] = True

        @staticmethod
        def from_spec(spec, spec_dir):
            return DummyContext(spec, spec_dir)

    class DummyExecutor:
        def execute(self, step, context):
            return StepResult("x", True, ["ok"])

    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.ExecutionContext",
        DummyContext,
    )
    monkeypatch.setattr(
        "providence_integration.engine.integration_engine.StepExecutor",
        lambda: DummyExecutor(),
    )
    spec_file = make_spec_file(tmp_path)
    engine = IntegrationEngine(str(spec_file))
    engine.run()
    assert cleanup_called.get("yes")
