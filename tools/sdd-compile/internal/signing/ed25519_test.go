package signing

import (
	"bytes"
	"crypto/ed25519"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"
)

func writeKeyPair(t *testing.T, dir string) (privPath, pubPEM string) {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatalf("generate key: %v", err)
	}

	privBytes, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		t.Fatalf("marshal private key: %v", err)
	}
	privPEM := pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privBytes})
	privPath = filepath.Join(dir, "test.key")
	if err := os.WriteFile(privPath, privPEM, 0o600); err != nil {
		t.Fatalf("write private key: %v", err)
	}

	pubBytes, err := x509.MarshalPKIXPublicKey(pub)
	if err != nil {
		t.Fatalf("marshal public key: %v", err)
	}
	pubPEM = string(pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: pubBytes}))
	return privPath, pubPEM
}

func TestSignArtifactAndVerifySignatureRoundTrip(t *testing.T) {
	dir := t.TempDir()
	privPath, pubPEM := writeKeyPair(t, dir)

	artifactPath := filepath.Join(dir, "artifact.json")
	if err := os.WriteFile(artifactPath, []byte(`{"a":1}`), 0o644); err != nil {
		t.Fatalf("write artifact: %v", err)
	}

	sigPath, err := SignArtifact(artifactPath, "master", "test-01", privPath)
	if err != nil {
		t.Fatalf("SignArtifact: %v", err)
	}
	if sigPath != artifactPath+".sig" {
		t.Errorf("unexpected sig path: %s", sigPath)
	}

	sigBytes, err := os.ReadFile(sigPath)
	if err != nil {
		t.Fatalf("read sig file: %v", err)
	}
	if len(sigBytes) == 0 || sigBytes[len(sigBytes)-1] != '\n' {
		t.Fatal("signature manifest must end with a newline")
	}
	if !bytes.Contains(sigBytes, []byte("\n  \"algorithm\": \"ed25519\",")) {
		t.Fatal("signature manifest must use two-space indentation")
	}

	var manifest struct {
		KeyID       string `json:"key_id"`
		Profile     string `json:"profile"`
		PayloadHash string `json:"payload_hash"`
		Signature   string `json:"signature"`
	}
	if err := json.Unmarshal(sigBytes, &manifest); err != nil {
		t.Fatalf("parse manifest: %v", err)
	}
	if manifest.KeyID != "test-01" || manifest.Profile != "master" {
		t.Errorf("unexpected manifest fields: %+v", manifest)
	}

	valid, err := VerifySignature(pubPEM, []byte(manifest.PayloadHash), manifest.Signature)
	if err != nil {
		t.Fatalf("VerifySignature: %v", err)
	}
	if !valid {
		t.Error("expected signature to verify successfully")
	}
}

func TestVerifySignatureRejectsTamperedMessage(t *testing.T) {
	dir := t.TempDir()
	privPath, pubPEM := writeKeyPair(t, dir)

	artifactPath := filepath.Join(dir, "artifact.json")
	os.WriteFile(artifactPath, []byte(`{"a":1}`), 0o644)

	sigPath, err := SignArtifact(artifactPath, "master", "test-01", privPath)
	if err != nil {
		t.Fatalf("SignArtifact: %v", err)
	}
	sigBytes, _ := os.ReadFile(sigPath)
	var manifest struct {
		Signature string `json:"signature"`
	}
	json.Unmarshal(sigBytes, &manifest)

	valid, err := VerifySignature(pubPEM, []byte("tampered-hash"), manifest.Signature)
	if err != nil {
		t.Fatalf("VerifySignature: %v", err)
	}
	if valid {
		t.Error("expected tampered message to fail verification")
	}
}

func TestVerifySignatureInvalidBase64(t *testing.T) {
	_, pubPEM := writeKeyPair(t, t.TempDir())
	if _, err := VerifySignature(pubPEM, []byte("m"), "not-base64!!"); err == nil {
		t.Error("expected error for invalid base64 signature")
	}
}

func TestVerifySignatureInvalidPublicKeyPEM(t *testing.T) {
	if _, err := VerifySignature("not a pem", []byte("m"), base64.StdEncoding.EncodeToString([]byte("sig"))); err == nil {
		t.Error("expected error for invalid PEM public key")
	}
}

func TestSignArtifactMissingArtifact(t *testing.T) {
	dir := t.TempDir()
	privPath, _ := writeKeyPair(t, dir)
	if _, err := SignArtifact(filepath.Join(dir, "missing.json"), "master", "k", privPath); err == nil {
		t.Error("expected error for missing artifact file")
	}
}

func TestSignArtifactMissingKey(t *testing.T) {
	dir := t.TempDir()
	artifactPath := filepath.Join(dir, "artifact.json")
	os.WriteFile(artifactPath, []byte(`{}`), 0o644)
	if _, err := SignArtifact(artifactPath, "master", "k", filepath.Join(dir, "missing.key")); err == nil {
		t.Error("expected error for missing key file")
	}
}
