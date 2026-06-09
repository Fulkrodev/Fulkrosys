FROM python:3.12-slim

COPY shared/ /app/shared/
COPY scope_enforcer/ /app/scope_enforcer/
WORKDIR /app

CMD ["python", "-m", "scope_enforcer.server"]
