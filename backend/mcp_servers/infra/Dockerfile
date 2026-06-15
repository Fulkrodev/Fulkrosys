FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 git build-essential libpq-dev libssl-dev libffi-dev \
    ruby ruby-dev nmap wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb \
      > /tmp/msfinstall \
 && chmod 755 /tmp/msfinstall \
 && ( /tmp/msfinstall || echo "metasploit best-effort · omitido (log visible)" )
ENV PATH="/opt/metasploit-framework/bin:${PATH}"

# Suite AD ofensiva · best-effort (pesada · puede fallar en slim) · log VISIBLE
# (antes 2>/dev/null ocultaba el fallo → imagen verde sin herramientas).
RUN pip install --no-cache-dir impacket netexec bloodhound certipy-ad coercer \
    || echo "suite AD (impacket/netexec/...) best-effort · omitido (log visible)"

RUN git clone --depth 1 https://github.com/lgandx/Responder.git /opt/responder \
    || echo "Responder best-effort · omitido (log visible)"

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
RUN go install github.com/ropnop/kerbrute@latest \
    || echo "kerbrute best-effort · omitido (log visible)"

# §6 audit-2026-06-15 · el build FALLA si falta el binario base certero (nmap).
RUN command -v nmap >/dev/null 2>&1 || { echo "FALTA binario primario: nmap" >&2; exit 1; }

COPY shared/ /app/shared/
COPY infra/ /app/infra/
WORKDIR /app
CMD ["python", "-m", "infra.server"]
