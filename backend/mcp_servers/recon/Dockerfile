FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap masscan wget curl dnsutils whois git ca-certificates unzip \
 && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

RUN go install github.com/owasp-amass/amass/v4/...@latest 2>/dev/null || true \
 && go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
 && go install github.com/projectdiscovery/httpx/cmd/httpx@latest \
 && go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

RUN pip install --no-cache-dir theHarvester shodan

RUN git clone --depth 1 https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb 2>/dev/null || true \
 && ln -sf /opt/exploitdb/searchsploit /usr/local/bin/searchsploit 2>/dev/null || true

COPY shared/ /app/shared/
COPY recon/ /app/recon/
WORKDIR /app
CMD ["python", "-m", "recon.server"]
