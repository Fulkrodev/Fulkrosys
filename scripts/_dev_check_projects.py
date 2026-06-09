import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv(".env")


async def main() -> None:
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    nclients = await c.fetchval("SELECT count(*) FROM clients WHERE deleted_at IS NULL")
    nprojects = await c.fetchval("SELECT count(*) FROM projects WHERE deleted_at IS NULL")
    print(f"clients={nclients}  projects={nprojects}")
    rows = await c.fetch(
        "SELECT p.id AS project_id, p.client_id, p.nombre, c.nombre AS cliente "
        "FROM projects p JOIN clients c ON c.id=p.client_id "
        "WHERE p.deleted_at IS NULL LIMIT 5"
    )
    print("\nsample projects (project_id != client_id):")
    for r in rows:
        same = "SAME" if str(r["project_id"]) == str(r["client_id"]) else "DIFF"
        print(f"  proj={r['project_id']}  client={r['client_id']}  [{same}]  {r['cliente']} / {r['nombre']}")
    await c.close()


asyncio.run(main())
