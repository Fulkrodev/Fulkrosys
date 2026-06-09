FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/go.tar.gz https://go.dev/dl/go1.22.2.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf /tmp/go.tar.gz && rm /tmp/go.tar.gz
ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"

RUN go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
 && nuclei -update-templates 2>/dev/null || true

RUN wget -qO- https://raw.githubusercontent.com/aquasecurity/trivy-repo/main/install.sh \
      | sh -s -- -b /usr/local/bin v0.50.0 2>/dev/null || true

RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
      | sh -s -- -b /usr/local/bin 2>/dev/null || true

RUN pip install --no-cache-dir gvm-tools python-gvm

COPY shared/ /app/shared/
COPY vulnscan/ /app/vulnscan/
WORKDIR /app
CMD ["python", "-m", "vulnscan.server"]
