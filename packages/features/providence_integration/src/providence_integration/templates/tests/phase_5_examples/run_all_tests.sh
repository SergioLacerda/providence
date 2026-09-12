#!/bin/bash

# Phase 5: Run all functional tests for SDD framework
# Tests both INTEGRATION and EXECUTION flows

set -e

cd "$(dirname "$0")/.."  # Go to /tests/

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         🚀 PHASE 5: FUNCTIONAL TESTING (BOTH FLOWS)            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Run INTEGRATION flow test
echo "📋 Running INTEGRATION flow test..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 integration/phase_5_examples/test_integration_flow.py
INTEGRATION_RESULT=$?
echo ""

# Run EXECUTION flow test
echo "📋 Running EXECUTION flow test..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 integration/phase_5_examples/test_execution_flow.py
EXECUTION_RESULT=$?
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      📊 TEST SUMMARY                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

if [ $INTEGRATION_RESULT -eq 0 ]; then
    echo "✅ INTEGRATION Flow: PASS"
else
    echo "❌ INTEGRATION Flow: FAIL"
fi

if [ $EXECUTION_RESULT -eq 0 ]; then
    echo "✅ EXECUTION Flow: PASS"
else
    echo "❌ EXECUTION Flow: FAIL"
fi

echo ""

# Overall result
if [ $INTEGRATION_RESULT -eq 0 ] && [ $EXECUTION_RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED - Framework is production-ready!"
    echo ""
    echo "Next: Phase 6 (Final Commit & Deployment)"
    exit 0
else
    echo "❌ SOME TESTS FAILED - Fix issues and re-run"
    echo ""
    echo "Run individual tests:"
    echo "  python3 integration/phase_5_examples/test_integration_flow.py"
    echo "  python3 integration/phase_5_examples/test_execution_flow.py"
    exit 1
fi
