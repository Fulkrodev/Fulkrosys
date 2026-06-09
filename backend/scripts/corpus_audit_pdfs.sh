#!/usr/bin/env bash
# Sub-lote 1.B.5.2 PASO 1 · audit integridad PDFs en _incoming/corpus_cache/
# NOTE: sin pipefail · pdftotext | head genera SIGPIPE benigno.
set -u

ROOT="${1:-_incoming/corpus_cache/manual}"
TOTAL=0
TOTAL_PAGES=0
FAILED=0

printf "%-70s | %4s | %9s | %5s | %s\n" "filename" "pp" "bytes" "chars" "status"
printf -- '-%.0s' {1..110}; echo

for pdf in $(find "$ROOT" -name "*.pdf" | sort); do
    TOTAL=$((TOTAL+1))
    size=$(stat -c%s "$pdf")
    pages=$(pdfinfo "$pdf" 2>/dev/null | awk '/^Pages:/ {print $2}')
    pages=${pages:-0}
    text=$(pdftotext "$pdf" - 2>/dev/null | head -c 500)
    text_len=${#text}
    basename=$(basename "$pdf")

    flag="OK"
    if [ "$pages" -lt 1 ]; then flag="FAIL-PAGES"; FAILED=$((FAILED+1)); fi
    if [ "$size" -lt 51200 ]; then flag="FAIL-SIZE"; FAILED=$((FAILED+1)); fi
    if [ "$text_len" -lt 100 ]; then flag="FAIL-TEXT"; FAILED=$((FAILED+1)); fi

    TOTAL_PAGES=$((TOTAL_PAGES+pages))
    printf "%-70s | %4s | %9d | %5d | %s\n" "$basename" "$pages" "$size" "$text_len" "$flag"
done

echo
echo "TOTAL: $TOTAL PDFs · $TOTAL_PAGES pages · $FAILED failed"
