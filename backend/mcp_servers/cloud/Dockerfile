FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir prowler scoutsuite pacu kube-hunter

RUN wget -qO /usr/local/bin/kube-bench https://github.com/aquasecurity/kube-bench/releases/latest/download/kube-bench_linux_amd64 \
 && chmod +x /usr/local/bin/kube-bench 2>/dev/null || true

COPY shared/ /app/shared/
COPY cloud/ /app/cloud/
WORKDIR /app
CMD ["python", "-m", "cloud.server"]
