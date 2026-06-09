"""Process inventory from PKG process nodes."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m16_onboarding import pkg_service as pkg


async def inventory_processes(session: AsyncSession, project_id: uuid.UUID) -> dict:
    processes = await pkg.get_nodes_by_type(session, project_id, "process")

    process_details = []
    for proc in processes:
        systems_used = await pkg.get_neighbors(session, proc["id"], edge_type="uses", direction="outgoing")
        info_processed = await pkg.get_neighbors(session, proc["id"], edge_type="processes", direction="outgoing")
        owners = await pkg.get_neighbors(session, proc["id"], edge_type="owns", direction="incoming")

        process_details.append({
            "label": proc["label"],
            "node_id": str(proc["id"]),
            "properties": proc.get("properties"),
            "systems_used": [s["label"] for s in systems_used],
            "information_processed": [i["label"] for i in info_processed],
            "owners": [o["label"] for o in owners],
        })

    unlinked = [p for p in process_details if not p["systems_used"]]

    return {
        "total_processes": len(processes),
        "processes": process_details,
        "unlinked_processes": len(unlinked),
        "unlinked_process_names": [p["label"] for p in unlinked],
        "verdict": "complete" if not unlinked else "incomplete_inventory",
    }
