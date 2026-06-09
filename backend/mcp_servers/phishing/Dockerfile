FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/gophish \
 && wget -qO /tmp/gophish.zip https://github.com/gophish/gophish/releases/download/v0.12.1/gophish-v0.12.1-linux-64bit.zip 2>/dev/null \
 && unzip /tmp/gophish.zip -d /opt/gophish 2>/dev/null \
 && rm -f /tmp/gophish.zip
ENV PATH="/opt/gophish:${PATH}"

COPY shared/ /app/shared/
COPY phishing/ /app/phishing/
WORKDIR /app
CMD ["python", "-m", "phishing.server"]
