#!/usr/bin/env bash
# Dev helper: poll backend :8000 + frontend :3000 until both respond.
for i in $(seq 1 40); do
  B=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
  F=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)
  echo "intento $i · backend=$B · frontend=$F"
  if [ "$B" = "200" ] && { [ "$F" = "200" ] || [ "$F" = "307" ] || [ "$F" = "302" ]; }; then
    echo "AMBOS LISTOS"
    exit 0
  fi
  sleep 3
done
echo "TIMEOUT"
exit 1
