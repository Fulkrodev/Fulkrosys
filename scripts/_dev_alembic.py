"""Dev helper: run alembic with DATABASE_MIGRATE_URL loaded from .env (so env.py
uses the privileged fulkro_migrate role for DDL). Pass alembic args through.

Uso (desde la raíz del repo): .venv/bin/python scripts/_dev_alembic.py upgrade head
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

if not os.environ.get("DATABASE_MIGRATE_URL"):
    sys.exit("DATABASE_MIGRATE_URL not in .env")

args = sys.argv[1:] or ["current"]
proc = subprocess.run(
    [sys.executable, "-m", "alembic", *args],
    cwd=str(ROOT / "backend"),
    env=os.environ.copy(),
)
sys.exit(proc.returncode)
