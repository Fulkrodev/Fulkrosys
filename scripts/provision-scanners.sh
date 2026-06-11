#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# FULKRO · provision-scanners.sh · instala los escáneres del pentest autónomo M8
# ════════════════════════════════════════════════════════════════════════════
# Instala los binarios de los motores que SÍ son posibles en un VPS cloud, para
# que el autopilot (USE_MCP_REAL=true) ejecute el pentest entero de verdad.
#
# Correr DENTRO del contenedor backend (o en su build), como root:
#   bash scripts/provision-scanners.sh
# Luego poner USE_MCP_REAL=true en .env.prod y reiniciar el backend.
#
# FÍSICAMENTE IMPOSIBLE en un VPS (NO se instalan · el sistema los declina solo
# con su razón física vía mcp_client.scanner_capability · NUNCA finge resultado):
#   - wireless  (necesita adaptador WiFi en modo monitor · on-site)
#   - cracking  (hashcat · necesita GPU dedicada)
#   - mobile    (emulador/dispositivo Android/iOS · device farm)
#   - redteam   (C2 / adversary emulation · infra ofensiva + reglas firmadas)
#   - phishing  (dominios + infra de envío · ofensivo · consentimiento explícito)
# Estos son un tier de engagement dedicado, NO escaneo cloud automatizado.
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

OK=0; FAIL=0
ok()   { printf '  \033[32mOK\033[0m   %s\n' "$1"; OK=$((OK+1)); }
warn() { printf '  \033[33mSKIP\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
have() { command -v "$1" >/dev/null 2>&1; }

echo "== Provisionando escáneres M8 (motores posibles en VPS) =="

# ── apt (Debian/Ubuntu) · nmap + lynis ──────────────────────────────────────
if have apt-get; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq || true
  apt-get install -y -qq nmap lynis git curl ca-certificates jq >/dev/null 2>&1 \
    && ok "apt: nmap lynis git curl jq" || warn "apt install (¿permisos root?)"
else
  warn "apt-get no disponible · instala nmap/lynis/git/curl a mano"
fi

# ── nuclei (vulnscan · binario Go oficial) ──────────────────────────────────
if ! have nuclei; then
  NUC_VER="3.3.7"
  ARCH="$(uname -m)"; case "$ARCH" in x86_64) GA=amd64;; aarch64|arm64) GA=arm64;; *) GA=amd64;; esac
  curl -sSL "https://github.com/projectdiscovery/nuclei/releases/download/v${NUC_VER}/nuclei_${NUC_VER}_linux_${GA}.zip" -o /tmp/nuclei.zip 2>/dev/null \
    && (cd /tmp && unzip -oq nuclei.zip nuclei -d /usr/local/bin 2>/dev/null) \
    && chmod +x /usr/local/bin/nuclei 2>/dev/null \
    && nuclei -update-templates -silent >/dev/null 2>&1 || true
fi
have nuclei && ok "nuclei ($(nuclei -version 2>&1 | head -1))" || warn "nuclei no instalado"

# ── httpx (recon web · binario Go) ──────────────────────────────────────────
if ! have httpx; then
  HX_VER="1.6.9"; ARCH="$(uname -m)"; case "$ARCH" in x86_64) GA=amd64;; aarch64|arm64) GA=arm64;; *) GA=amd64;; esac
  curl -sSL "https://github.com/projectdiscovery/httpx/releases/download/v${HX_VER}/httpx_${HX_VER}_linux_${GA}.zip" -o /tmp/httpx.zip 2>/dev/null \
    && (cd /tmp && unzip -oq httpx.zip httpx -d /usr/local/bin 2>/dev/null) \
    && chmod +x /usr/local/bin/httpx 2>/dev/null || true
fi
have httpx && ok "httpx" || warn "httpx no instalado (opcional · recon web)"

# ── testssl.sh (webpentest · TLS) ───────────────────────────────────────────
if ! have testssl.sh; then
  git clone --depth 1 -q https://github.com/drwetter/testssl.sh.git /opt/testssl 2>/dev/null \
    && ln -sf /opt/testssl/testssl.sh /usr/local/bin/testssl.sh 2>/dev/null || true
fi
have testssl.sh && ok "testssl.sh" || warn "testssl.sh no instalado (opcional)"

# ── pip (sast + cloud) · semgrep + prowler + checkov ────────────────────────
PIP="$(command -v pip3 || command -v pip || true)"
if [ -n "${PIP}" ]; then
  "${PIP}" install -q --no-input semgrep prowler checkov >/dev/null 2>&1 \
    && ok "pip: semgrep prowler checkov" || warn "pip install (semgrep/prowler/checkov)"
else
  warn "pip no disponible · instala semgrep/prowler/checkov a mano"
fi

# ── trivy (vulnscan · imágenes/SBOM) ────────────────────────────────────────
if ! have trivy && have apt-get; then
  curl -sSL https://aquasecurity.github.io/trivy-repo/deb/public.key 2>/dev/null \
    | gpg --dearmor -o /usr/share/keyrings/trivy.gpg 2>/dev/null || true
  echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" \
    > /etc/apt/sources.list.d/trivy.list 2>/dev/null || true
  apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq trivy >/dev/null 2>&1 || true
fi
have trivy && ok "trivy" || warn "trivy no instalado (opcional · imágenes Docker/SBOM)"

# ── Resumen + matriz de capacidad real (la misma que usa el autopilot) ──────
echo ""
echo "== Resumen: ${OK} instalados · ${FAIL} omitidos/opcionales =="
echo "== Matriz de capacidad (lo que el autopilot ejecutará REAL) =="
for pair in "recon:nmap" "vulnscan:nuclei" "config:lynis" "sast:semgrep" \
            "webpentest:testssl.sh" "cloud:prowler" "vulnscan:trivy"; do
  srv="${pair%%:*}"; bin="${pair##*:}"
  if have "${bin}"; then printf '  \033[32m✓\033[0m %-12s (%s)\n' "${srv}" "${bin}"
  else printf '  \033[31m✗\033[0m %-12s (%s · no instalado)\n' "${srv}" "${bin}"; fi
done
echo ""
echo "Siguiente paso: USE_MCP_REAL=true en .env.prod + reiniciar backend."
echo "Verifica desde la app:  GET /api/v1/mcps  (o scanner_capabilities())"
