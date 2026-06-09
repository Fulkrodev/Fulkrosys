FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    hashcat john ruby ruby-dev wget curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN gem install cewl 2>/dev/null || true

RUN mkdir -p /opt/wordlists \
 && wget -qO /opt/wordlists/rockyou.txt.gz https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt 2>/dev/null || true

COPY shared/ /app/shared/
COPY cracking/ /app/cracking/
WORKDIR /app
CMD ["python", "-m", "cracking.server"]
