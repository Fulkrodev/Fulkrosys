"""Tests Pydantic schemas registros vivos E-300..E-325 · sub-lote 1.C.B fase 2.

26 happy paths + 26 invalid paths + registry sanity + validate_entry_data.
Total >= 52 tests.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.motors.m_live_records.schemas import (
    ENTRY_SCHEMAS,
    REGISTER_TYPE_BLOQUES,
    REGISTER_TYPE_LABELS,
    LiveRecordCreate,
    LiveRecordListResponse,
    LiveRecordUpdate,
    LiveRecordsDashboardBlock,
    LiveRecordsDashboardResponse,
    validate_entry_data,
)


# ─── Registry sanity ──────────────────────────────────────────────────────


def test_registry_has_26_entries():
    assert len(ENTRY_SCHEMAS) == 26
    assert len(REGISTER_TYPE_LABELS) == 26
    assert len(REGISTER_TYPE_BLOQUES) == 26


def test_registry_covers_E_300_to_E_325():
    expected = {f"E-{n}" for n in range(300, 326)}
    assert set(ENTRY_SCHEMAS.keys()) == expected
    assert set(REGISTER_TYPE_LABELS.keys()) == expected
    assert set(REGISTER_TYPE_BLOQUES.keys()) == expected


def test_bloques_are_9_distinct():
    bloques = set(REGISTER_TYPE_BLOQUES.values())
    assert bloques == {
        "activos", "personas", "incidentes", "cambios", "proveedores",
        "backup", "continuidad", "auditoria", "comite",
    }


def test_validate_entry_data_rejects_unknown_register_type():
    with pytest.raises(ValueError, match="Unknown register_type"):
        validate_entry_data("E-999", {})


# ─── Happy path · 26 schemas ──────────────────────────────────────────────


_HAPPY_PAYLOADS: dict[str, dict] = {
    "E-300": {
        "codigo_activo": "ACT-001",
        "nombre": "Servidor BBDD principal",
        "categoria_activo": "hardware",
        "propietario": "IT Dept",
        "ubicacion": "CPD Madrid",
        "criticidad": "alta",
        "fecha_alta": "2026-01-15",
    },
    "E-301": {
        "codigo_sistema": "SYS-PRD-01",
        "nombre": "Sistema produccion ERP",
        "tipo_sistema": "produccion",
        "categoria_ens": "MEDIA",
        "responsable": "CTO",
        "fecha_alta": "2026-01-15",
    },
    "E-302": {
        "codigo_aplicacion": "APP-001",
        "nombre": "ERP SAP",
        "proveedor": "SAP SE",
        "version": "S/4HANA 2023",
        "tipo_licencia": "propietario",
        "fecha_alta": "2026-01-15",
        "procesa_datos_personales": True,
    },
    "E-303": {
        "dni_hash": "a" * 64,
        "nombre_completo": "Juan Perez",
        "email_corporativo": "juan@empresa.com",
        "rol_principal": "Analista",
        "departamento": "IT",
        "fecha_alta_organizacion": "2026-01-01",
    },
    "E-304": {
        "empleado_dni_hash": "a" * 64,
        "sistema_codigo": "SYS-PRD-01",
        "rol_asignado": "operador",
        "permisos": ["read", "write"],
        "fecha_alta_acceso": "2026-01-15",
        "aprobador": "CISO",
    },
    "E-305": {
        "codigo_incidente": "INC-2026-001",
        "fecha_deteccion": "2026-02-10T14:30:00Z",
        "nivel_criticidad": "alto",
        "descripcion_breve": "Acceso no autorizado detectado",
        "descripcion_detallada": "Detalle del incidente con contexto completo.",
        "fase_nist": "contencion",
    },
    "E-306": {
        "codigo_vulnerabilidad": "VLN-001",
        "cve_id": "CVE-2026-1234",
        "cvss_score": 7.5,
        "descripcion": "RCE en componente XYZ",
        "fecha_deteccion": "2026-02-10",
        "estado": "en_remediacion",
    },
    "E-307": {
        "codigo_notificacion": "NOT-2026-001",
        "autoridad": "lucia",
        "incidente_codigo": "INC-2026-001",
        "fecha_notificacion": "2026-02-10T16:00:00Z",
        "plazo_legal_horas": 72,
        "cumplido_en_plazo": True,
        "estado_respuesta": "recibida_ack",
    },
    "E-308": {
        "codigo_cambio": "CHG-001",
        "tipo_cambio": "normal",
        "descripcion": "Actualizacion firmware switches",
        "fecha_solicitud": "2026-02-01",
        "solicitante": "Equipo Networking",
    },
    "E-309": {
        "codigo_cambio_material": "CMM-001",
        "descripcion": "Migracion alcance cert a nuevo CPD",
        "impacto_categoria_ens": "ninguno",
        "requiere_notificacion_entidad_acreditada": True,
        "fecha_cambio": "2026-03-01",
    },
    "E-310": {
        "codigo_excepcion": "EXC-001",
        "medida_ens": "op.acc.5",
        "motivo": "Sistema legacy sin MFA · plan migracion 6 meses",
        "compensaciones": ["VPN obligatoria", "Monitorizacion reforzada"],
        "fecha_aprobacion": "2026-02-01",
        "fecha_revision": "2026-08-01",
        "aprobador": "Comite SGSI",
        "estado": "activa",
    },
    "E-311": {
        "codigo_proveedor": "PRV-001",
        "razon_social": "Cloud Provider SL",
        "cif": "B12345678",
        "pais": "ES",
        "tipo_servicio": "IaaS",
        "criticidad": "alta",
        "fecha_alta": "2026-01-01",
        "procesa_datos_personales": True,
    },
    "E-312": {
        "codigo_evaluacion": "EVA-001",
        "proveedor_codigo": "PRV-001",
        "periodo": "2026-Q1",
        "fecha_evaluacion": "2026-04-15",
        "puntuacion_global": 8.5,
        "evaluador": "CISO",
        "decision": "renovar",
    },
    "E-313": {
        "codigo_adenda": "ADD-001",
        "proveedor_codigo": "PRV-001",
        "tipo_adenda": "dpa_rgpd",
        "fecha_firma": "2026-01-15",
        "fecha_inicio_vigencia": "2026-01-15",
        "firmante_proveedor": "CEO Cloud Provider",
        "firmante_cliente": "CEO Cliente",
    },
    "E-314": {
        "codigo_backup": "BKP-2026-001",
        "sistema_codigo": "SYS-PRD-01",
        "fecha_ejecucion": "2026-02-10T02:00:00Z",
        "tipo_backup": "completo",
        "tamano_gb": 250.5,
        "duracion_minutos": 90,
        "resultado": "ok",
        "ubicacion_destino": "s3://bucket/backups/",
    },
    "E-315": {
        "codigo_prueba": "RST-001",
        "backup_codigo": "BKP-2026-001",
        "fecha_prueba": "2026-02-15",
        "tipo_restauracion": "parcial",
        "duracion_minutos": 45,
        "resultado": "ok",
        "operador": "Equipo Ops",
    },
    "E-316": {
        "codigo_verificacion": "VER-001",
        "backup_codigo": "BKP-2026-001",
        "fecha_verificacion": "2026-02-11",
        "algoritmo": "sha256",
        "integridad_ok": True,
    },
    "E-317": {
        "codigo_prueba_bcp": "BCP-2026-001",
        "fecha_prueba": "2026-03-15",
        "tipo_prueba": "tabletop",
        "escenario_probado": "Perdida acceso al CPD principal",
        "resultado_global": "satisfactorio",
    },
    "E-318": {
        "codigo_ejercicio_drp": "DRP-2026-001",
        "fecha_ejercicio": "2026-03-20",
        "tipo_desastre_simulado": "perdida_datacenter",
        "duracion_total_horas": 4.5,
        "resultado": "ok",
    },
    "E-319": {
        "codigo_medicion": "MED-001",
        "sistema_codigo": "SYS-PRD-01",
        "fecha_medicion": "2026-03-31",
        "rto_objetivo_minutos": 240,
        "rto_real_minutos": 180,
        "rpo_objetivo_minutos": 60,
        "rpo_real_minutos": 45,
        "cumple_objetivos": True,
    },
    "E-320": {
        "codigo_auditoria": "AUD-INT-001",
        "fecha_inicio": "2026-04-01",
        "alcance": "Medidas Anexo II op.* completo",
        "auditor_interno": "Auditoria Interna SL",
        "estado": "en_curso",
    },
    "E-321": {
        "codigo_auditoria_ext": "AUD-EXT-001",
        "entidad_acreditada": "ENAC-ENT-X",
        "fecha_inicio": "2026-05-15",
        "categoria_ens_evaluada": "MEDIA",
        "alcance": "Sistemas produccion ERP + portal cliente",
    },
    "E-322": {
        "codigo_hallazgo": "NC-001",
        "auditoria_codigo": "AUD-EXT-001",
        "severidad": "menor",
        "medida_ens_afectada": "op.exp.1",
        "descripcion": "Procedimientos operacion no documentados completamente",
        "accion_correctiva": "Redactar runbooks pendientes",
        "responsable": "CTO",
        "fecha_compromiso": "2026-07-31",
        "estado": "en_remediacion",
    },
    "E-323": {
        "codigo_acta": "ACT-2026-Q1",
        "fecha_reunion": "2026-03-31",
        "asistentes": ["CEO", "CISO", "CTO", "DPO"],
        "temas_tratados": ["Revision incidentes Q1", "Plan renovacion ENS"],
        "duracion_minutos": 90,
    },
    "E-324": {
        "codigo_decision": "DEC-001",
        "acta_codigo": "ACT-2026-Q1",
        "fecha_decision": "2026-03-31",
        "asunto": "Aprobacion presupuesto renovacion ENS 2026",
        "descripcion": "Asignacion 50k EUR para auditoria + mejoras",
        "responsable_implementacion": "CFO",
        "estado": "en_implementacion",
    },
    "E-325": {
        "codigo_indicador": "KPI-001",
        "nombre": "Incidentes criticidad alta",
        "periodo": "2026-02",
        "valor": 2.0,
        "unidad": "count",
        "objetivo": 5.0,
        "cumple_objetivo": True,
        "tendencia": "estable",
    },
}


@pytest.mark.parametrize("register_type", sorted(_HAPPY_PAYLOADS.keys()))
def test_each_register_type_validates_happy_payload(register_type):
    payload = _HAPPY_PAYLOADS[register_type]
    out = validate_entry_data(register_type, payload)
    assert out is not None
    assert isinstance(out, dict)


def test_all_26_register_types_covered_by_happy_payloads():
    assert set(_HAPPY_PAYLOADS.keys()) == set(ENTRY_SCHEMAS.keys())


# ─── Invalid paths · 26 schemas ────────────────────────────────────────────


_INVALID_PAYLOADS: dict[str, dict] = {
    "E-300": {"codigo_activo": "ACT-001"},  # missing required fields
    "E-301": {"codigo_sistema": "SYS-1", "tipo_sistema": "xxx"},  # invalid enum
    "E-302": {"nombre": "x", "version": "1"},  # missing required
    "E-303": {"dni_hash": "x", "nombre_completo": "y"},  # dni_hash too short + missing fields
    "E-304": {"empleado_dni_hash": "a" * 64},  # missing required
    "E-305": {"codigo_incidente": "INC-1", "nivel_criticidad": "extremo"},  # invalid enum
    "E-306": {"codigo_vulnerabilidad": "V-1", "cvss_score": 15.0},  # out of range
    "E-307": {"codigo_notificacion": "N-1", "autoridad": "fbi"},  # invalid enum
    "E-308": {"codigo_cambio": "C-1", "tipo_cambio": "weird"},  # invalid enum
    "E-309": {"codigo_cambio_material": "CM-1"},  # missing required
    "E-310": {"codigo_excepcion": "E-1", "estado": "weird"},  # invalid enum
    "E-311": {"codigo_proveedor": "P-1", "pais": "ESP"},  # pais > 2 chars
    "E-312": {"codigo_evaluacion": "EV-1", "puntuacion_global": -1.0},  # out of range
    "E-313": {"codigo_adenda": "AD-1", "tipo_adenda": "weird"},  # invalid enum
    "E-314": {"codigo_backup": "B-1", "tamano_gb": -10.0},  # negative
    "E-315": {"codigo_prueba": "R-1", "tipo_restauracion": "weird"},  # invalid enum
    "E-316": {"codigo_verificacion": "V-1", "algoritmo": "weakhash"},  # invalid enum
    "E-317": {"codigo_prueba_bcp": "B-1", "resultado_global": "perfect"},  # invalid enum
    "E-318": {"codigo_ejercicio_drp": "D-1", "tipo_desastre_simulado": "alien"},  # invalid enum
    "E-319": {"codigo_medicion": "M-1", "rto_objetivo_minutos": -5},  # negative
    "E-320": {"codigo_auditoria": "A-1", "estado": "weird"},  # invalid enum
    "E-321": {"codigo_auditoria_ext": "AE-1", "categoria_ens_evaluada": "EXTREMA"},  # invalid enum
    "E-322": {"codigo_hallazgo": "H-1", "severidad": "critical"},  # invalid enum
    "E-323": {"codigo_acta": "A-1", "duracion_minutos": -5},  # negative
    "E-324": {"codigo_decision": "D-1", "estado": "weird"},  # invalid enum
    "E-325": {"codigo_indicador": "I-1", "periodo": "2026-13"},  # invalid period pattern
}


@pytest.mark.parametrize("register_type", sorted(_INVALID_PAYLOADS.keys()))
def test_each_register_type_rejects_invalid_payload(register_type):
    payload = _INVALID_PAYLOADS[register_type]
    with pytest.raises(ValidationError):
        validate_entry_data(register_type, payload)


def test_all_26_register_types_covered_by_invalid_payloads():
    assert set(_INVALID_PAYLOADS.keys()) == set(ENTRY_SCHEMAS.keys())


# ─── Wrappers ─────────────────────────────────────────────────────────────


def test_live_record_create_accepts_arbitrary_entry_data():
    payload = LiveRecordCreate(entry_data={"any": "shape"})
    assert payload.entry_data == {"any": "shape"}


def test_live_record_update_allows_partial():
    payload = LiveRecordUpdate(status="archived")
    assert payload.status == "archived"
    assert payload.entry_data is None


def test_live_record_update_rejects_invalid_status():
    with pytest.raises(ValidationError):
        LiveRecordUpdate(status="weird")  # type: ignore[arg-type]


def test_live_record_list_response_shape():
    resp = LiveRecordListResponse(records=[], total=0, limit=50, offset=0)
    assert resp.total == 0


def test_dashboard_response_shape():
    import uuid as _u

    block = LiveRecordsDashboardBlock(
        register_type="E-300",
        label="Inventario de activos",
        bloque="activos",
        active_count=3,
        archived_count=1,
    )
    resp = LiveRecordsDashboardResponse(
        project_id=_u.uuid4(),
        blocks=[block],
        total_active=3,
    )
    assert resp.total_active == 3
    assert resp.blocks[0].register_type == "E-300"
