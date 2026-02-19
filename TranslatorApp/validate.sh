#!/usr/bin/env bash
# validate.sh — Post-deploy validation for Linux / production
#
# Usage:
#   ./validate.sh                              # test localhost:5555
#   ./validate.sh https://kadeutsch.org        # test production
#   BASE_URL=https://kadeutsch.org ./validate.sh
#
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:5555}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== TranslatorApp Validation ==="
echo "Target: $BASE_URL"
echo ""

# ── Quick health check via curl (no pytest needed) ──
echo "--- Health Check ---"
HEALTH=$(curl -sf --max-time 10 "$BASE_URL/health" 2>&1) || {
    echo "FAIL: /health endpoint unreachable"
    echo "  Response: $HEALTH"
    exit 1
}

echo "  Response: $HEALTH"

# Parse JSON status (works with or without jq)
if command -v jq &>/dev/null; then
    STATUS=$(echo "$HEALTH" | jq -r '.status')
    DB=$(echo "$HEALTH" | jq -r '.db')
    VERSION=$(echo "$HEALTH" | jq -r '.version')
else
    STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    DB=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['db'])")
    VERSION=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])")
fi

echo "  Status:  $STATUS"
echo "  DB:      $DB"
echo "  Version: $VERSION"

if [ "$STATUS" != "ok" ] || [ "$DB" != "ok" ]; then
    echo ""
    echo "FAIL: Health check reports issues"
    exit 1
fi

echo "  Health check: PASS"
echo ""

# ── Full smoke tests (if pytest is available) ──
if command -v python3 &>/dev/null && python3 -c "import pytest" 2>/dev/null; then
    echo "--- Smoke Tests (pytest) ---"
    cd "$SCRIPT_DIR"
    BASE_URL="$BASE_URL" python3 -m pytest tests/test_smoke.py -v --tb=short
    RESULT=$?
else
    echo "--- Smoke Tests (curl fallback) ---"
    RESULT=0
    for path in "/" "/about" "/subtitles/" "/content/" "/glossary/" "/statistic/" "/pretranslate/"; do
        HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" --max-time 10 "$BASE_URL$path")
        if [ "$HTTP_CODE" = "200" ]; then
            echo "  GET $path → $HTTP_CODE ✓"
        else
            echo "  GET $path → $HTTP_CODE ✗"
            RESULT=1
        fi
    done
fi

echo ""
if [ "$RESULT" -eq 0 ]; then
    echo "=== ALL CHECKS PASSED ==="
else
    echo "=== SOME CHECKS FAILED ==="
fi

exit $RESULT
