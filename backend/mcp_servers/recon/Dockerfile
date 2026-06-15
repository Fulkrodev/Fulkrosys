FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap masscan wget curl dnsutils whois git ca-certificates unzip \
 && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

# amass es best-effort (su build con Go falla a menudo · opcional · log visible,
# no se silencia con 2>/dev/null). subfinder/httpx/naabu son PRIMARIOS (sin || true).
RUN ( go install github.com/owasp-amass/amass/v4/...@latest || echo "amass opcional · omitido" ) \
 && go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
 && go install github.com/projectdiscovery/httpx/cmd/httpx@latest \
 && go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

RUN pip install --no-cache-dir theHarvester shodan

# exploitdb/searchsploit best-effort (dataset grande · opcional · log visible).
RUN ( git clone --depth 1 https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb \
      && ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit ) \
    || echo "exploitdb opcional · omitido"

# §6 audit-2026-06-15 · el build FALLA si falta un binario primario (antes el
# `2>/dev/null||true` dejaba la imagen verde sin herramientas → scan en vacío).
RUN for t in nmap masscan subfinder httpx naabu; do \
      command -v "$t" >/dev/null 2>&1 || { echo "FALTA binario primario: $t" >&2; exit 1; }; \
    done

COPY shared/ /app/shared/
COPY recon/ /app/recon/
WORKDIR /app
CMD ["python", "-m", "recon.server"]
