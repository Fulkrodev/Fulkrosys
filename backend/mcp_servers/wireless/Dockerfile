FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    aircrack-ng git python3-pip wget curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/derv82/wifite2.git /opt/wifite2 2>/dev/null || true \
 && ln -sf /opt/wifite2/Wifite.py /usr/local/bin/wifite 2>/dev/null || true

COPY shared/ /app/shared/
COPY wireless/ /app/wireless/
WORKDIR /app
CMD ["python", "-m", "wireless.server"]
