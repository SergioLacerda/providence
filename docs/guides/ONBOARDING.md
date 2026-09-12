# Onboarding Guide (Local Development)

Set up a local development environment for contributing to the Providence codebase itself.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (required)

## Deploy local + build

```bash
# Clone and bootstrap the workspace (creates .venv, installs all packages + dev/test deps)
git clone https://github.com/SergioLacerda/providence.git
cd providence
uv run providence setup run
```

`uv run` resolves the workspace environment from `pyproject.toml` on demand — no
pre-existing `.venv` or manual activation required, and it works the same on Linux, macOS,
and Windows.

`uv run providence setup run`:

- creates `.venv` if it doesn't exist
- installs all workspace packages (core, telemetry, runtime, compiler, integration, wizard,
  cli) + dev/test dependencies from root `pyproject.toml`
- validates imports and CLI responsiveness

> Equivalent via Make (used by CI/automation): `make install`, followed by
> `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows) if you prefer an
> activated shell.

<!-- -->

> [!WARNING]
> If you also have `sdd` installed globally as the `providence-cli` tool (e.g. via
> `uv tool install`, as an adopter in another project), that global binary may appear
> earlier in your `PATH` and
> shadow this repository's version (`.venv/bin/providence` or `.venv/Scripts/providence.exe`). When
> developing in this repo, always prefer `uv run sdd <command>` (uses this workspace's
> `.venv` regardless of `PATH`), or run `uv tool uninstall providence-cli` before starting.

## Quick bootstrap

```bash
# Bootstrap local governance runtime: profile + governance generate + skills + runtime validate
uv run providence init --default
```

`providence init --default` is equivalent to
`providence init --type client --name local-dev --language en --force` and
runs the full chain:

1. Workspace profile (`.providence/profile`)
2. `providence governance generate --full-bootstrap`
3. `providence skills --full-bootstrap --regenerate-seeds`
4. `providence runtime status --force`

```bash
# Verify everything is healthy
uv run providence runtime status --force
uv run providence governance validate
```

## Step-by-step (manual / customized)

If you need finer control over individual steps (e.g. re-running just governance
generation, or skipping skills regeneration):

```bash
uv run providence init --type client --name local-dev --force
make governance-bootstrap   # compile + generate + sign artifacts (= providence governance generate --full-bootstrap)
uv run providence skills --full-bootstrap --regenerate-seeds
uv run providence runtime status --force
uv run providence governance validate
```

CLI reference: [`docs/spec/reference/commands/cli.md`](../spec/reference/commands/cli.md)
