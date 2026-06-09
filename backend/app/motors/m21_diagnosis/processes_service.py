"""M21 Paso 5 — Business processes (Agente 23).

Inventario de procesos de negocio por sector, con:
- Templates precargados (6 sectores × 10-15 procesos tipicos)
- Persistencia en tabla ``business_processes``
- Feed automatico a BIA (Business Impact Analysis) de M6
- Deteccion de dependencias upstream/downstream

Tabla ``business_processes`` (model ya existente):
- nombre, descripcion, criticidad (alta/media/baja)
- propietario, dependencias JSONB
- sistemas_involucrados JSONB
- rto_horas, rpo_horas
- bpmn_mermaid

Este servicio anade:
- load_sector_template(sector) → lista de procesos tipo
- seed_sector_processes(project_id, sector) → persiste los templates
- feed_bia(project_id) → estructura para M6 E-400 BIA
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import BusinessProcess


# ════════════════════════════════════════════════════════════════════
# Sector process templates
# ════════════════════════════════════════════════════════════════════
#
# Cada sector trae 10-15 procesos tipicos con criticidad, RTO/RPO, y
# categoria (core_business / support / compliance). Son valores base
# razonables; el consultor los ajusta durante la reunion exploratoria.

@dataclass
class ProcessTemplate:
    nombre: str
    criticidad: str                          # alta | media | baja
    descripcion: str = ""
    categoria: str = "core_business"         # core_business | support | compliance
    rto_horas: int = 24
    rpo_horas: int = 4
    sistemas_soportan: list[str] = field(default_factory=list)
    frecuencia_ejecucion: str = "diaria"
    volumen_anual: str = "alto"


SECTOR_TEMPLATES: dict[str, list[ProcessTemplate]] = {
    "sanidad_privada": [
        ProcessTemplate(
            nombre="Gestion de historia clinica electronica",
            descripcion="Consulta, actualizacion y almacenamiento de historial medico de pacientes.",
            criticidad="alta", categoria="core_business",
            rto_horas=4, rpo_horas=1,
            sistemas_soportan=["HIS", "EHR", "Almacen documental"],
        ),
        ProcessTemplate(
            nombre="Cita medica y agenda", criticidad="alta",
            descripcion="Alta/modificacion/cancelacion de citas presenciales y telematicas.",
            categoria="core_business", rto_horas=8, rpo_horas=2,
            sistemas_soportan=["PMS", "Portal paciente", "Call center"],
        ),
        ProcessTemplate(
            nombre="Atencion de urgencias", criticidad="alta",
            descripcion="Triaje, admision y asistencia en servicios de urgencias.",
            categoria="core_business", rto_horas=1, rpo_horas=0,
            sistemas_soportan=["HIS", "Monitorizacion clinica"],
        ),
        ProcessTemplate(
            nombre="Prescripcion electronica de medicamentos", criticidad="alta",
            descripcion="Emision de recetas electronicas integradas con farmacias.",
            categoria="core_business", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["HIS", "Receta electronica"],
        ),
        ProcessTemplate(
            nombre="Facturacion a aseguradoras", criticidad="media",
            descripcion="Liquidacion mensual con aseguradoras privadas y Muface.",
            categoria="support", rto_horas=72, rpo_horas=24,
            sistemas_soportan=["ERP financiero"],
        ),
        ProcessTemplate(
            nombre="Pruebas diagnosticas (RX, analitica)", criticidad="alta",
            descripcion="Solicitud, realizacion y entrega de resultados diagnosticos.",
            categoria="core_business", rto_horas=8, rpo_horas=4,
            sistemas_soportan=["RIS", "LIS", "PACS"],
        ),
        ProcessTemplate(
            nombre="Consentimiento informado digital", criticidad="media",
            categoria="compliance",
            descripcion="Captacion, firma y custodia de consentimientos (RGPD).",
            rto_horas=24, rpo_horas=8, sistemas_soportan=["Portal paciente"],
        ),
        ProcessTemplate(
            nombre="Notificacion de brechas (AEPD)", criticidad="alta",
            categoria="compliance",
            descripcion="Detectar + notificar brechas a la AEPD en 72h.",
            rto_horas=2, rpo_horas=1, sistemas_soportan=["SIEM", "Portal AEPD"],
            frecuencia_ejecucion="ad-hoc",
        ),
        ProcessTemplate(
            nombre="Onboarding personal clinico", criticidad="media",
            categoria="support",
            descripcion="Alta, formacion LOPDGDD + secreto profesional.",
            rto_horas=120, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Gestion de proveedores clinicos", criticidad="media",
            categoria="support",
            descripcion="Seleccion, evaluacion y renovacion de proveedores.",
            rto_horas=168, rpo_horas=24,
        ),
    ],
    "fintech": [
        ProcessTemplate(
            nombre="Onboarding de cliente (KYC)", criticidad="alta",
            descripcion="Verificacion de identidad, AML, riesgo.",
            categoria="core_business", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["CRM", "AML", "ID-proofing"],
        ),
        ProcessTemplate(
            nombre="Concesion de credito", criticidad="alta",
            descripcion="Scoring, aprobacion y activacion del producto crediticio.",
            categoria="core_business", rto_horas=8, rpo_horas=2,
        ),
        ProcessTemplate(
            nombre="Procesamiento de transacciones", criticidad="alta",
            descripcion="Autorizacion y liquidacion de pagos.",
            categoria="core_business", rto_horas=1, rpo_horas=0,
            sistemas_soportan=["Core bancario", "SEPA", "Card scheme"],
        ),
        ProcessTemplate(
            nombre="Conciliacion y liquidacion", criticidad="alta",
            descripcion="Cuadre diario de posiciones.",
            categoria="core_business", rto_horas=4, rpo_horas=1,
        ),
        ProcessTemplate(
            nombre="Reporting regulatorio", criticidad="alta",
            categoria="compliance",
            descripcion="Banco de Espana, CNMV, SEPBLAC.",
            rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Prevencion del fraude", criticidad="alta",
            descripcion="Monitorizacion online + reglas + ML.",
            categoria="core_business", rto_horas=1, rpo_horas=0,
            sistemas_soportan=["Antifraude", "SIEM"],
        ),
        ProcessTemplate(
            nombre="Soporte al cliente (atencion canales)", criticidad="media",
            categoria="support", rto_horas=8, rpo_horas=2,
            descripcion="Contact center, chat, email.",
        ),
        ProcessTemplate(
            nombre="Gestion de incidentes DORA", criticidad="alta",
            categoria="compliance", rto_horas=2, rpo_horas=1,
            descripcion="Clasificacion y notificacion a autoridad en plazos DORA.",
        ),
        ProcessTemplate(
            nombre="Gestion de proveedores TIC criticos (DORA)", criticidad="alta",
            categoria="compliance",
            descripcion="Due diligence + contratos ICT + registro DORA.",
            rto_horas=168, rpo_horas=48,
        ),
        ProcessTemplate(
            nombre="Facturacion interna", criticidad="media",
            categoria="support", rto_horas=72, rpo_horas=24,
        ),
    ],
    "servicios_profesionales": [
        ProcessTemplate(
            nombre="Onboarding de empleado", criticidad="media",
            categoria="support", rto_horas=72, rpo_horas=24,
            descripcion="Alta en sistemas, formacion, entrega equipos.",
        ),
        ProcessTemplate(
            nombre="Gestion de proyectos cliente", criticidad="alta",
            categoria="core_business", rto_horas=8, rpo_horas=4,
            sistemas_soportan=["PMS", "CRM", "ERP"],
        ),
        ProcessTemplate(
            nombre="Facturacion al cliente", criticidad="alta",
            categoria="support", rto_horas=48, rpo_horas=8,
            descripcion="Emision de facturas y seguimiento de cobro.",
        ),
        ProcessTemplate(
            nombre="Soporte y mantenimiento al cliente", criticidad="media",
            categoria="core_business", rto_horas=8, rpo_horas=2,
        ),
        ProcessTemplate(
            nombre="Ventas y comercial", criticidad="media",
            categoria="core_business", rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Gestion documental de proyectos", criticidad="media",
            categoria="support",
            descripcion="Entregables y firmas digitales con clientes.",
            rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Compras y aprovisionamiento", criticidad="baja",
            categoria="support", rto_horas=168, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Reporting financiero y fiscal", criticidad="alta",
            categoria="compliance", rto_horas=72, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Seguridad de la informacion (SGSI)", criticidad="alta",
            categoria="compliance", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["SIEM", "IAM"],
        ),
        ProcessTemplate(
            nombre="Gestion de proveedores", criticidad="media",
            categoria="support", rto_horas=168, rpo_horas=48,
        ),
    ],
    "industria": [
        ProcessTemplate(
            nombre="Planificacion de la produccion", criticidad="alta",
            categoria="core_business", rto_horas=8, rpo_horas=2,
            sistemas_soportan=["MES", "ERP"],
        ),
        ProcessTemplate(
            nombre="Ejecucion de la produccion (linea)", criticidad="alta",
            categoria="core_business", rto_horas=2, rpo_horas=0,
            sistemas_soportan=["MES", "SCADA"],
        ),
        ProcessTemplate(
            nombre="Logistica y expediciones", criticidad="alta",
            categoria="core_business", rto_horas=8, rpo_horas=2,
            sistemas_soportan=["WMS", "TMS"],
        ),
        ProcessTemplate(
            nombre="Control de calidad", criticidad="alta",
            categoria="core_business", rto_horas=4, rpo_horas=1,
        ),
        ProcessTemplate(
            nombre="Mantenimiento preventivo/correctivo", criticidad="alta",
            categoria="support", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["CMMS"],
        ),
        ProcessTemplate(
            nombre="Compras de materias primas", criticidad="media",
            categoria="support", rto_horas=48, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Salud y seguridad laboral (PRL)", criticidad="alta",
            categoria="compliance", rto_horas=8, rpo_horas=2,
        ),
        ProcessTemplate(
            nombre="Gestion medioambiental", criticidad="media",
            categoria="compliance", rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Facturacion B2B", criticidad="media",
            categoria="support", rto_horas=48, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="I+D+i industrial", criticidad="baja",
            categoria="support", rto_horas=168, rpo_horas=24,
        ),
    ],
    "educacion_privada": [
        ProcessTemplate(
            nombre="Matricula de alumnos", criticidad="alta",
            categoria="core_business", rto_horas=24, rpo_horas=4,
        ),
        ProcessTemplate(
            nombre="Gestion de calificaciones", criticidad="alta",
            categoria="core_business", rto_horas=8, rpo_horas=2,
        ),
        ProcessTemplate(
            nombre="Expediente academico", criticidad="alta",
            categoria="core_business", rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Facturacion de matriculas", criticidad="media",
            categoria="support", rto_horas=48, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Gestion de becas", criticidad="media",
            categoria="compliance", rto_horas=72, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Protección de menores", criticidad="alta",
            categoria="compliance", rto_horas=4, rpo_horas=1,
            descripcion="Controles LOPIVI + formacion + canal etico.",
        ),
        ProcessTemplate(
            nombre="Plataforma e-learning", criticidad="alta",
            categoria="core_business", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["LMS"],
        ),
        ProcessTemplate(
            nombre="Gestion docente (altas/bajas)", criticidad="media",
            categoria="support", rto_horas=72, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Comunicacion con familias", criticidad="media",
            categoria="core_business", rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Informes regulatorios a Consejeria", criticidad="alta",
            categoria="compliance", rto_horas=72, rpo_horas=24,
        ),
    ],
    "administracion_publica": [
        ProcessTemplate(
            nombre="Registro de entrada/salida", criticidad="alta",
            categoria="core_business", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["SIR", "ORVE"],
        ),
        ProcessTemplate(
            nombre="Tramitacion de expedientes", criticidad="alta",
            categoria="core_business", rto_horas=8, rpo_horas=2,
        ),
        ProcessTemplate(
            nombre="Resolucion administrativa", criticidad="alta",
            categoria="core_business", rto_horas=24, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Notificacion electronica", criticidad="alta",
            categoria="compliance", rto_horas=8, rpo_horas=2,
            sistemas_soportan=["Notifica", "DEH"],
        ),
        ProcessTemplate(
            nombre="Recaudacion de tasas", criticidad="alta",
            categoria="support", rto_horas=48, rpo_horas=8,
        ),
        ProcessTemplate(
            nombre="Contratacion publica", criticidad="alta",
            categoria="compliance", rto_horas=168, rpo_horas=24,
            sistemas_soportan=["PLACSP"],
        ),
        ProcessTemplate(
            nombre="Transparencia y publicidad activa", criticidad="media",
            categoria="compliance", rto_horas=48, rpo_horas=24,
        ),
        ProcessTemplate(
            nombre="Atencion al ciudadano", criticidad="alta",
            categoria="core_business", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["Sede electronica"],
        ),
        ProcessTemplate(
            nombre="Gestion de identidad (certificados)", criticidad="alta",
            categoria="compliance", rto_horas=4, rpo_horas=1,
            sistemas_soportan=["Cl@ve", "FNMT"],
        ),
        ProcessTemplate(
            nombre="Interoperabilidad (ENI)", criticidad="alta",
            categoria="compliance", rto_horas=24, rpo_horas=8,
        ),
    ],
}

# Alias sectores
SECTOR_ALIASES = {
    "sanidad": "sanidad_privada",
    "financiero": "fintech",
    "servicios": "servicios_profesionales",
    "industrial": "industria",
    "educacion": "educacion_privada",
    "administracion": "administracion_publica",
    "sector_publico": "administracion_publica",
}


def load_sector_template(sector: str) -> list[ProcessTemplate]:
    """Devuelve los procesos tipo para un sector. Lanza KeyError si no existe."""
    key = SECTOR_ALIASES.get(sector.lower(), sector.lower())
    if key not in SECTOR_TEMPLATES:
        raise KeyError(
            f"Sector '{sector}' no reconocido. Validos: "
            f"{sorted(SECTOR_TEMPLATES.keys())}",
        )
    return SECTOR_TEMPLATES[key]


# ════════════════════════════════════════════════════════════════════
# Seed + BIA feed
# ════════════════════════════════════════════════════════════════════

async def seed_sector_processes(
    db: AsyncSession, project_id: uuid.UUID, sector: str,
    *, skip_existing: bool = True,
) -> list[BusinessProcess]:
    """Persiste los procesos del sector como rows en ``business_processes``.

    Si ``skip_existing=True`` (default), salta nombres ya presentes.
    """
    templates = load_sector_template(sector)
    existing = set()
    if skip_existing:
        stmt = select(BusinessProcess.nombre).where(
            BusinessProcess.project_id == project_id,
            BusinessProcess.deleted_at.is_(None),
        )
        existing = {r[0] for r in (await db.execute(stmt)).all()}

    created: list[BusinessProcess] = []
    for t in templates:
        if t.nombre in existing:
            continue
        bp = BusinessProcess(
            project_id=project_id,
            nombre=t.nombre,
            descripcion=t.descripcion,
            criticidad=t.criticidad,
            rto_horas=t.rto_horas,
            rpo_horas=t.rpo_horas,
            sistemas_involucrados={
                "sistemas": t.sistemas_soportan,
                "frecuencia": t.frecuencia_ejecucion,
                "volumen_anual": t.volumen_anual,
            },
            dependencias={
                "categoria": t.categoria,
                "upstream": [],
                "downstream": [],
            },
        )
        db.add(bp)
        created.append(bp)
    await db.flush()
    return created


async def list_processes(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[BusinessProcess]:
    stmt = select(BusinessProcess).where(
        BusinessProcess.project_id == project_id,
        BusinessProcess.deleted_at.is_(None),
    )
    return list((await db.execute(stmt)).scalars().all())


async def feed_bia(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Devuelve estructura lista para generar el BIA (E-400) con M6.

    Agrupa procesos por criticidad, calcula RTO/RPO objetivos maximos,
    y propone el perfil de continuidad del sistema.
    """
    processes = await list_processes(db, project_id)
    by_criticidad: dict[str, list[dict[str, Any]]] = {
        "alta": [], "media": [], "baja": [],
    }
    worst_rto = 0
    worst_rpo = 0
    for p in processes:
        sistemas = (p.sistemas_involucrados or {}).get("sistemas", [])
        categoria = (p.dependencias or {}).get("categoria", "core_business")
        row = {
            "id": str(p.id),
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "criticidad": p.criticidad or "media",
            "propietario": p.propietario,
            "rto_horas": p.rto_horas,
            "rpo_horas": p.rpo_horas,
            "sistemas": sistemas,
            "categoria": categoria,
        }
        by_criticidad.setdefault(
            (p.criticidad or "media").lower(), [],
        ).append(row)
        if (p.rto_horas or 0) > worst_rto:
            worst_rto = p.rto_horas or 0
        if (p.rpo_horas or 0) > worst_rpo:
            worst_rpo = p.rpo_horas or 0

    # Procesos core_business criticos son los que marcan el RTO/RPO
    # objetivo del sistema. Tomamos el menor RTO de los criticos.
    core_criticos = [
        r for r in by_criticidad["alta"]
        if r["categoria"] == "core_business"
    ]
    if core_criticos:
        objective_rto = min(r["rto_horas"] or 24 for r in core_criticos)
        objective_rpo = min(r["rpo_horas"] or 4 for r in core_criticos)
    else:
        objective_rto = 24
        objective_rpo = 4

    return {
        "total_procesos": len(processes),
        "por_criticidad": by_criticidad,
        "core_business_criticos": core_criticos,
        "rto_objetivo_horas": objective_rto,
        "rpo_objetivo_horas": objective_rpo,
        "peor_rto_horas": worst_rto,
        "peor_rpo_horas": worst_rpo,
        "recomendacion": (
            "alta_disponibilidad" if objective_rto <= 4
            else "continuidad_estandar" if objective_rto <= 24
            else "continuidad_basica"
        ),
    }


__all__ = [
    "ProcessTemplate",
    "SECTOR_TEMPLATES",
    "SECTOR_ALIASES",
    "feed_bia",
    "list_processes",
    "load_sector_template",
    "seed_sector_processes",
]
