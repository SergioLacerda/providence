# Compatibility Matrix — Providence

**Status:** Version 0.1.0+ (all packages synchronized via git tag)

---

## Supported Python Versions

| Version | Status | Support Level |
|---------|--------|---------------|
| 3.10    | ✅     | Stable (tested in CI) |
| 3.11    | ✅     | Stable (tested in CI) |
| 3.12    | ✅     | Stable (tested in CI) |
| 3.13    | 🟡     | Experimental (tested, allow-fail in CI) |
| 3.9     | ❌     | Unsupported (requires ≥3.10) |

**Policy:** We maintain support for the last 3 stable Python releases + 1 experimental (beta/RC).

---

## Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (Ubuntu) | ✅ | Primary testing target; CI matrix: Ubuntu 20.04+ |
| Windows | ✅ | Tested in CI matrix; use PowerShell or `bash` for scripts |
| macOS | ⚠️  | Untested; likely compatible but not in CI matrix |

**Policy:** Linux and Windows are the official supported platforms. macOS support is best-effort.

---

## Package Interdependencies

```
providence-cli
  └─ providence-wizard
      └─ providence-integration
          ├─ providence-runtime
          │   └─ providence-core
          └─ sdd-compiler
              └─ providence-core

providence-telemetry
  └─ providence-runtime
      └─ providence-core
```

**Installation:**

- **End-users (official channel):** download the `dist/` wheelhouse from a
  tagged [GitHub Release](https://github.com/SergioLacerda/providence/releases)
  and install with `pip install --no-index --find-links <dist-dir> providence-cli`.
  This exact flow is verified on `windows-latest` and `ubuntu-latest` by
  `.github/workflows/release.yml` before a release is published.
- **End-users (source/development install):** `uv tool install
  "git+https://github.com/SergioLacerda/providence#subdirectory=packages/interfaces/providence_cli"`
  tracks branch code rather than a released version.
- **Developers:** `uv sync` in monorepo root (all packages in editable mode)

There is no published `providence` package on PyPI; do not reference `pip
install providence` until PyPI publishing is implemented and proven in CI.

---

## Version Scheme & Semver

**Versioning Strategy:** Single version number for all packages.

- All 9 workspace packages release together with the same version (e.g., `0.2.0`)
- Version is derived from git tags: `v0.2.0` → all packages built at `0.2.0`
- Each package resolves its own version directly from the tag via `hatch-vcs`
  (`[tool.hatch.version] source = "vcs"`) — there is no separate sync step;
  the release workflow verifies every built wheel's filename matches the tag

### What Counts as Each Type of Change

#### MAJOR (X.0.0)

- **CLI:** Removing a command, renaming a flag, changing command behavior
- **API:** Removing a public function, changing function signature, removing a module
- **Schema:** Removing fields from governance artifacts, changing event schema format
- **Mandates:** Adding new mandatory compliance requirements

Examples:

- `providence governance compile` → `sdd compile` (command rename)
- Removing `--verbose` flag without replacement
- Changing `RuntimeEvent` schema (removing fields)

#### MINOR (1.X.0)

- **CLI:** Adding a new command, adding optional flags, new output format (backward-compatible)
- **API:** Adding new functions, adding optional parameters, new modules
- **Schema:** Adding optional fields (default to `None` or empty)
- **Features:** New governance features, new diagnostics

Examples:

- Adding `providence ask` command
- Adding `--format json` output option
- Adding new `economy.*` event types

#### PATCH (1.0.X)

- **Fixes:** Bug fixes, security patches, performance improvements
- **Docs:** Documentation updates, comment clarifications
- **Tests:** Test additions (not behavior changes)

Examples:

- Fixing drift detection bug
- Improving JSONL parsing performance
- Updating README

---

## Deprecation Policy

When a feature must be removed, follow this process:

1. **Deprecation warning** (minor version N)
   - Add warning message: "This command is deprecated. Use `foo` instead. (Deprecated in v1.5.0)"
   - Keep feature fully functional
   - Document in `CHANGELOG.md` under `Deprecated` section

2. **Removal** (major version N+1)
   - Remove the feature entirely
   - Document in `CHANGELOG.md` under `Removed` section
   - Include migration instructions

**Minimum deprecation window:** 1 minor version (at least ~1 month before removal)

Example:

- v1.5.0: Deprecate `providence governance --old-flag` with warning message
- v1.6.0, v1.7.0, etc.: Flag still works with warning
- v2.0.0: Remove `--old-flag` entirely

---

## Dependency Compatibility

### Python Core Dependencies

Ranges are intentional (exact versions pinned in `uv.lock`):

| Dependency | Min | Max | Reason |
|------------|-----|-----|--------|
| `PyYAML` | 6.0 | — | YAML parsing; stable API |
| `typer` | 0.9.0 | — | CLI framework; stable API |
| `rich` | 13.0.0 | — | Terminal formatting; stable API |
| `pytest` | 8.0.0 | — | Testing framework |
| `ruff` | 0.3.0 | — | Linting; rapid development cycle |

**Policy:** Keep dependencies at reasonable minimums to reduce installation conflicts. Update in `pyproject.toml`, run `uv lock`, commit both.

---

## Release Compatibility Checklist

Before releasing version X.Y.Z, verify:

- [ ] All sub-packages pass tests on supported Python versions (3.10, 3.11, 3.12)
- [ ] No breaking changes without version bump to major (X.0.0)
- [ ] `CHANGELOG.md` updated with [X.Y.Z] entry
- [ ] All package versions synchronized to X.Y.Z
- [ ] Release workflow validates version sync before build
- [ ] No unresolved security advisories (bandit + pip-audit pass)
- [ ] Container scanning passes (Trivy)

---

## Multi-Version Regression Testing

Future enhancement (Phase 5.3): Add CI matrix to test:

- Latest Python versions (3.10, 3.11, 3.12, 3.13)
- Latest + previous minor versions (e.g., if 3.12.5 is latest, test 3.12.0, 3.12.5)
- Artifact compatibility across versions (compile in 3.10, run in 3.12, etc.)

---

## Reporting Compatibility Issues

Found a compatibility problem?

1. Check [GitHub Issues](https://github.com/SergioLacerda/providence/issues) for existing report
2. If new: open issue with:
   - Python version
   - Platform (Linux/Windows/macOS)
   - Steps to reproduce
   - Full error traceback

---

## Links

- [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) — RFC process for breaking changes
