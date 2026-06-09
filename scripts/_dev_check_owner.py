import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv(".env")

PID = "4442b6e8-8bf9-4d78-9e33-a752f68e3c27"


async def main() -> None:
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    # who am I
    role = await c.fetchval("SELECT current_user")
    print("connected as:", role)
    # does the project row exist (under this role's RLS)?
    exists = await c.fetchval("SELECT count(*) FROM projects WHERE id=$1", PID)
    print(f"projects row visible to {role}: {exists}")
    cid = await c.fetchval("SELECT client_id FROM projects WHERE id=$1", PID)
    print("client_id (direct):", cid)
    # call the function
    try:
        owner = await c.fetchval("SELECT get_project_owner($1)", PID)
        print("get_project_owner():", owner)
    except Exception as e:
        print("get_project_owner ERROR:", repr(e)[:160])
    # function definition (security definer?)
    defn = await c.fetchval(
        "SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname='get_project_owner' LIMIT 1"
    )
    print("\n--- get_project_owner def ---")
    print(defn)
    await c.close()


asyncio.run(main())
