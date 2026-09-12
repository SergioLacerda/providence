package tests

import (
	"os"
	"path/filepath"
	"testing"

	"sdd-compile/internal/govcompiler"
)

// sddCompiledDir returns the path to the actual .providence/compiled directory,
// navigating up from the tests package location.
func sddCompiledDir(t *testing.T) string {
	t.Helper()
	// Walk up from package dir: tools/sdd-compile/tests → ../../../ is repo root
	dir, err := filepath.Abs("../../../.providence/compiled")
	if err != nil {
		t.Fatalf("resolve .providence/compiled: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, "governance-core.json")); err != nil {
		t.Skipf(".providence/compiled/governance-core.json not found (%v) — skipping integration test", err)
	}
	return dir
}

func TestGovCompilerCompile(t *testing.T) {
	src := sddCompiledDir(t)
	out := t.TempDir()

	compiler := govcompiler.New(src)
	result, err := compiler.Compile(out)
	if err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	for _, path := range []string{
		result.CoreMsgpackFile,
		result.ClientMsgpackFile,
		result.CoreMetadata,
		result.ClientMetadata,
	} {
		if _, err := os.Stat(path); err != nil {
			t.Errorf("expected output file missing: %s", path)
		}
	}
}

func TestGovCompilerFingerprintsPresent(t *testing.T) {
	src := sddCompiledDir(t)
	out := t.TempDir()

	result, err := govcompiler.New(src).Compile(out)
	if err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	if len(result.CoreFingerprint) != 64 {
		t.Errorf("core fingerprint should be 64 hex chars, got %d: %q", len(result.CoreFingerprint), result.CoreFingerprint)
	}
	if len(result.ClientFingerprint) != 64 {
		t.Errorf("client fingerprint should be 64 hex chars, got %d: %q", len(result.ClientFingerprint), result.ClientFingerprint)
	}
	if result.CoreFingerprint == result.ClientFingerprint {
		t.Error("core and client fingerprints should differ")
	}
}

func TestGovCompilerItemCountsPositive(t *testing.T) {
	src := sddCompiledDir(t)
	out := t.TempDir()

	result, err := govcompiler.New(src).Compile(out)
	if err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	if result.CoreItemCount <= 0 {
		t.Errorf("expected positive core item count, got %d", result.CoreItemCount)
	}
}

func TestGovCompilerMsgpackNoMagicHeader(t *testing.T) {
	src := sddCompiledDir(t)
	out := t.TempDir()

	result, err := govcompiler.New(src).Compile(out)
	if err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	data, err := os.ReadFile(result.CoreMsgpackFile)
	if err != nil {
		t.Fatalf("read msgpack: %v", err)
	}
	if len(data) < 4 {
		t.Fatal("msgpack output too short")
	}
	// Verify no known magic headers (msgpack-rpc: 0x92, custom: 0x89abcdef patterns etc.)
	// Plain msgpack map with fixmap starts with 0x8x or 0xde/0xdf.
	// Known forbidden magic: MsgPack-RPC 0x92, or custom 4-byte headers.
	forbidden := [][]byte{
		{0x89, 0xAB, 0xCD, 0xEF},
		{0x92, 0x00, 0x00, 0x00},
	}
	for _, magic := range forbidden {
		if data[0] == magic[0] && data[1] == magic[1] && data[2] == magic[2] && data[3] == magic[3] {
			t.Errorf("msgpack output starts with forbidden magic header %x", magic)
		}
	}
}

func TestGovCompilerValidation(t *testing.T) {
	src := sddCompiledDir(t)
	out := t.TempDir()

	compiler := govcompiler.New(src)
	if _, err := compiler.Compile(out); err != nil {
		t.Fatalf("Compile() failed: %v", err)
	}

	vr := compiler.ValidateCompilationDetailed(out)
	if !vr.OK {
		t.Errorf("validation failed: %v", vr.Errors)
	}
	if len(vr.Checks) == 0 {
		t.Error("expected validation checks to be populated")
	}
}

func TestGovCompilerValidationFailsOnMissingDir(t *testing.T) {
	compiler := govcompiler.New("/nonexistent")
	vr := compiler.ValidateCompilationDetailed("/nonexistent-output")
	if vr.OK {
		t.Error("expected validation to fail for nonexistent output dir")
	}
}
