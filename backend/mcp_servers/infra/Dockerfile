FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 git build-essential libpq-dev libssl-dev libffi-dev \
    ruby ruby-dev nmap wget ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb \
      > /tmp/msfinstall \
 && chmod 755 /tmp/msfinstall \
 && /tmp/msfinstall 2>/dev/null || true
ENV PATH="/opt/metasploit-framework/bin:${PATH}"

RUN pip install --no-cache-dir impacket netexec bloodhound certipy-ad coercer 2>/dev/null || true

RUN git clone --depth 1 https://github.com/lgandx/Responder.git /opt/responder 2>/dev/null || true

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
RUN go install github.com/ropnop/kerbrute@latest 2>/dev/null || true

COPY shared/ /app/shared/
COPY infra/ /app/infra/
WORKDIR /app
CMD ["python", "-m", "infra.server"]
