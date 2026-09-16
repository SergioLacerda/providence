// Package signing provides Ed25519 artifact signing using Go's crypto/ed25519.
// This replaces Python's OpenSSL subprocess approach with native Go signing.
// The signing protocol is identical: SHA-256 hash of file bytes (hex-encoded),
// signed as raw bytes with Ed25519, base64-encoded result written to .sig manifest.
package signing

import (
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// SignArtifact signs artifactPath with the Ed25519 private key at privateKeyFile,
// writes a .sig manifest alongside the artifact, and returns the .sig path.
// Profile is "master" or "client"; keyID is the signing key identifier.
func SignArtifact(artifactPath, profile, keyID, privateKeyFile string) (string, error) {
	fileBytes, err := os.ReadFile(artifactPath)
	if err != nil {
		return "", fmt.Errorf("read artifact: %w", err)
	}

	hash := sha256.Sum256(fileBytes)
	payloadHash := hex.EncodeToString(hash[:])

	privKey, err := loadEd25519Key(privateKeyFile)
	if err != nil {
		return "", fmt.Errorf("load signing key: %w", err)
	}

	// Sign the hex-encoded hash bytes (matches Python: msg_path.write_bytes(payload_hash.encode("utf-8")))
	sig := ed25519.Sign(privKey, []byte(payloadHash))
	sigB64 := base64.StdEncoding.EncodeToString(sig)

	manifest := map[string]any{
		"schema_version": "1.0",
		"algorithm":      "ed25519",
		"key_id":         keyID,
		"artifact_name":  filepath.Base(artifactPath),
		"profile":        profile,
		"payload_hash":   payloadHash,
		"signature":      sigB64,
		"signed_at":      time.Now().UTC().Format(time.RFC3339),
	}

	sigPath := artifactPath + ".sig"
	b, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return "", fmt.Errorf("marshal signature manifest: %w", err)
	}
	b = append(b, '\n')
	if err := os.WriteFile(sigPath, b, 0o644); err != nil {
		return "", fmt.Errorf("write signature file: %w", err)
	}
	return sigPath, nil
}

// loadEd25519Key reads a PEM-encoded Ed25519 private key (PKCS8 or raw).
func loadEd25519Key(path string) (ed25519.PrivateKey, error) {
	pemBytes, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read key file: %w", err)
	}
	block, _ := pem.Decode(pemBytes)
	if block == nil {
		return nil, fmt.Errorf("no PEM block found in %s", path)
	}
	key, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("parse private key: %w", err)
	}
	ed, ok := key.(ed25519.PrivateKey)
	if !ok {
		return nil, fmt.Errorf("key is not Ed25519 (got %T)", key)
	}
	return ed, nil
}

// VerifySignature verifies an Ed25519 signature over message using a PEM-encoded
// (SPKI/PKIX) public key. It matches the OpenSSL `pkeyutl -verify` contract this
// package replaces: message is the raw bytes that were signed (the UTF-8 encoded
// hex payload hash), signatureB64 is the base64-encoded raw signature.
func VerifySignature(publicKeyPEM string, message []byte, signatureB64 string) (bool, error) {
	sig, err := base64.StdEncoding.DecodeString(signatureB64)
	if err != nil {
		return false, fmt.Errorf("decode signature: %w", err)
	}
	pub, err := loadEd25519PublicKey([]byte(publicKeyPEM))
	if err != nil {
		return false, fmt.Errorf("load public key: %w", err)
	}
	return ed25519.Verify(pub, message, sig), nil
}

// loadEd25519PublicKey reads a PEM-encoded Ed25519 public key (PKIX/SPKI).
func loadEd25519PublicKey(pemBytes []byte) (ed25519.PublicKey, error) {
	block, _ := pem.Decode(pemBytes)
	if block == nil {
		return nil, fmt.Errorf("no PEM block found")
	}
	key, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("parse public key: %w", err)
	}
	pub, ok := key.(ed25519.PublicKey)
	if !ok {
		return nil, fmt.Errorf("key is not Ed25519 (got %T)", key)
	}
	return pub, nil
}
