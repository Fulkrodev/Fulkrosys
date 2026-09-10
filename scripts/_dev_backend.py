"""Dev backend launcher: load .env into os.environ (so auth/crypto.py reads the
NON-ephemeral Ed25519 key · OPS-052 72ª) then run uvicorn on :8000.

Uso (desde la raíz del repo): .venv/bin/python scripts/_dev_backend.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # repo root on sys.path → `backend` importable
load_dotenv(ROOT / ".env")

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )
