FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    lynis libopenscap8 openscap-utils openscap-scanner \
    wget curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
COPY config/ /app/config/
WORKDIR /app
CMD ["python", "-m", "config.server"]
