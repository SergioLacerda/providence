#!/bin/bash
set -e

# Sovereign Entrypoint: Governance-Aware Boot Sequence
# Mandate: P003 (Mandatory Human Sign-off)

echo "🛡️ Starting Providence Sovereign Container..."

# 1. Keyring Pre-flight
TRUST_DIR="/app/.providence/trust"
KEYRING="$TRUST_DIR/trusted-keys.json"

if [ ! -f "$KEYRING" ]; then
    echo "⚠️ WARNING: Trusted keyring not found at $KEYRING"
    echo "   Container will enter SAFETY-MODE (Diagnostics Only)."
    export SDD_GOVERNANCE_MODE="safety"
else
    # 2. Run Governance Audit (Hardened Gate)
    echo "🔍 Performing Security Audit (P003)..."
    if providence governance audit --verbose; then
        echo "✅ Audit passed. Governance is hardened."
        export SDD_GOVERNANCE_MODE="hardened"
    else
        echo "❌ CRITICAL: Governance audit failed!"
        echo "   Integrity breach or missing human signatures detected."
        echo "   Container will enter SAFETY-MODE (Diagnostics Only)."
        export SDD_GOVERNANCE_MODE="safety"
    fi
fi

# 3. Apply Safety-Mode Restrictions
if [ "$SDD_GOVERNANCE_MODE" == "safety" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚨 SAFETY-MODE ACTIVE"
    echo "   - Agent execution BLOCKED"
    echo "   - Diagnostic tools ENABLED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ "$#" -eq 0 ]; then
        set -- providence tools list
    fi
else
    if [ "$#" -eq 0 ]; then
        set -- make check
    fi
fi

# 4. Test isolation for container CI health checks
# When running `make check` inside the container, execute tests from a shadow
# copy of the repository so any `.providence` runtime/trust mutations stay in /tmp.
if [ "${1:-}" = "make" ] && [ "${2:-}" = "check" ]; then
    SHADOW_ROOT="/tmp/sdd-shadow-repo"
    rm -rf "$SHADOW_ROOT"
    mkdir -p "$SHADOW_ROOT"

    # Copy full repo tree (including tests and Makefile) to isolated location.
    cp -a /app/. "$SHADOW_ROOT/"

    # Replace the copied .venv with a symlink to the canonical /app/.venv.
    # The copied venv's pyvenv.cfg and Python wrapper may not activate correctly
    # from a different directory depth, causing editable-install .pth files to
    # be skipped and workspace packages to resolve as empty namespace packages.
    rm -rf "$SHADOW_ROOT/.venv"
    ln -s /app/.venv "$SHADOW_ROOT/.venv"

    # Ensure telemetry tests use their own tmp_path/workspace resolution.
    unset SDD_TELEMETRY_PATH || true
    unset SDD_COMPLIANCE_EVENTS_PATH || true
    unset SDD_WORKSPACE_ROOT || true

    # Do not force global workspace/event paths here; several tests rely on
    # per-test tmp_path resolution and explicit monkeypatching.
    export SDD_ALLOW_REPO_SDD_MUTATION=1

    # Run the check target from the isolated repository copy.
    set -- make -C "$SHADOW_ROOT" check
fi

exec /usr/bin/tini -- "$@"
