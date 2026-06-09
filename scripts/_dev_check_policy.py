import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv(".env")

PID = "4442b6e8-8bf9-4d78-9e33-a752f68e3c27"


async def main() -> None:
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    pols = await c.fetch(
        "SELECT polname, pg_get_expr(polqual, polrelid) AS using_expr "
        "FROM pg_policy WHERE polrelid='public.projects'::regclass"
    )
    print("=== projects RLS policies ===")
    for p in pols:
        print(f"  {p['polname']}: {p['using_expr']}")
    forced = await c.fetchval(
        "SELECT relforcerowsecurity FROM pg_class WHERE oid='public.projects'::regclass"
    )
    print("force RLS:", forced)
    # simulate the real request as fulkro_app WITH app.current_user + project ctx
    await c.execute("SET ROLE fulkro_app")
    await c.execute("SELECT set_config('app.current_user','157cf7fb-2d2a-423f-9f21-a1fb9f9e7329',false)")
    n1 = await c.fetchval("SELECT count(*) FROM projects WHERE id=$1", PID)
    print(f"\nwith app.current_user set, visible: {n1}")
    await c.execute("SELECT set_config('app.current_project_id',$1,false)", PID)
    n2 = await c.fetchval("SELECT count(*) FROM projects WHERE id=$1", PID)
    print(f"with app.current_project_id set too, visible: {n2}")
    await c.close()


asyncio.run(main())
