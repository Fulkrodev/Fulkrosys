"""Data Flow Diagrams (M22-C).

Genera DFDs simplificados cruzando assets+identities+data_stores descubiertos.
Incluye generador de codigo Mermaid y deteccion de observaciones de seguridad
(flujos sin cifrar, datos personales salientes, etc).
"""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DataFlowDiagram, DiscoveredDataStore
from backend.app.models.onboarding import DiscoveredAsset, DiscoveredIdentity


_CLASSIF_ORDER = ["sin_clasificar", "publica", "interna", "confidencial", "reservada"]

# tipo MAGERIT -> rol DFD
_PROCESS_TYPES = {"SW", "S"}  # software/servicios -> process
_DATA_TYPES = {"D"}  # datos -> data_store
_COMM_TYPES = {"COM"}  # comunicaciones -> pueden ser external boundary


def _max_classification(items: Iterable[str]) -> str:
    best_idx = 0
    for c in items:
        if not c:
            continue
        try:
            idx = _CLASSIF_ORDER.index(c)
        except ValueError:
            continue
        if idx > best_idx:
            best_idx = idx
    return _CLASSIF_ORDER[best_idx]


def _asset_node_type(asset: DiscoveredAsset) -> str:
    tipo = (asset.tipo_magerit or "").upper()
    if tipo in _DATA_TYPES:
        return "data_store"
    if tipo in _PROCESS_TYPES:
        return "process"
    return "process"


def _is_encrypted_protocol(proto: str) -> bool:
    return (proto or "").upper() in {"HTTPS", "TLS", "SSH", "SFTP", "SMTPS"}


def generate_mermaid(nodos: list[dict], flujos: list[dict]) -> str:
    """Genera codigo Mermaid flowchart desde nodos y flujos."""
    lines = ["flowchart LR"]
    # Declarar nodos con shape por tipo
    for n in nodos:
        nid = n["id"]
        nombre = str(n.get("nombre") or nid).replace("\"", "'")
        ntipo = n.get("tipo") or "process"
        if ntipo == "external_entity":
            shape_l, shape_r = "([", "])"
        elif ntipo == "data_store":
            shape_l, shape_r = "[(", ")]"
        else:
            shape_l, shape_r = "[", "]"
        lines.append(f"    {nid}{shape_l}\"{nombre}\"{shape_r}")
    # Flujos
    for f in flujos:
        origen, destino = f.get("origen"), f.get("destino")
        if not origen or not destino:
            continue
        label = f.get("protocolo") or f.get("datos") or ""
        label = str(label).replace("\"", "'")
        if label:
            lines.append(f"    {origen} -->|{label}| {destino}")
        else:
            lines.append(f"    {origen} --> {destino}")
    return "\n".join(lines)


def _detect_security_observations(
    nodos: list[dict], flujos: list[dict], data_stores: list[DiscoveredDataStore],
) -> list[str]:
    obs: list[str] = []
    ds_by_id = {str(d.id): d for d in data_stores}

    for f in flujos:
        proto = (f.get("protocolo") or "").upper()
        if proto and not _is_encrypted_protocol(proto):
            obs.append(
                f"Flujo sin cifrar ({proto}) entre "
                f"{f.get('origen')} y {f.get('destino')}"
            )

        destino_node = next(
            (n for n in nodos if n.get("id") == f.get("destino")), None,
        )
        if destino_node and destino_node.get("data_store_id"):
            ds = ds_by_id.get(str(destino_node["data_store_id"]))
            if ds and ds.tiene_datos_personales and not _is_encrypted_protocol(proto):
                obs.append(
                    f"Datos personales viajando sin cifrado hacia {destino_node.get('nombre')}"
                )

    for ds in data_stores:
        if ds.tiene_datos_personales and ds.control_acceso == "public":
            obs.append(
                f"Data store '{ds.nombre}' publico contiene datos personales"
            )
        if ds.tiene_datos_personales and ds.cifrado_en_reposo is False:
            obs.append(
                f"Data store '{ds.nombre}' con datos personales sin cifrado en reposo"
            )
    return obs


async def _load_project_entities(
    session: AsyncSession, project_id: uuid.UUID,
) -> tuple[list[DiscoveredAsset], list[DiscoveredIdentity], list[DiscoveredDataStore]]:
    r_a = await session.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    r_i = await session.execute(
        select(DiscoveredIdentity).where(
            DiscoveredIdentity.project_id == project_id,
            DiscoveredIdentity.deleted_at.is_(None),
        )
    )
    r_d = await session.execute(
        select(DiscoveredDataStore).where(
            DiscoveredDataStore.project_id == project_id,
            DiscoveredDataStore.deleted_at.is_(None),
        )
    )
    return (
        list(r_a.scalars().all()),
        list(r_i.scalars().all()),
        list(r_d.scalars().all()),
    )


def _build_nodes_and_flows(
    assets: list[DiscoveredAsset],
    identities: list[DiscoveredIdentity],
    data_stores: list[DiscoveredDataStore],
) -> tuple[list[dict], list[dict]]:
    nodos: list[dict] = []
    flujos: list[dict] = []
    node_index: dict[str, str] = {}  # entity_id -> dfd node_id

    # Identidades externas -> external_entity
    ext_idents = [
        i for i in identities if i.tipo_cuenta in {"externa", "invitado"}
    ]
    for i, ident in enumerate(ext_idents):
        nid = f"ext{i + 1}"
        nodos.append({
            "id": nid,
            "tipo": "external_entity",
            "nombre": ident.display_name or ident.username or "externo",
            "identity_id": str(ident.id),
        })
        node_index[str(ident.id)] = nid

    # Assets -> process / data_store
    for i, asset in enumerate(assets):
        ntipo = _asset_node_type(asset)
        nid = f"a{i + 1}"
        nodos.append({
            "id": nid,
            "tipo": ntipo,
            "nombre": asset.nombre,
            "asset_id": str(asset.id),
            "tipo_magerit": asset.tipo_magerit,
        })
        node_index[str(asset.id)] = nid

    # Data stores -> data_store
    for i, ds in enumerate(data_stores):
        nid = f"ds{i + 1}"
        nodos.append({
            "id": nid,
            "tipo": "data_store",
            "nombre": ds.nombre,
            "data_store_id": str(ds.id),
            "clasificacion": ds.clasificacion_inicial,
        })
        node_index[str(ds.id)] = nid

    # Flujos inferidos:
    # 1. external_entity -> process (cuando hay procesos, conectar con primero)
    process_nodes = [n for n in nodos if n["tipo"] == "process"]
    ext_nodes = [n for n in nodos if n["tipo"] == "external_entity"]
    if process_nodes and ext_nodes:
        for e in ext_nodes:
            flujos.append({
                "origen": e["id"], "destino": process_nodes[0]["id"],
                "datos": "credenciales/request", "protocolo": "HTTPS",
                "cifrado": True,
            })

    # 2. process -> data_store (cada process se conecta a cada ds)
    ds_nodes = [n for n in nodos if n["tipo"] == "data_store"]
    for p in process_nodes:
        for ds in ds_nodes:
            flujos.append({
                "origen": p["id"], "destino": ds["id"],
                "datos": "datos negocio", "protocolo": "TLS",
                "cifrado": True,
            })

    return nodos, flujos


async def generate_dfd(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    assets: list[DiscoveredAsset],
    identities: list[DiscoveredIdentity],
    data_stores: list[DiscoveredDataStore],
    nombre: str = "DFD Principal",
    tipo: str = "sistema_sistema",
    descripcion: Optional[str] = None,
) -> DataFlowDiagram:
    nodos, flujos = _build_nodes_and_flows(assets, identities, data_stores)
    mermaid = generate_mermaid(nodos, flujos)
    clasif_max = _max_classification([d.clasificacion_inicial for d in data_stores])
    observaciones = _detect_security_observations(nodos, flujos, data_stores)

    dfd = DataFlowDiagram(
        project_id=project_id,
        discovery_run_id=run_id,
        nombre=nombre,
        descripcion=descripcion,
        tipo=tipo,
        nodos=nodos,
        flujos=flujos,
        clasificacion_max_datos=clasif_max,
        mermaid_code=mermaid,
        observaciones_seguridad=observaciones,
    )
    session.add(dfd)
    await session.flush()
    return dfd


async def generate_all_dfds(
    session: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
) -> list[DataFlowDiagram]:
    """Genera dos DFDs automaticos: sistema-sistema y datos-personales."""
    assets, identities, data_stores = await _load_project_entities(session, project_id)
    dfds: list[DataFlowDiagram] = []

    # DFD 1: sistema-sistema (assets + data stores completos)
    dfds.append(await generate_dfd(
        session, project_id, run_id,
        assets=assets, identities=identities, data_stores=data_stores,
        nombre="DFD Sistema-Sistema", tipo="sistema_sistema",
        descripcion="Flujos entre assets, identidades externas y data stores.",
    ))

    # DFD 2: solo data stores con datos personales
    ds_personales = [d for d in data_stores if d.tiene_datos_personales]
    if ds_personales:
        dfds.append(await generate_dfd(
            session, project_id, run_id,
            assets=[a for a in assets if (a.tipo_magerit or "").upper() in _PROCESS_TYPES],
            identities=[i for i in identities if i.tipo_cuenta in {"externa", "invitado"}],
            data_stores=ds_personales,
            nombre="DFD Datos Personales", tipo="datos_personales",
            descripcion="Flujos que involucran data stores con datos personales.",
        ))
    return dfds


async def list_dfds(
    session: AsyncSession, project_id: uuid.UUID,
) -> list[DataFlowDiagram]:
    r = await session.execute(
        select(DataFlowDiagram)
        .where(
            DataFlowDiagram.project_id == project_id,
            DataFlowDiagram.deleted_at.is_(None),
        )
        .order_by(DataFlowDiagram.created_at.desc())
    )
    return list(r.scalars().all())


async def get_dfd(
    session: AsyncSession, dfd_id: uuid.UUID,
) -> Optional[DataFlowDiagram]:
    r = await session.execute(
        select(DataFlowDiagram).where(
            DataFlowDiagram.id == dfd_id,
            DataFlowDiagram.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


def to_dict(d: DataFlowDiagram) -> dict:
    return {
        "id": str(d.id),
        "project_id": str(d.project_id),
        "discovery_run_id": str(d.discovery_run_id),
        "nombre": d.nombre,
        "descripcion": d.descripcion,
        "tipo": d.tipo,
        "nodos": d.nodos or [],
        "flujos": d.flujos or [],
        "clasificacion_max_datos": d.clasificacion_max_datos,
        "mermaid_code": d.mermaid_code,
        "observaciones_seguridad": d.observaciones_seguridad or [],
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }
