#!/usr/bin/env bash
set -u
cd /home/usuario/fulkro
source .venv/bin/activate
export PYTHONPATH=/home/usuario/fulkro

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
