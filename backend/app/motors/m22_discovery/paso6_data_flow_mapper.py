"""M22 Paso 6 — Data Flow Mapper por proceso critico (Agente 25).

Genera Data Flow Diagrams BPMN-style por cada proceso critico detectado
por M21. Cruza:
- BusinessProcess (M21) → proceso + sistemas_involucrados + criticidad
- Stakeholder (M21) → propietario del proceso + permisos
- DiscoveredAsset (M22) → software/servicios/hardware que soportan el proceso
- DiscoveredDataStore (M22) → bases de datos + buckets con datos

Por cada proceso critico genera:
- 1 DataFlowDiagram tipo `proceso` (tabla data_flow_diagrams)
- Nodos: entrada (external_entity), procesamiento (process),
  almacenamiento (data_store), salida (external_entity + etiqueta)
- Flujos: con protocolo + cifrado + clasificacion datos
- Mermaid flowchart TD (top-down), ramificado: entradas -> procesos ->
  stores -> salidas
- Observaciones de seguridad (flujos sin cifrar, datos personales visibles,
  stakeholder sin permisos documentados)
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import BusinessProcess, Stakeholder
from backend.app.models.discovery import DataFlowDiagram, DiscoveredDataStore
from backend.app.models.onboarding import DiscoveredAsset

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Matching process <-> assets <-> data stores
# ════════════════════════════════════════════════════════════════════

def _normalize_token(value: str) -> str:
    return (value or "").lower().strip()


def _process_system_tokens(process: BusinessProcess) -> set[str]:
    """Conjunto de tokens identificando sistemas del proceso.

    sistemas_involucrados puede venir como:
    - {"sistemas": ["HIS", "EHR"]}  (M21 default)
    - list directa
    - dict con otras claves
    """
    tokens: set[str] = set()
    sis = process.sistemas_involucrados
    if isinstance(sis, dict):
        raw = sis.get("sistemas") or sis.get("systems") or list(sis.values())
    else:
        raw = sis or []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                tokens.add(_normalize_token(item))
    # Tokens del nombre tambien
    for w in (process.nombre or "").split():
        if len(w) >= 3:
            tokens.add(_normalize_token(w))
    return tokens


def match_assets_to_process(
    process: BusinessProcess, assets: list[DiscoveredAsset],
) -> list[DiscoveredAsset]:
    tokens = _process_system_tokens(process)
    matched: list[DiscoveredAsset] = []
    for a in assets:
        candidates = {
            _normalize_token(a.nombre or ""),
            _normalize_token((a.metadata_extra or {}).get("description") or ""),
        }
        tag_list = (a.metadata_extra or {}).get("tags") or []
        for t in tag_list:
            if isinstance(t, str):
                candidates.add(_normalize_token(t))
        if any(
            tok and any(tok in cand for cand in candidates)
            for tok in tokens
        ):
            matched.append(a)
    return matched


def match_stores_to_process(
    process: BusinessProcess, stores: list[DiscoveredDataStore],
) -> list[DiscoveredDataStore]:
    tokens = _process_system_tokens(process)
    matched: list[DiscoveredDataStore] = []
    for s in stores:
        cand = _normalize_token(s.nombre or "")
        if any(tok and tok in cand for tok in tokens):
            matched.append(s)
            continue
        # Fallback: procesos de salud -> stores con datos_salud
        if s.tiene_datos_salud and any(
            tk in {"historia", "clinica", "salud", "paciente"} for tk in tokens
        ):
            matched.append(s)
    return matched


# ════════════════════════════════════════════════════════════════════
# Construccion del grafo
# ════════════════════════════════════════════════════════════════════

def _encrypted(protocol: str) -> bool:
    return protocol.upper() in {"HTTPS", "TLS", "SSH", "SFTP", "SMTPS", "QUIC"}


def _build_process_graph(
    process: BusinessProcess,
    matched_assets: list[DiscoveredAsset],
    matched_stores: list[DiscoveredDataStore],
    process_owner: Optional[Stakeholder],
) -> tuple[list[dict], list[dict], list[str]]:
    """Devuelve (nodos, flujos, observaciones)."""
    nodos: list[dict] = []
    flujos: list[dict] = []
    observaciones: list[str] = []

    # Entrada: usuarios y sistemas externos
    entry_id = "in_user"
    nodos.append({
        "id": entry_id, "tipo": "external_entity",
        "nombre": f"Usuarios de {process.nombre}",
        "descripcion": "Punto de entrada humano o externo.",
    })

    # Proceso central
    proc_id = "p_main"
    nodos.append({
        "id": proc_id, "tipo": "process",
        "nombre": process.nombre,
        "process_id": str(process.id),
        "criticidad": process.criticidad,
        "rto_horas": process.rto_horas,
        "rpo_horas": process.rpo_horas,
        "propietario": (process_owner.nombre if process_owner else process.propietario),
    })

    # Flujo entrada -> proceso
    flujos.append({
        "origen": entry_id, "destino": proc_id,
        "datos": "credenciales + request",
        "protocolo": "HTTPS",
        "cifrado": True,
    })

    # Assets soportan al proceso (hw/sw). Los tratamos como subprocesos
    for i, a in enumerate(matched_assets):
        tipo = (a.tipo_magerit or "SW").upper()
        aid = f"a{i + 1}"
        node_tipo = "process" if tipo in {"SW", "S"} else "service"
        nodos.append({
            "id": aid, "tipo": node_tipo,
            "nombre": a.nombre,
            "asset_id": str(a.id),
            "tipo_magerit": tipo,
            "criticidad": a.criticidad_propuesta,
        })
        flujos.append({
            "origen": proc_id, "destino": aid,
            "datos": "invocacion servicio",
            "protocolo": "TLS",
            "cifrado": True,
        })

    # Data stores
    for i, s in enumerate(matched_stores):
        sid = f"ds{i + 1}"
        nodos.append({
            "id": sid, "tipo": "data_store",
            "nombre": s.nombre,
            "data_store_id": str(s.id),
            "clasificacion": s.clasificacion_inicial,
            "datos_personales": bool(s.tiene_datos_personales),
            "cifrado_reposo": s.cifrado_en_reposo,
        })
        proto = "TLS" if (s.cifrado_en_transito is not False) else "UNENCRYPTED"
        flujos.append({
            "origen": proc_id, "destino": sid,
            "datos": (
                "datos personales" if s.tiene_datos_personales else "datos de negocio"
            ),
            "protocolo": proto,
            "cifrado": _encrypted(proto),
        })
        if s.tiene_datos_personales and s.cifrado_en_reposo is False:
            observaciones.append(
                f"Data store '{s.nombre}' almacena datos personales sin cifrado at-rest."
            )
        if s.tiene_datos_personales and s.control_acceso == "public":
            observaciones.append(
                f"Data store '{s.nombre}' publico contiene datos personales."
            )

    # Salida: reportes/APIs externos derivados del proceso
    out_id = "out_report"
    nodos.append({
        "id": out_id, "tipo": "external_entity",
        "nombre": f"Salidas de {process.nombre}",
        "descripcion": "Respuesta, reportes, notificaciones.",
    })
    flujos.append({
        "origen": proc_id, "destino": out_id,
        "datos": "respuesta / report",
        "protocolo": "HTTPS",
        "cifrado": True,
    })

    # Observaciones adicionales
    if process_owner is None and not process.propietario:
        observaciones.append(
            f"Proceso '{process.nombre}' sin propietario stakeholder asignado."
        )
    for f in flujos:
        if not f.get("cifrado", True):
            observaciones.append(
                f"Flujo sin cifrar ({f.get('protocolo')}) entre "
                f"{f['origen']} y {f['destino']}."
            )

    return nodos, flujos, observaciones


def generate_mermaid_bpmn(
    process_name: str, nodos: list[dict], flujos: list[dict],
) -> str:
    """Mermaid flowchart TD con agrupacion BPMN-style."""
    lines = [
        f"%% DFD BPMN para proceso: {process_name}",
        "flowchart TD",
    ]
    for n in nodos:
        nid = n["id"]
        label = str(n.get("nombre") or nid).replace("\"", "'").replace("\n", " ")
        tipo = n.get("tipo")
        if tipo == "external_entity":
            lines.append(f"    {nid}([\"{label}\"])")
        elif tipo == "data_store":
            lines.append(f"    {nid}[(\"{label}\")]")
        elif tipo == "service":
            lines.append(f"    {nid}{{{{\"{label}\"}}}}")
        else:
            lines.append(f"    {nid}[\"{label}\"]")
    for f in flujos:
        origen = f.get("origen")
        destino = f.get("destino")
        if not origen or not destino:
            continue
        label = f.get("datos") or f.get("protocolo") or ""
        label = str(label).replace("\"", "'")
        arrow = "-->" if f.get("cifrado", True) else "-. sin cifrar .->"
        if label:
            lines.append(f"    {origen} {arrow}|{label}| {destino}")
        else:
            lines.append(f"    {origen} {arrow} {destino}")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# Persistencia
# ════════════════════════════════════════════════════════════════════

async def _load_project_entities(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[list[BusinessProcess], list[DiscoveredAsset], list[DiscoveredDataStore], list[Stakeholder]]:
    r_p = await db.execute(
        select(BusinessProcess).where(
            BusinessProcess.project_id == project_id,
            BusinessProcess.deleted_at.is_(None),
        )
    )
    r_a = await db.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    r_s = await db.execute(
        select(DiscoveredDataStore).where(
            DiscoveredDataStore.project_id == project_id,
            DiscoveredDataStore.deleted_at.is_(None),
        )
    )
    r_st = await db.execute(
        select(Stakeholder).where(
            Stakeholder.project_id == project_id,
            Stakeholder.deleted_at.is_(None),
        )
    )
    return (
        list(r_p.scalars().all()),
        list(r_a.scalars().all()),
        list(r_s.scalars().all()),
        list(r_st.scalars().all()),
    )


async def map_flows_for_critical_processes(
    db: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    include_all: bool = False,
) -> list[DataFlowDiagram]:
    """Genera un DFD por proceso critico (o todos si include_all=True)."""
    processes, assets, stores, stakeholders = await _load_project_entities(
        db, project_id,
    )
    stakeholders_by_name: dict[str, Stakeholder] = {
        (s.nombre or "").lower(): s for s in stakeholders
    }

    target_processes = (
        processes if include_all
        else [p for p in processes if (p.criticidad or "").lower() == "alta"]
    )

    diagrams: list[DataFlowDiagram] = []
    for p in target_processes:
        matched_assets = match_assets_to_process(p, assets)
        matched_stores = match_stores_to_process(p, stores)
        owner = stakeholders_by_name.get((p.propietario or "").lower())
        nodos, flujos, observaciones = _build_process_graph(
            p, matched_assets, matched_stores, owner,
        )
        if len(matched_stores) > 0:
            classifs = [
                s.clasificacion_inicial or "sin_clasificar"
                for s in matched_stores
            ]
            ORDER = ["sin_clasificar", "publica", "interna", "confidencial", "reservada"]
            classif_max = max(
                classifs, key=lambda c: ORDER.index(c) if c in ORDER else 0,
            )
        else:
            classif_max = "sin_clasificar"
        mermaid = generate_mermaid_bpmn(p.nombre, nodos, flujos)

        dfd = DataFlowDiagram(
            project_id=project_id,
            discovery_run_id=run_id,
            nombre=f"DFD — {p.nombre}",
            descripcion=(
                f"Data Flow Diagram BPMN del proceso '{p.nombre}' "
                f"(criticidad={p.criticidad}, RTO={p.rto_horas}h, "
                f"RPO={p.rpo_horas}h)."
            ),
            tipo="proceso",
            nodos=nodos,
            flujos=flujos,
            clasificacion_max_datos=classif_max,
            mermaid_code=mermaid,
            observaciones_seguridad=observaciones,
        )
        db.add(dfd)
        diagrams.append(dfd)

    await db.flush()
    return diagrams


async def build_data_flow_table(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Resumen tabular de los flujos agregados: tabla `data_flows` logica.

    No persiste en una tabla separada — devuelve la vista derivada de los
    DataFlowDiagram activos. Cada fila = 1 flujo entre nodos etiquetado.
    """
    r = await db.execute(
        select(DataFlowDiagram).where(
            DataFlowDiagram.project_id == project_id,
            DataFlowDiagram.deleted_at.is_(None),
        )
    )
    rows: list[dict[str, Any]] = []
    for d in r.scalars().all():
        nodo_by_id = {n["id"]: n for n in (d.nodos or []) if isinstance(n, dict)}
        for f in d.flujos or []:
            if not isinstance(f, dict):
                continue
            rows.append({
                "dfd_id": str(d.id),
                "dfd_nombre": d.nombre,
                "origen": nodo_by_id.get(f.get("origen"), {}).get("nombre", f.get("origen")),
                "destino": nodo_by_id.get(f.get("destino"), {}).get("nombre", f.get("destino")),
                "datos": f.get("datos"),
                "protocolo": f.get("protocolo"),
                "cifrado": bool(f.get("cifrado", True)),
                "clasificacion_max": d.clasificacion_max_datos,
            })
    return rows


__all__ = [
    "match_assets_to_process",
    "match_stores_to_process",
    "generate_mermaid_bpmn",
    "map_flows_for_critical_processes",
    "build_data_flow_table",
]
