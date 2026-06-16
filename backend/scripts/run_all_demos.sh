#!/usr/bin/env bash
set -u
# W9-2: repo-root relativo al script (backend/scripts/ → ../..), no hardcode WSL.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
source .venv/bin/activate
export PYTHONPATH="$REPO_ROOT"

DEMOS=(
  demo_s7_paso7_full.py
  demo_s8_paso1_templates.py
  demo_s8_paso2_retainer.py
  demo_s8_paso3_client_portal.py
  demo_s8_paso4_lifecycle.py
  demo_s8_paso5_conformity.py
  demo_s8_paso6_pricing.py
  demo_s8_paso8_e2e_year_dataforma.py
)

TOTAL_PASS=0
TOTAL_FAIL=0

for demo in "${DEMOS[@]}"; do
  echo "===================================="
  echo "=== $demo ==="
  echo "===================================="
  out=$(python "backend/scripts/$demo" 2>&1)
  rc=$?
  echo "$out" | tail -6
  if [ $rc -eq 0 ]; then
    TOTAL_PASS=$((TOTAL_PASS+1))
  else
    TOTAL_FAIL=$((TOTAL_FAIL+1))
    echo "FAILED (rc=$rc)"
  fi
done

echo ""
echo "===================================="
echo "TOTAL DEMOS: pass=$TOTAL_PASS fail=$TOTAL_FAIL"
echo "===================================="
