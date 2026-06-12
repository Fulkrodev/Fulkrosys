"""R20 · builders de contexto de continuidad (BIA E-400 · Estrategias E-401 · DRP E-403).

Pueblan RTO/RPO/procesos críticos/estrategias/ubicaciones/proveedores hoy vacíos.
Fuentes (OPS-045 audit-first · sin tabla nueva):
- ``bia_analyses`` (BIA estructurado per servicio · RTO/RPO/impacto · m19_risk).
- ``cliente_continuidad_input`` (cuestionario cliente · procesos_críticos +
  RTO/RPO tolerancia + impacto diario).
- ``services`` (m01 · servicios finalistas/instrumentales · fallback).
- ``system_sites`` (R05 · sedes físicas / regiones cloud · ubicaciones).
- ``providers`` (m14 · proveedores críticos).

El contexto base (cliente/proyecto/responsables/firmas) lo aporta
``build_governance_context`` (merge universal en ``generate_document``); estos
builders sólo aportan los datos de continuidad. Determinista (R1 · trazabilidad
ENAC): nunca inventa cifras; donde no hay dato, deja marca honesta.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.bia import BiaAnalysis
from backend.app.models.cliente_continuidad import ClienteContinuidadInput
from backend.app.models.core import Service, System, SystemSite
from backend.app.models.m14_providers import Provider

_PENDIENTE = "(pendiente de cumplimentar)"


def _fmt_horas(h: int | None) -> str:
    if h is None:
        return _PENDIENTE
    if h < 24:
        return f"{h} horas"
    dias = round(h / 24, 1)
    dias_txt = f"{int(dias)}" if dias == int(dias) else f"{dias}"
    return f"{h} horas ({dias_txt} día{'s' if dias != 1 else ''})"


def _criticidad_from_rto(rto_h: int | None) -> str:
    if rto_h is None:
        return "ALTO"
    if rto_h <= 4:
        return "CRÍTICO"
    if rto_h <= 24:
        return "ALTO"
    if rto_h <= 72:
        return "MEDIO"
    return "BAJO"


def _estrategia_from_rto(rto_h: int | None) -> str:
    if rto_h is None or rto_h <= 4:
        return "Redundancia activa (active-active) + sitio alterno hot"
    if rto_h <= 24:
        return "Sitio alterno warm + restauración desde copias de seguridad (E-106)"
    if rto_h <= 72:
        return "Restauración desde copias de seguridad (E-106) en sitio alterno"
    return "Procedimiento manual de contingencia + restauración programada"


def _mecanismo_from_rto(rto_h: int | None) -> str:
    if rto_h is None or rto_h <= 4:
        return "Failover automático a réplica activa"
    if rto_h <= 24:
        return "Activación de sitio warm + restauración de backups"
    return "Restauración desde copias de seguridad"


def _eur(value) -> str:
    if value is None:
        return "(por determinar)"
    try:
        return f"~{Decimal(value):,.0f} €".replace(",", ".")
    except (TypeError, ValueError):
        return "(por determinar)"


def _impacto_matrix(criticidad: str, daily_eur) -> dict:
    """Matriz temporal cualitativa determinista según criticidad (op.cont.1)."""
    niveles = {
        "CRÍTICO": ["Moderado", "Alto", "Alto", "Crítico", "Inasumible", "Inasumible"],
        "ALTO": ["Bajo", "Moderado", "Alto", "Alto", "Crítico", "Inasumible"],
        "MEDIO": ["Bajo", "Bajo", "Moderado", "Alto", "Alto", "Crítico"],
        "BAJO": ["Bajo", "Bajo", "Bajo", "Moderado", "Alto", "Alto"],
    }.get(criticidad, ["Bajo", "Moderado", "Alto", "Alto", "Crítico", "Inasumible"])
    # factores económicos por ventana (fracción del impacto diario)
    factores = [1 / 24, 4 / 24, 8 / 24, 1.0, 3.0, 7.0]
    horas = ["h1", "h4", "h8", "h24", "h72", "s1"]
    out: dict = {}
    for i, key in enumerate(horas):
        eco = (
            _eur(Decimal(str(daily_eur)) * Decimal(str(factores[i])))
            if daily_eur is not None else "(según valoración)"
        )
        out[key] = {
            "operativo": niveles[i],
            "economico": eco,
            "reputacional": niveles[i],
            "legal": "Alto" if niveles[i] in ("Crítico", "Inasumible") else "Moderado",
        }
    return out


async def _collect_processes(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """Lista canónica de procesos críticos (bia_analyses ∪ cuestionario ∪ servicios)."""
    bia_rows = list((await db.execute(
        select(BiaAnalysis).where(BiaAnalysis.project_id == project_id)
        .order_by(BiaAnalysis.service_name)
    )).scalars().all())

    quest = (await db.execute(
        select(ClienteContinuidadInput).where(
            ClienteContinuidadInput.project_id == project_id,
        )
    )).scalar_one_or_none()
    quest_procs = {}
    global_rto = global_rpo = None
    global_daily = None
    if quest is not None:
        global_rto = quest.rto_horas_tolerancia
        global_rpo = quest.rpo_horas_tolerancia
        global_daily = quest.impacto_diario_eur
        for p in (quest.procesos_criticos or []):
            if isinstance(p, dict) and p.get("nombre"):
                quest_procs[str(p["nombre"]).strip().lower()] = p

    procesos: list[dict] = []

    def _enrich(nombre: str, base: dict) -> dict:
        q = quest_procs.get(nombre.strip().lower(), {})
        rto_h = base.get("rto_h") if base.get("rto_h") is not None else (
            q.get("rto_horas") or global_rto
        )
        rpo_h = base.get("rpo_h") if base.get("rpo_h") is not None else (
            q.get("rpo_horas") or global_rpo
        )
        criticidad = (
            q.get("criticidad") or base.get("criticidad")
            or _criticidad_from_rto(rto_h)
        )
        daily = base.get("daily") if base.get("daily") is not None else global_daily
        return {
            "nombre": nombre,
            "area": q.get("area") or base.get("area") or "Operaciones",
            "criticidad": criticidad,
            "responsable": q.get("responsable") or base.get("responsable") or "Responsable funcional",
            "descripcion": q.get("descripcion") or base.get("descripcion")
            or f"Proceso de negocio «{nombre}» dentro del alcance del SGSI.",
            "rto_h": rto_h,
            "rpo_h": rpo_h,
            "rto": _fmt_horas(rto_h),
            "rpo": _fmt_horas(rpo_h),
            "mtpd": _fmt_horas(rto_h * 2 if rto_h else None),
            "mbco": "Prestación mínima de funciones esenciales del proceso",
            "daily": daily,
            "recursos": base.get("recursos", []),
            "dependencias_externas": base.get("dependencias_externas", []),
        }

    if bia_rows:
        for b in bia_rows:
            recursos = []
            for k, v in (b.minimum_resources or {}).items():
                recursos.append({"tipo": str(k).capitalize(), "descripcion": str(v)})
            procesos.append(_enrich(b.service_name, {
                "rto_h": b.rto_hours, "rpo_h": b.rpo_hours,
                "daily": b.daily_impact_eur, "recursos": recursos,
                "dependencias_externas": list(b.stakeholders or []),
            }))
    elif quest_procs:
        for nombre, q in quest_procs.items():
            procesos.append(_enrich(q.get("nombre", nombre), {}))
    else:
        # Fallback m01: servicios finalistas del sistema (no deja el BIA vacío).
        svc_rows = list((await db.execute(
            select(Service).join(System, System.id == Service.system_id)
            .where(System.project_id == project_id)
            .order_by(Service.nombre)
        )).scalars().all())
        for s in svc_rows:
            if s.tipo == "instrumental":
                continue
            procesos.append(_enrich(s.nombre, {
                "descripcion": f"Servicio finalista «{s.nombre}» del sistema.",
            }))

    for p in procesos:
        p["impacto"] = _impacto_matrix(p["criticidad"], p.get("daily"))
        p.pop("daily", None)  # Decimal interno · fuera del contexto JSON-serializable
    return procesos


async def _base_context(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Bloque base cliente/proyecto que los E-400/E-401/E-403 exigen.

    El contexto de gobernanza (merge universal) NO aporta nif/domicilio_social;
    los entregables los exigen ``required``. Se leen de clients (cif→nif,
    domicilio_fiscal→domicilio_social). Mirror de build_informe_final_context.
    """
    row = (await db.execute(sa_text(
        "SELECT COALESCE(c.nombre,'Cliente'), COALESCE(c.cif,''), "
        "       COALESCE(c.domicilio_fiscal,''), COALESCE(p.nombre,'Sistema'), "
        "       p.categoria_objetivo "
        "FROM projects p LEFT JOIN clients c ON c.id = p.client_id "
        "WHERE p.id = :p"
    ), {"p": str(project_id)})).first()
    razon, cif, dom, sistema, cat = (
        row if row is not None else ("Cliente", "", "", "Sistema", None)
    )
    return {
        "cliente": {
            "razon_social": razon,
            "nif": cif or "(NIF pendiente)",
            "domicilio_social": dom or "(domicilio pendiente)",
            "organo_aprobador_politicas": "la Dirección de la entidad",
        },
        "proyecto": {
            "version_actual": "1.0",
            "codigo_documento_base": "ENS",
            "sistema_principal": sistema,
            "alcance": f"el sistema de información «{sistema}»",
            "fecha_aprobacion_inicial": date.today().isoformat(),
            "categoria_ens": cat,
        },
    }


async def _sites(db: AsyncSession, project_id: uuid.UUID) -> list[SystemSite]:
    return list((await db.execute(
        select(SystemSite).join(System, System.id == SystemSite.system_id)
        .where(System.project_id == project_id, SystemSite.deleted_at.is_(None))
        .order_by(SystemSite.nombre)
    )).scalars().all())


async def _providers(db: AsyncSession, project_id: uuid.UUID) -> list[Provider]:
    return list((await db.execute(
        select(Provider).where(
            Provider.project_id == project_id,
            Provider.deleted_at.is_(None),
            Provider.criticality.in_(("CRITICO", "ALTO")),
        ).order_by(Provider.criticality, Provider.name)
    )).scalars().all())


def _site_direccion(s: SystemSite) -> str:
    if s.tipo == "region_cloud":
        return f"Región cloud{(' ' + s.pais) if s.pais else ''}".strip()
    parts = [p for p in [s.direccion, s.pais] if p]
    return ", ".join(parts) if parts else _PENDIENTE


async def build_bia_context(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Contexto BIA E-400 (``bia.*``)."""
    procesos = await _collect_processes(db, project_id)
    providers = await _providers(db, project_id)
    sites = await _sites(db, project_id)
    proc_names = ", ".join(p["nombre"] for p in procesos[:3]) or "los procesos críticos"

    proveedores = [{
        "nombre": pr.name, "servicio": pr.scope or pr.type,
        "procesos": proc_names, "plan_b": "Contrato de respaldo o proveedor alternativo",
    } for pr in providers]

    aplicaciones = [{
        "nombre": p["nombre"], "funcion": p["descripcion"][:80],
        "rto": p["rto"], "rpo": p["rpo"],
    } for p in procesos]

    escenarios = [
        {"descripcion": "Fallo de hardware / infraestructura del sitio primario", "probabilidad": "Media", "impacto": "Alto"},
        {"descripcion": "Ciberataque (ransomware / indisponibilidad)", "probabilidad": "Media", "impacto": "Crítico"},
        {"descripcion": "Indisponibilidad de proveedor cloud crítico", "probabilidad": "Baja", "impacto": "Alto"},
        {"descripcion": "Desastre físico en la ubicación primaria", "probabilidad": "Baja", "impacto": "Crítico"},
    ]
    bia = {
        "procesos": procesos,
        "personal_clave": [{
            "rol": "Responsable de Seguridad (RSEG)",
            "procesos": proc_names,
            "suplencia": "Responsable de Sistemas (RSIS)",
        }, {
            "rol": "Responsable de Sistemas (RSIS)",
            "procesos": proc_names,
            "suplencia": "Equipo técnico TIC",
        }],
        "infraestructura_critica": [{
            "nombre": (s.nombre + (" (" + s.tipo + ")" if s.tipo else "")),
            "procesos": proc_names,
            "rto": _fmt_horas(min((p["rto_h"] for p in procesos if p["rto_h"]), default=None)),
        } for s in sites] or [{
            "nombre": "Infraestructura del sistema (sede/cloud por determinar)",
            "procesos": proc_names, "rto": _PENDIENTE,
        }],
        "aplicaciones_criticas": aplicaciones,
        "proveedores_criticos": proveedores,
        "escenarios": escenarios,
        "escenarios_prioritarios": [{
            "titulo": "Ciberataque con indisponibilidad de sistemas",
            "descripcion": "Cifrado/indisponibilidad de sistemas críticos por ransomware.",
            "procesos_afectados": proc_names,
            "recursos_comprometidos": "Sistemas, datos y copias en línea",
            "estrategia": "Aislamiento + restauración desde copias offline (E-106) en sitio alterno",
        }],
        "dependencias_internas": [
            "Disponibilidad del personal técnico clave",
            "Integridad de las copias de seguridad (E-106)",
            "Operatividad de la red interna y los sistemas de autenticación",
        ],
        "dependencias_externas": [
            (f"{pr.name} ({pr.type})") for pr in providers
        ] or ["Proveedores TIC críticos (por inventariar)"],
        "spofs": [{
            "nombre": "Autenticación / directorio",
            "descripcion": "Indisponibilidad del sistema de identidad bloquearía el acceso.",
            "mitigacion": "Redundancia del directorio + procedimiento de acceso de emergencia.",
        }, {
            "nombre": "Copias de seguridad",
            "descripcion": "Una copia única o no verificada compromete la recuperación.",
            "mitigacion": "Regla 3-2-1 + pruebas de restauración trimestrales (E-405).",
        }],
        "version": "1.0",
        "fecha_emision": date.today().isoformat(),
        "fecha_aprobacion": "(pendiente de aprobación por el Comité de Seguridad)",
        "proxima_revision": (date.today() + timedelta(days=365)).isoformat(),
        "elaborado_por": "el equipo de Fulkro (consultoría ENS)",
        "conclusiones": (
            f"El análisis identifica {len(procesos)} proceso(s) crítico(s) cuya "
            "interrupción comprometería la prestación del servicio. Los objetivos "
            "RTO/RPO definidos son la base del Plan de Continuidad (E-401) y del "
            "Plan de Recuperación de Desastres (E-403)."
        ),
        "recomendaciones": [
            "Mantener y probar periódicamente las estrategias de continuidad por proceso.",
            "Verificar trimestralmente la restauración desde copias de seguridad (E-405).",
            "Revisar el BIA ante cualquier cambio material en procesos o proveedores.",
        ],
        "inversiones_recomendadas": [{
            "descripcion": "Infraestructura de respaldo / sitio alterno",
            "justificacion": "Cumplir el RTO de los procesos críticos.",
            "coste": "Según plan económico aprobado",
            "prioridad": "Alta",
        }, {
            "descripcion": "Programa de pruebas de continuidad (E-405/E-406)",
            "justificacion": "Validar la eficacia real de las estrategias (op.cont.3).",
            "coste": "Según plan económico aprobado",
            "prioridad": "Media",
        }],
    }
    return {**(await _base_context(db, project_id)), "bia": bia}


async def build_continuity_context(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Contexto Estrategias de Continuidad E-401."""
    procesos = await _collect_processes(db, project_id)
    sites = await _sites(db, project_id)
    providers = await _providers(db, project_id)

    procesos_criticos = [{
        "nombre": p["nombre"], "rto": p["rto"], "rpo": p["rpo"],
        "criticidad": p["criticidad"], "descripcion": p["descripcion"],
    } for p in procesos]

    estrategias = [{
        "proceso": p["nombre"],
        "estrategia": _estrategia_from_rto(p["rto_h"]),
        "coste_estimado": "Según plan económico aprobado",
        "responsable": "Responsable de Sistemas (RSIS)",
        "plazo": p["rto"],
    } for p in procesos]

    ubicaciones_alternas = [{
        "nombre": s.nombre,
        "direccion": _site_direccion(s),
        "capacidad": "Total" if s.tipo == "region_cloud" else "Parcial/Total",
        "tiempo_activacion": "Inmediata (cloud)" if s.tipo == "region_cloud" else "Según plan de activación",
    } for s in sites]

    proveedores_criticos = [{
        "nombre": pr.name, "tipo_servicio": pr.type,
        "sla": "Según contrato de nivel de servicio",
        "contacto_emergencia": "Según contrato (24/7 para proveedores críticos)",
    } for pr in providers]

    return {
        **(await _base_context(db, project_id)),
        "procesos_criticos": procesos_criticos,
        "estrategias": estrategias,
        "ubicaciones_alternas": ubicaciones_alternas,
        "proveedores_criticos": proveedores_criticos,
    }


async def build_drp_context(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Contexto DRP E-403 (``sistemas_criticos`` + ``ubicaciones``)."""
    procesos = await _collect_processes(db, project_id)
    sites = await _sites(db, project_id)

    sistemas_criticos = [{
        "nombre": p["nombre"],
        "funcion": p["descripcion"][:80],
        "rto": p["rto"], "rpo": p["rpo"],
        "mecanismo": _mecanismo_from_rto(p["rto_h"]),
    } for p in procesos]

    sede = next((s for s in sites if s.tipo == "sede_fisica"), None)
    cloud = next((s for s in sites if s.tipo == "region_cloud"), None)
    otros = [s for s in sites if s not in (sede, cloud)]
    primario = sede or (sites[0] if sites else None)
    secundario = cloud or (otros[0] if otros else None)

    ubicaciones = {
        "primario": {
            "nombre": primario.nombre if primario else "Sitio primario",
            "direccion": _site_direccion(primario) if primario else _PENDIENTE,
        },
        "secundario": {
            "nombre": secundario.nombre if secundario else "Sitio secundario",
            "direccion": _site_direccion(secundario) if secundario else _PENDIENTE,
            "modalidad": "hot" if (secundario and secundario.tipo == "region_cloud") else "warm",
            "tiempo_activacion": "Inmediata (cloud)" if (secundario and secundario.tipo == "region_cloud") else "Según plan de activación",
        },
    }
    return {
        **(await _base_context(db, project_id)),
        "sistemas_criticos": sistemas_criticos,
        "ubicaciones": ubicaciones,
    }
