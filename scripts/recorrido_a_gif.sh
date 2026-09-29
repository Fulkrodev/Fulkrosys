#!/usr/bin/env bash
# Convierte la grabación de frontend/tests/capturas/grabar-recorrido.mjs en:
#   landing/assets/video/recorrido.webm  (web: VP9, lo reproduce cualquier navegador)
#   landing/assets/video/recorrido.mp4   (web: H.264, respaldo para Safari)
#   docs/assets/recorrido.gif            (README: sin cortinillas y 1,25x más rápido, paleta propia)
#
# Uso:  scripts/recorrido_a_gif.sh out/recorrido/recorrido.webm
set -euo pipefail

ENTRADA="${1:?uso: scripts/recorrido_a_gif.sh <grabacion.webm>}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
MP4="$RAIZ/landing/assets/video/recorrido.mp4"
WEBM="$RAIZ/landing/assets/video/recorrido.webm"
GIF="$RAIZ/docs/assets/recorrido.gif"
mkdir -p "$(dirname "$MP4")" "$(dirname "$GIF")"
PALETA="$(mktemp --suffix=.png)"
trap 'rm -f "$PALETA"' EXIT

# La grabación cubre cada carga con una cortinilla oscura. Aquí se recortan esos
# tramos (blackdetect) y de cada uno queda una transición de 0,2 s.
CORTES="$(ffmpeg -v info -i "$ENTRADA" -vf "blackdetect=d=0.3:pix_th=0.12:pic_th=0.97" \
  -an -f null - 2>&1 | grep -oE 'black_start:[0-9.]+ black_end:[0-9.]+' \
  | awk -F'[: ]' '{printf "%sbetween(t,%.2f,%.2f)", (NR>1?"+":""), $2+0.2, $4}')"
SIN_OSCUROS="select='not(${CORTES:-0})',setpts=N/FRAME_RATE/TB"

ffmpeg -v error -y -i "$ENTRADA" -an \
  -vf "fps=30,$SIN_OSCUROS,scale=1280:-2:flags=lanczos" \
  -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart "$MP4"

ffmpeg -v error -y -i "$ENTRADA" -an \
  -vf "fps=30,$SIN_OSCUROS,scale=1280:-2:flags=lanczos" \
  -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 -deadline good "$WEBM"

FILTRO="fps=30,$SIN_OSCUROS,setpts=PTS/1.25,fps=8,scale=800:-1:flags=lanczos"
ffmpeg -v error -y -i "$ENTRADA" -vf "$FILTRO,palettegen=max_colors=128:stats_mode=diff" "$PALETA"
ffmpeg -v error -y -i "$ENTRADA" -i "$PALETA" \
  -lavfi "$FILTRO [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" "$GIF"

ls -la "$WEBM" "$MP4" "$GIF"
