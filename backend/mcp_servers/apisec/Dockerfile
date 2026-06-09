FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir arjun

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
RUN go install github.com/assetnote/kiterunner/cmd/kr@latest 2>/dev/null || true

COPY shared/ /app/shared/
COPY apisec/ /app/apisec/
WORKDIR /app
CMD ["python", "-m", "apisec.server"]
