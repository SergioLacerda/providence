#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Governance compliance validator for Providence Architecture."""

import argparse
import base64
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from tools.lib.providence_env import detect_repo_root, get_sdd_paths
except ImportError:
    # Fallback if lib is not found (unlikely in standard structure)
    def detect_repo_root() -> Path:
        return Path.cwd()

    def get_sdd_paths() -> dict[str, Path]:
        root = Path.cwd()
        gen = root / "generated"
        return {
            "root": root,
            "compiler_output": gen / "master" / "compiled",
            "wizard_runtime": gen / "client" / "compiled",
        }


try:
    from providence_core.utils.process import SafeProcessRunner
except ImportError:
    _fallback_root = Path(__file__).resolve().parents[2]
    _fallback_src = _fallback_root / "packages" / "core" / "providence_core" / "src"
    if str(_fallback_src) not in sys.path:
        sys.path.insert(0, str(_fallback_src))
    from providence_core.utils.process import SafeProcessRunner


class GovernanceComplianceValidator:
    """Validates governance file integrity and compliance rules."""

    GOVERNANCE_FILE = ".providence/source/governance-core.json"

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = Path(project_dir) if project_dir else detect_repo_root()
        providence_core_src = (
            self.project_dir / "packages" / "core" / "providence_core" / "src"
        )
        if str(providence_core_src) not in sys.path:
            sys.path.insert(0, str(providence_core_src))
        self.paths = get_sdd_paths()
        self.integrity_requested: bool = False

        # Canonical names (relative to project/repo root)
        self.SOURCE_GOVERNANCE = self.GOVERNANCE_FILE
        self.SIGNATURE_FILE = ".providence/source/.governance-signature.json"

        self.governance_file = self._resolve_governance_file()
        self.signature_file = self.project_dir / self.SIGNATURE_FILE

    def _resolve_governance_file(self) -> Path:
        """Resolve the governance file path (Source, Compiled, or Wizard Runtime)."""
        candidates = [
            self.project_dir / self.SOURCE_GOVERNANCE,
            self.paths.get("wizard_runtime", Path()) / "governance-core.json",
            self.paths.get("compiler_output", Path()) / "governance-core.json",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return Path(candidate)
        return Path(candidates[0])

    def _is_project_governance(self, data: dict[str, Any]) -> bool:
        """Return True when validating generated project governance under .providence/source."""
        required = {"seedlings", "authority", "policies", "phases"}
        return required.issubset(data.keys())

    def _is_compiled_governance(self, data: dict[str, Any]) -> bool:
        """Return True when validating compiled governance artifacts."""
        required = {"category", "version", "items", "fingerprint"}
        return required.issubset(data.keys())

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def _compute_fingerprint(self, data: dict[str, Any]) -> str:
        """Compute SHA-256 fingerprint of the governance data (excluding signature field)."""
        clean = {
            k: v for k, v in data.items() if k not in {"_signature", "fingerprint"}
        }
        serialized = json.dumps(clean, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def sign_governance(self) -> bool:
        """Sign the governance file and write a companion signature file."""
        if not self.governance_file.exists():
            return False
        try:
            with open(self.governance_file, encoding="utf-8") as f:
                data = json.load(f)
            fingerprint = self._compute_fingerprint(data)
            signature = {"fingerprint": fingerprint}
            self.signature_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.signature_file, "w", encoding="utf-8") as f:
                json.dump(signature, f, indent=2)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_integrity(self, data: dict[str, Any]) -> list[str]:
        """Return list of integrity violation messages (empty = OK)."""
        if not self.integrity_requested:
            return []

        # Target: the file being validated
        target_file = self.governance_file
        sig_file = target_file.with_suffix(target_file.suffix + ".sig")

        if not sig_file.exists():
            return [f"Integrity Failure: signature file missing ({sig_file.name})"]

        try:
            with open(sig_file, encoding="utf-8") as f:
                manifest = json.load(f)

            # 1. Verify payload hash matches what was signed
            actual_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
            signed_hash = manifest.get("payload_hash")
            if actual_hash != signed_hash:
                return [
                    "Integrity Failure: artifact content mismatch with signature (tampering detected)"
                ]

            # 2. Verify Ed25519 signature using openssl
            # We need the public key. We look in .providence/trust/
            key_id = manifest.get("key_id", "unknown")
            pub_key = self.project_dir / ".providence" / "trust" / f"{key_id}.pub.pem"

            if not pub_key.exists():
                return [
                    f"Integrity Failure: public key for '{key_id}' not found in .providence/trust/"
                ]

            # Use openssl pkeyutl to verify (World Class standard)
            # The message signed was the payload_hash string
            # Since the signature is in a JSON manifest, we need to extract it to a temp file
            with tempfile.TemporaryDirectory() as tmpdir:
                sig_bin = Path(tmpdir) / "sig.bin"
                sig_bin.write_bytes(base64.b64decode(manifest.get("signature", "")))

                verify_cmd = [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(pub_key),
                    "-rawin",
                    "-digest",
                    "sha256",
                    "-sigfile",
                    str(sig_bin),
                ]
                proc = SafeProcessRunner().run(
                    verify_cmd,
                    input_data=actual_hash.encode("utf-8"),
                    capture_output=True,
                )

                if proc.returncode != 0:
                    return [
                        f"Integrity Failure: Ed25519 signature verification failed for key '{key_id}'"
                    ]

        except Exception as e:
            return [f"Integrity Failure: {type(e).__name__} - {e}"]

        return []

    def _check_structure(self, data: dict[str, Any]) -> list[str]:
        """Check required top-level fields."""
        violations = []
        required = ["seedlings", "authority", "policies", "phases"]
        for field in required:
            if field not in data:
                violations.append(f"Missing required field: {field}")
        return violations

    def _check_compiled_structure(self, data: dict[str, Any]) -> list[str]:
        """Check required fields for compiled governance artifacts."""
        violations = []
        required = ["category", "version", "items", "fingerprint"]
        for field in required:
            if field not in data:
                violations.append(f"Missing required compiled field: {field}")
        if data.get("category") != "CORE":
            violations.append("Compiled governance category must be 'CORE'")
        if not isinstance(data.get("items", []), list):
            violations.append("Compiled governance items must be a list")
        return violations

    def _check_policies(self, data: dict[str, Any]) -> list[str]:
        """Check policies section."""
        violations = []
        policies = data.get("policies", {})
        enforcement = policies.get("enforcement", "")
        valid_levels = {"strict", "standard", "permissive"}
        if enforcement.lower() not in valid_levels:
            violations.append(
                f"Invalid enforcement level: '{enforcement}' (must be one of {valid_levels})"
            )
        return violations

    def validate_all(self) -> tuple[bool, dict[str, Any]]:
        """Run all validation checks.

        Returns:
            (is_compliant, results_dict) where results_dict has key 'violations'.
        """
        if not self.governance_file.exists():
            return False, {
                "violations": [f"Governance file not found: {self.governance_file}"]
            }

        try:
            with open(self.governance_file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, {"violations": [f"Invalid JSON in governance file: {e}"]}

        violations: list[str] = []
        if self._is_project_governance(data):
            violations.extend(self._check_structure(data))
            violations.extend(self._check_policies(data))
        elif self._is_compiled_governance(data):
            violations.extend(self._check_compiled_structure(data))
        else:
            violations.append("Unrecognized governance format")
        violations.extend(self._check_integrity(data))

        is_compliant = len(violations) == 0
        return is_compliant, {
            "violations": violations,
            "governance_file": str(self.governance_file),
        }

    def get_mandatory_fix_steps(self, results: dict[str, Any]) -> list[str]:
        """Return human-readable fix steps for each violation."""
        steps = []
        for v in results.get("violations", []):
            if "Missing required field" in v:
                steps.append(f"Add the missing field to {self.GOVERNANCE_FILE}")
            elif "Missing required compiled field" in v:
                steps.append(
                    "Regenerate compiled governance artifacts from the current spec"
                )
            elif "enforcement level" in v:
                steps.append(
                    "Set policies.enforcement to 'strict', 'standard', or 'permissive'"
                )
            elif "Integrity Failure" in v:
                if str(self.governance_file).endswith(
                    "governance-core.json"
                ) and "/compiled/" in str(self.governance_file):
                    steps.append(
                        "Regenerate compiled governance artifacts to refresh the embedded fingerprint"
                    )
                else:
                    steps.append(
                        "Re-sign the governance file: validator.sign_governance()"
                    )
            else:
                steps.append(f"Fix violation: {v}")
        return steps

    def get_enforcement_level(self) -> tuple[str, str]:
        """Return governance enforcement level and context message."""
        valid_levels = {"strict", "standard", "permissive"}

        if not self.governance_file.exists():
            return "UNKNOWN", f"Governance file not found: {self.governance_file}"

        try:
            with open(self.governance_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return "UNKNOWN", f"Could not read governance file: {e}"

        if self._is_project_governance(data):
            enforcement = str(
                data.get("policies", {}).get("enforcement", "permissive")
            ).lower()
            if enforcement not in valid_levels:
                return (
                    "UNKNOWN",
                    f"Invalid enforcement level in governance file: {enforcement}",
                )
            return enforcement.upper(), f"Source: {self.governance_file}"

        if self._is_compiled_governance(data):
            # Compiled artifacts do not carry full policy metadata.
            # Default to PERMISSIVE for reporting compatibility.
            return (
                "PERMISSIVE",
                f"Source: {self.governance_file} (compiled artifact default)",
            )

        return "UNKNOWN", f"Unrecognized governance format: {self.governance_file}"


def main(argv: list[str] | None = None) -> int:
    """Run governance validation CLI."""
    parser = argparse.ArgumentParser(
        description="Validate governance compliance and integrity"
    )
    parser.add_argument(
        "project_dir", nargs="?", default=".", help="Project directory to validate"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Run compliance verification"
    )
    parser.add_argument(
        "--check-integrity", action="store_true", help="Validate governance integrity"
    )
    parser.add_argument(
        "--fix-steps",
        action="store_true",
        help="Print recommended fix steps on failure",
    )
    parser.add_argument(
        "--sign", action="store_true", help="Create or refresh governance signature"
    )
    parser.add_argument(
        "--enforcement-check",
        action="store_true",
        help="Print current enforcement level",
    )

    args = parser.parse_args(argv)

    validator = GovernanceComplianceValidator(Path(args.project_dir))
    validator.integrity_requested = args.check_integrity

    if args.sign:
        ok = validator.sign_governance()
        if ok:
            print(f"OK: Governance signed: {validator.signature_file}")
            return 0
        print(f"ERROR: Could not sign governance file: {validator.governance_file}")
        return 1

    if args.enforcement_check:
        level, context = validator.get_enforcement_level()
        print(f"Enforcement level: {level}")
        print(context)
        return 0 if level in {"STRICT", "STANDARD", "PERMISSIVE"} else 1

    ok, results = validator.validate_all()
    if ok:
        print(f"OK: Governance is compliant: {results['governance_file']}")
        return 0

    print("ERROR: Governance violations found:")
    for v in results["violations"]:
        print(f"  - {v}")
    if args.fix_steps:
        for step in validator.get_mandatory_fix_steps(results):
            print(f"  -> {step}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
