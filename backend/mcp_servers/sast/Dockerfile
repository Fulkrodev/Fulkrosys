FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre wget curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir semgrep bandit safety checkov

RUN wget -qO /tmp/depcheck.zip https://github.com/jeremylong/DependencyCheck/releases/latest/download/dependency-check-10.0.0-release.zip 2>/dev/null \
 && unzip /tmp/depcheck.zip -d /opt 2>/dev/null \
 && ln -sf /opt/dependency-check/bin/dependency-check.sh /usr/local/bin/dependency-check 2>/dev/null \
 && rm -f /tmp/depcheck.zip

COPY shared/ /app/shared/
COPY sast/ /app/sast/
WORKDIR /app
CMD ["python", "-m", "sast.server"]
