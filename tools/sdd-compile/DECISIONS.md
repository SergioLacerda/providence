# sdd-compile: Migration Decisions

This document records the rationale and resolved decisions behind the migration
of governance compilation from the Python `packages/core/sdd_compiler` package
to this Go binary (`tools/sdd-compile`).

## Why Go

The Python compiler's DSL parsing/validation and governance compilation were a
performance bottleneck on large mandate/guideline sets, and duplicated logic
already mirrored in the project's other Go-adjacent tooling ambitions. The
migration ports DSL validation, parsing, string pooling, compile state,
governance artifact compilation (JSON → msgpack), and Ed25519 signing to Go,
while keeping a thin Python bridge (`providence_core.utils.compiler_runner.CompilerRunner`)
so existing orchestration code does not need to shell out directly.

## Fingerprint determinism

The governance fingerprint is computed from source rules by the pipeline
builder, not derived from compiled artifact bytes. The Go binary does not
recompute fingerprints — it preserves whatever fingerprint is present in the
input JSON through to the compiled output. Signing is a separate concern: the
Ed25519 signature covers the SHA-256 hash of the artifact file bytes, computed
independently of the governance fingerprint.

## Signing without OpenSSL

The Python compiler shelled out to `openssl pkeyutl -sign -rawin`. The Go
binary uses `crypto/ed25519.Sign()` directly. Both implementations sign the
same payload — the hex-encoded SHA-256 hash of the artifact file, encoded as
UTF-8 bytes — so signatures produced by either implementation are protocol
compatible and verifiable by the same downstream consumers.

## `sign`/`verify` subcommands and runtime verification parity (2026-07-13)

The `internal/signing` Ed25519 backend originally only served the `compile`
pipeline's own signing step (`internal/govcompiler`). The Python CLI's
`providence governance sign` path and the runtime's signature verification
(`providence_runtime.signatures`) still shelled out to `openssl pkeyutl -sign` /
`openssl pkeyutl -verify` separately, leaving OpenSSL a required ambient
dependency for Windows standalone signing and verification.

`sign` and `verify` cobra commands were added (`cmd/sign.go`, `cmd/verify.go`)
so `CompilerRunner` (`providence_core.utils.compiler_runner`) can drive both from
Python without spawning `openssl`. `verify` reads its request
(`public_key_pem`, `message`, `signature_b64`) as JSON on stdin rather than
CLI flags, since a PEM public key does not fit safely into a single argv
entry on Windows. A malformed key or signature is reported as
`{"ok": true, "valid": false}` rather than a process failure, matching the
previous OpenSSL-backed contract where any verification problem resolved to
"signature invalid" rather than raising.

`providence governance keygen` (private/public key generation) still shells out to
OpenSSL; only signing and verification moved to the native backend, per the
residual scope in
`.analysis/pending/20260713-windows-standalone-native-signing-verification-residual.md`.

## msgpack number fidelity

Go's `encoding/json` decodes all JSON numbers into `interface{}` as `float64`
by default, which would corrupt integers (e.g. item counts, version numbers)
when re-encoded to msgpack. The Go compiler uses `json.Decoder.UseNumber()`
plus a recursive type normalizer to preserve the int/float distinction that
Python's `json.load` gives for free, ensuring msgpack output is byte-faithful
to what the Python compiler would have produced.

## Wizard dependency (SQ-002)

`packages/interfaces/providence_wizard` depended on `sdd-compiler` in its
`pyproject.toml` but never imported it directly from source. The dependency
was dropped once orchestration moved to `CompilerRunner`/the Go binary,
rather than keeping it as a defensive no-op dependency.

## Debug and maintenance tooling (SQ-003)

`tools/debug/debug_msgpack.py` was the only maintenance tool with real
compiler logic (it invoked `GovernanceCompiler.compile()` directly); it was
ported to `providence_core.utils.compiler_runner.CompilerRunner`. The remaining
flagged tools (`run-all-tests.py`, `update-golden-snapshots.py`,
`sync_versions.py`, `validate_cycles.py`, `validate_imports.py`) only listed
`sdd_compiler` as a path/prefix entry in static lists (sys.path bootstrap,
test layer registry, version sync targets, import-cycle/layer prefixes) — those
entries were simply removed rather than ported, since there was no compiler
logic to bridge.

## Deletion

`packages/core/sdd_compiler/` was deleted only after a full-repo grep confirmed
zero active `sdd_compiler.*` imports remained (outside a docstring mention in
`compiler_runner.py` and an unrelated fixture string in a telemetry test), and
`make ci-pr` was confirmed green against the Go-backed pipeline.
