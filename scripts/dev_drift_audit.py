"""Read-only DB drift audit: compare ORM Base.metadata (what the code expects)
against the live dev DB (information_schema). Lists every missing table/column
that would 500 the app. NO writes.

Run: /home/usuario/fulkro/.venv/bin/python scripts/dev_drift_audit.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import backend.app.models  # noqa: F401,E402  (registers all models)
from backend.app.models.base import Base  # noqa: E402

import asyncpg  # noqa: E402


async def main() -> None:
    url = (
        os.environ["DATABASE_URL"]
        .replace("+asyncpg", "")
        .replace("+psycopg2", "")
        .replace("postgresql+asyncpg", "postgresql")
    )
    conn = await asyncpg.connect(url)
    colrows = await conn.fetch(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema='public'"
    )
    db: dict[str, set[str]] = {}
    for r in colrows:
        db.setdefault(r["table_name"], set()).add(r["column_name"])
    tabrows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    db_tables = {t["table_name"] for t in tabrows}
    await conn.close()

    missing_tables: list[str] = []
    missing_cols: list[str] = []
    for tname, table in sorted(Base.metadata.tables.items()):
        short = tname.split(".")[-1]
        if short not in db_tables:
            missing_tables.append(short)
            continue
        for col in table.columns:
            if col.name not in db.get(short, set()):
                nn = "" if col.nullable else " NOT NULL"
                missing_cols.append(f"{short}.{col.name}  ({col.type}{nn})")

    print(f"=== MISSING TABLES (modelo, NO en DB): {len(missing_tables)}")
    for t in missing_tables:
        print("  -", t)
    print(f"\n=== MISSING COLUMNS (modelo, NO en DB): {len(missing_cols)}")
    for c in missing_cols:
        print("  -", c)
    print(
        f"\n=== modelo: {len(Base.metadata.tables)} tablas · DB public: {len(db_tables)} tablas"
    )


if __name__ == "__main__":
    asyncio.run(main())
