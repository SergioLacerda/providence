import shutil
import tempfile
from pathlib import Path

from providence_integration.engine.context import ExecutionContext


def make_spec(isolation=False, working_dir=None):
    ctx = {}
    if isolation:
        ctx["isolation"] = True
    if working_dir is not None:
        ctx["working_dir"] = working_dir
    return {"context": ctx}


def test_from_spec_isolation_creates_temp_dir():
    spec = make_spec(isolation=True)
    ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
    assert ctx.isolation_enabled is True
    assert ctx._temp_dir is not None
    assert ctx.working_dir.exists()
    # Cleanup
    ctx.cleanup()
    assert ctx._temp_dir is None


def test_from_spec_configured_working_dir(tmp_path):
    wd = tmp_path / "custom"
    spec = make_spec(working_dir=str(wd))
    ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
    assert ctx.working_dir == wd.resolve()
    assert wd.exists()
    ctx.cleanup()


def test_from_spec_default_cwd(monkeypatch):
    fake_cwd = Path(tempfile.mkdtemp())
    monkeypatch.setattr(Path, "cwd", staticmethod(lambda: fake_cwd))
    spec = make_spec()
    ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
    assert ctx.working_dir == fake_cwd
    ctx.cleanup()
    shutil.rmtree(fake_cwd)


def test_as_dict_and_data():
    spec = make_spec()
    ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
    d = ctx.as_dict()
    assert isinstance(d, dict)
    assert "working_dir" in d
    ctx.cleanup()


def test_cleanup_removes_temp_dir():
    spec = make_spec(isolation=True)
    ctx = ExecutionContext.from_spec(spec, Path("/tmp/spec"))
    temp_dir = ctx._temp_dir
    assert temp_dir.exists()
    ctx.cleanup()
    assert ctx._temp_dir is None
    assert not temp_dir.exists()
