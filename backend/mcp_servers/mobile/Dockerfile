FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre apktool wget curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir mobsf 2>/dev/null || true

COPY shared/ /app/shared/
COPY mobile/ /app/mobile/
WORKDIR /app
CMD ["python", "-m", "mobile.server"]
