import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv(".env")

TABLES = ["project_archived_backups", "projects", "conformity_routes"]


async def main() -> None:
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    for t in TABLES:
        cols = await c.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=$1",
            t,
        )
        names = {r[0] for r in cols}
        print(f"{t:30} exists={bool(cols)}  has_deleted_at={'deleted_at' in names}")
    await c.close()


asyncio.run(main())
