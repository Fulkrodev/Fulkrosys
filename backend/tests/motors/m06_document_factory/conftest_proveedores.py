"""Fixture sintetico `cliente_con_proveedores` · sub-lote 1.B.7.1.0 (AMEND-014).

Provee 3 proveedores representativos del target FULKRO (empresa privada
licitando · AMEND-012) + 1 assessment ejemplo (E-602) + 1 addendum ejemplo
(E-604) listos para tests render E-600 a E-604 y para `smoke_render_plantillas_demo`.

Naming patron: NO `conftest.py` (no auto-discovery global pytest). Los tests
que necesiten el fixture lo IMPORTAN explicitamente:

    from backend.tests.motors.m06_document_factory.conftest_proveedores import (
        cliente_con_proveedores,
        PROVEEDORES_SINTETICOS,
    )

Reglas duras (LECCION-OPS-021):
- NO INSERT real en BD en este modulo a nivel import · todo dentro de fixture
- _admin_setup(db) usado para INSERTs RLS-protegidos
- RESET ROLE antes de assertions SUT
- Tenant context (current_project_id + current_client_id) set tras _admin_setup
"""
from __future__ import annotations

import json
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.conftest import _admin_setup


# ---------------------------------------------------------------------------
# Datos sinteticos (importables sin DB · usables desde smoke_render_*)
# ---------------------------------------------------------------------------

PROVEEDORES_SINTETICOS: list[dict] = [
    {
        "name": "CloudHost Iberia S.L.",
        "type": "cloud",
        "scope": (
            "Hosting cloud productivo (compute + storage + red) · region eu-west "
            "Madrid · IaaS multi-tenant con tenant FULKRO aislado."
        ),
        "criticality": "CRITICO",
        "normativas_aplicables": ["ENS", "RGPD", "NIS2"],
        "notes": (
            "Proveedor cloud nivel CRITICO · activa C-002 (ENS Art.18 + RGPD "
            "Art.28 + NIS2 Art.21 segun providers_service.detect_cross_compliance_gaps)."
        ),
    },
    {
        "name": "SaaS-CRM Solutions",
        "type": "saas",
        "scope": (
            "Plataforma SaaS CRM comercial · datos personales clientes B2B · "
            "integracion via API REST con backoffice."
        ),
        "criticality": "ALTO",
        "normativas_aplicables": ["RGPD", "NIS2"],
        "notes": (
            "Proveedor SaaS ALTO · activa C-002 (ENS Art.18 + RGPD Art.28) "
            "sin NIS2 Art.21 (regla cloud+CRITICO no se cumple)."
        ),
    },
    {
        "name": "Consultoria Cumplimiento Norte",
        "type": "consultoria",
        "scope": (
            "Servicios consultivos de cumplimiento ENS/RGPD · acceso "
            "ocasional a documentacion interna del SGSI bajo NDA."
        ),
        "criticality": "MEDIO",
        "normativas_aplicables": ["RGPD"],
        "notes": (
            "Proveedor consultoria MEDIO · NO activa C-002 (regla "
            "cloud/saas+CRITICO/ALTO no se cumple) · sin gaps cross-compliance."
        ),
    },
]


ASSESSMENT_SINTETICO: dict = {
    "assessment_date": date(2026, 5, 15),
    "assessor": "Marcos Mata (consultor externo FULKRO)",
    "questionnaire_version": "v1.0",
    "responses": {
        "identificacion": {
            "denominacion_social": "CloudHost Iberia S.L.",
            "cif": "B12345678",
            "domicilio": "Calle Gran Via 1, 28013 Madrid",
        },
        "ens_art31": {
            "tiene_ens_propio": True,
            "categoria_ens": "ALTA",
            "ultima_auditoria": "2025-11-12",
            "auditor_acreditado_enac": "AENOR",
        },
        "rgpd_art28": {
            "es_encargado_tratamiento": True,
            "subencargados_declarados": True,
            "ubicacion_datos": "UE (Madrid + Frankfurt)",
            "registros_actividad_disponibles": True,
        },
        "nis2_art21": {
            "esta_dentro_ambito": True,
            "tipo_entidad": "esencial",
            "notificacion_24h_acreditada": True,
        },
        "capacidades_tecnicas": {
            "iso_27001": True,
            "soc2_type2": True,
            "pci_dss": False,
        },
    },
    "risk_score": 0.18,  # bajo (proveedor maduro)
    "risk_level": "BAJO",
    "decision": "APROBADO",
    "decision_rationale": (
        "Proveedor maduro · ENS ALTA + ISO 27001 + SOC2 + auditoria reciente. "
        "Aprobado sin condiciones · valido hasta proxima revision anual."
    ),
    "valid_until": date(2027, 5, 15),
}


ASSESSMENT_FULL: dict = {
    # Superset del ASSESSMENT_SINTETICO arriba · campos extra para render E-602
    # (Informe Evaluacion). Mantenemos ASSESSMENT_SINTETICO sin tocar para no
    # romper consumidores 1.B.7.1.0; este FULL es para E-602/E-603 specifics.
    "id": "assessment-cloudhost-2026-001",
    "fecha_cuestionario": date(2026, 5, 10),
    "fecha_decision": date(2026, 5, 15),
    "evaluador": {
        "nombre": "Marcos Mata Garcia",
        "cargo": "Consultor independiente en ENS",
    },
    "aplica_nis2": True,
    "aplica_dora": False,
    "dimension_b": {
        "descripcion": (
            "El proveedor aporta Declaracion de Conformidad ENS ALTA vigente "
            "emitida por AENOR en noviembre 2025 + ISO 27001 alcance completo "
            "del servicio + SOC 2 Type II del periodo cerrado."
        ),
        "evidencias": [
            "Declaracion ENS ALTA AENOR (Anexo B.1)",
            "Certificado ISO 27001 alcance Cloud Hosting (Anexo B.1.d)",
            "SOC 2 Type II reporte 2025 (Anexo B.1.d)",
        ],
        "conclusion": "Conforme ENS ALTA · equivalencia clara con categoria ALTA cliente",
    },
    "dimension_c": {
        "descripcion": (
            "Encargado de tratamiento RGPD Art.28 con contrato modelo aportado. "
            "Subencargados declarados (4 entidades) todos en EEE. Sin transferencias "
            "internacionales fuera EEE."
        ),
        "categorias_datos": ["Identificativos", "Contacto profesional", "Trafico"],
        "transferencias": "Ninguna fuera EEE (UE-Madrid + UE-Frankfurt)",
        "conclusion": "Contrato encargado tratamiento RGPD Art.28 firmara como anexo E-604",
    },
    "dimension_d": {
        "descripcion": (
            "Proveedor inscrito en registro nacional NIS2 como entidad esencial "
            "(sector infraestructura digital)."
        ),
        "conclusion": "Cumplimiento NIS2 Art.21 acreditado · notificacion 24h aceptada",
    },
    "dimension_f": {
        "conclusion": "Capacidades tecnicas solidas · personal acreditado SC-300/SC-200 + ISO 27001 LA",
    },
    "certificaciones_vigentes": [
        "ENS ALTA (AENOR · noviembre 2025)",
        "ISO/IEC 27001:2022 (alcance Cloud Hosting)",
        "ISO/IEC 27017 (cloud-specific controls)",
        "ISO/IEC 27018 (PII processors in cloud)",
        "SOC 2 Type II (2025)",
    ],
    "rto_horas": 4,
    "rpo_horas": 1,
    "bcp_aportado": True,
    "acepta_salida_30d": True,
    "notificacion_horas": 24,
    "colabora_ines": True,
    "hallazgos_positivos": [
        "Conformidad ENS ALTA directa · alineada con categoria cliente",
        "Suite ISO 27001+27017+27018 completa para cloud",
        "RTO 4h dentro umbral CRITICO (cliente exige <= 4h para CRITICO)",
        "BCP documentado + ejercicios trimestrales acreditados",
    ],
    "hallazgos_criticos": [
        {
            "titulo": "Subencargado no notificado a la Entidad",
            "descripcion": (
                "Se ha identificado un subencargado (CDN provider) no declarado "
                "previamente en cuestionario. Requiere actualizacion declaracion."
            ),
            "severidad": "MEDIA",
        },
    ],
    "scoring_por_seccion": {
        "B · ENS conformidad": 95,
        "C · RGPD Art.28": 88,
        "D · NIS2 Art.21": 92,
        "F · Capacidades tecnicas": 90,
        "G · Continuidad + salida": 94,
        "H · Respuesta incidentes": 90,
    },
    "scoring_total": 91,
    "nivel_criticidad_asignado": "CRITICO",
    "nivel_criticidad_justificacion": (
        "Proveedor hosting cloud productivo de toda la plataforma SaaS · "
        "interrupcion detendria servicios esenciales · trata datos personales "
        "categoria ordinaria pero volumen elevado. Nivel CRITICO conforme "
        "metodologia E-217 seccion 4.2."
    ),
    "decision": "APROBADO",
    "condiciones": [],
    "valid_until": date(2027, 5, 15),
}


PLAN_SUPERVISION_FULL: dict = {
    "periodo_inicio": date(2026, 6, 1),
    "periodo_fin": date(2027, 5, 31),
    "responsable": {
        "nombre": "Marcos Mata Garcia",
        "cargo": "Responsable de Seguridad (CISO interim)",
    },
    "notificacion_horas": 24,
    "revisiones_documentales": [
        {
            "tipo": "Revision recertificaciones (ENS + ISO 27001)",
            "periodicidad": "Anual",
            "proxima_fecha": "2026-12-01",
            "responsable": "Marcos Mata",
        },
        {
            "tipo": "Revision SOC 2 Type II + BCP",
            "periodicidad": "Anual",
            "proxima_fecha": "2026-11-15",
            "responsable": "Sara Tecnica (CTO)",
        },
        {
            "tipo": "Revision registro incidentes proveedor",
            "periodicidad": "Trimestral",
            "proxima_fecha": "2026-08-30",
            "responsable": "Marcos Mata",
        },
    ],
    "documentos_requeridos": [
        "Declaracion Conformidad ENS vigente (renovada)",
        "Certificado ISO 27001 + alcance vigente",
        "Reporte SOC 2 Type II del periodo cerrado",
        "Informe auditoria interna del periodo",
        "Registro incidentes que afectaron al servicio",
        "Cambios declarados en subencargados o transferencias internacionales",
    ],
    "reuniones_operativas": [
        {
            "frecuencia": "Mensual",
            "participantes_entidad": "Marcos Mata (CISO) + Sara Tecnica (CTO)",
            "participantes_proveedor": "Account Manager + Security Officer asignado",
            "agenda": "SLA + incidentes + cambios + roadmap proximo periodo",
        },
        {
            "frecuencia": "Trimestral",
            "participantes_entidad": "Comite Seguridad Informacion",
            "participantes_proveedor": "VP Engineering + Director Compliance",
            "agenda": "Revision estrategica + KPIs ENS + planificacion auditorias",
        },
    ],
    "pruebas_tecnicas": [
        {
            "tipo": "Test penetracion interfaces expuestas",
            "periodicidad": "Anual",
            "coordinacion": "Preaviso 30d · ventana mantenimiento sabado madrugada",
        },
        {
            "tipo": "Escaneo vulnerabilidades activos servicio",
            "periodicidad": "Trimestral",
            "coordinacion": "Reporte mensual sin intrusion + ventana trimestral con coordinacion",
        },
    ],
    "kpis_sla": [
        {
            "nombre": "Disponibilidad mensual",
            "objetivo": ">= 99.9%",
            "umbral_alerta": "< 99.5%",
            "origen": "Monitor uptime proveedor + verificacion checks Entidad",
        },
        {
            "nombre": "Tiempo medio resolucion incidentes graves",
            "objetivo": "<= 4h",
            "umbral_alerta": "> 6h",
            "origen": "Tickets soporte proveedor + correlation logs Entidad",
        },
        {
            "nombre": "Notificacion incidentes graves",
            "objetivo": "<= 24h desde deteccion",
            "umbral_alerta": "> 24h",
            "origen": "Registro notificaciones formales",
        },
    ],
}


ADDENDUM_SINTETICO: dict = {
    "addendum_code": "ADENDA-ENS-2026-001",
    "contract_ref": "CONTRATO-MARCO-2025-CLOUDHOST-001",
    "normativas_cubiertas": ["ENS", "RGPD", "NIS2"],
    "fecha_firma": date(2026, 5, 18),
    "fecha_vigor": date(2026, 6, 1),
    "vencimiento": date(2028, 5, 31),
    "firmado_cliente": True,
    "firmado_proveedor": False,  # pendiente firma contraparte
    "minio_object_key": (
        "fulkro-documents/proyectos/{project_id}/proveedores/"
        "cloudhost-iberia/ADENDA-ENS-2026-001.docx"
    ),
    "generated_from_template_code": "E-604",
    "metadata_": {
        "generador": "adenda_generator_v1",
        "clausulas_incluidas": [
            "C-002.ENS-18",
            "C-002.RGPD-28",
            "C-002.NIS2-21",
        ],
        "idioma": "es-ES",
    },
}


# ---------------------------------------------------------------------------
# Fixture pytest async · INSERT rows en DB (RLS-aware)
# ---------------------------------------------------------------------------

@pytest.fixture
async def cliente_con_proveedores(db: AsyncSession) -> dict:
    """Crea cliente + project + 3 proveedores + 1 assessment + 1 addendum.

    Returns dict con:
        client_id, project_id (strings UUID),
        providers (list dicts: {id, name, type, criticality, normativas_aplicables, ...}),
        assessment (dict columnas + provider_id),
        addendum (dict columnas + provider_id).

    Provider CRITICO (CloudHost Iberia) usado para assessment + addendum sample.
    """
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        # cliente piloto (target FULKRO empresa privada licitando · AMEND-012)
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, sector, numero_empleados, created_at) "
            "VALUES (:id, 'Demo Provider Client SL', :cif, 'fintech', 75, now())"
        ), {"id": str(client_id), "cif": unique_cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Provider Lifecycle Demo Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})

        # 3 proveedores sinteticos
        inserted_providers: list[dict] = []
        for prov in PROVEEDORES_SINTETICOS:
            prov_id = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO providers "
                "(id, project_id, name, type, scope, criticality, created_at) "
                "VALUES (:id, :pid, :name, :type, :scope, :crit, now())"
            ), {
                "id": str(prov_id),
                "pid": str(project_id),
                "name": prov["name"],
                "type": prov["type"],
                "scope": prov["scope"],
                "crit": prov["criticality"],
            })
            inserted_providers.append({"id": str(prov_id), **prov})

        # assessment sample sobre el primer proveedor (CloudHost · CRITICO)
        provider_for_sample = inserted_providers[0]
        assessment_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO provider_assessments "
            "(id, project_id, provider_id, assessment_date, assessor, "
            " questionnaire_version, responses, risk_score, risk_level, "
            " decision, decision_rationale, valid_until, created_at) "
            "VALUES (:id, :pid, :prov, :date, :assessor, :qv, "
            "        CAST(:resp AS jsonb), :rscore, :rlevel, :dec, :rat, :vu, now())"
        ), {
            "id": str(assessment_id),
            "pid": str(project_id),
            "prov": provider_for_sample["id"],
            "date": ASSESSMENT_SINTETICO["assessment_date"],
            "assessor": ASSESSMENT_SINTETICO["assessor"],
            "qv": ASSESSMENT_SINTETICO["questionnaire_version"],
            "resp": json.dumps(ASSESSMENT_SINTETICO["responses"]),
            "rscore": ASSESSMENT_SINTETICO["risk_score"],
            "rlevel": ASSESSMENT_SINTETICO["risk_level"],
            "dec": ASSESSMENT_SINTETICO["decision"],
            "rat": ASSESSMENT_SINTETICO["decision_rationale"],
            "vu": ASSESSMENT_SINTETICO["valid_until"],
        })

        # addendum sample sobre mismo proveedor
        addendum_id = uuid.uuid4()
        minio_key = ADDENDUM_SINTETICO["minio_object_key"].format(project_id=project_id)
        await db.execute(text(
            "INSERT INTO provider_addendums "
            "(id, project_id, provider_id, addendum_code, contract_ref, "
            " normativas_cubiertas, fecha_firma, fecha_vigor, vencimiento, "
            " firmado_cliente, firmado_proveedor, minio_object_key, "
            " generated_from_template_code, metadata, created_at) "
            "VALUES (:id, :pid, :prov, :code, :cref, CAST(:norm AS jsonb), "
            "        :ff, :fv, :venc, :fc, :fp, :mk, :tcode, "
            "        CAST(:meta AS jsonb), now())"
        ), {
            "id": str(addendum_id),
            "pid": str(project_id),
            "prov": provider_for_sample["id"],
            "code": ADDENDUM_SINTETICO["addendum_code"],
            "cref": ADDENDUM_SINTETICO["contract_ref"],
            "norm": json.dumps(ADDENDUM_SINTETICO["normativas_cubiertas"]),
            "ff": ADDENDUM_SINTETICO["fecha_firma"],
            "fv": ADDENDUM_SINTETICO["fecha_vigor"],
            "venc": ADDENDUM_SINTETICO["vencimiento"],
            "fc": ADDENDUM_SINTETICO["firmado_cliente"],
            "fp": ADDENDUM_SINTETICO["firmado_proveedor"],
            "mk": minio_key,
            "tcode": ADDENDUM_SINTETICO["generated_from_template_code"],
            "meta": json.dumps(ADDENDUM_SINTETICO["metadata_"]),
        })

    # tenant context (post _admin_setup · role = fulkro_app · RLS enforced)
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()

    return {
        "client_id": str(client_id),
        "project_id": str(project_id),
        "providers": inserted_providers,
        "assessment": {
            "id": str(assessment_id),
            "provider_id": provider_for_sample["id"],
            **ASSESSMENT_SINTETICO,
        },
        "addendum": {
            "id": str(addendum_id),
            "provider_id": provider_for_sample["id"],
            "minio_object_key": minio_key,
            **{k: v for k, v in ADDENDUM_SINTETICO.items() if k != "minio_object_key"},
        },
    }
