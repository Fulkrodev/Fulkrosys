"""Pydantic schemas para registros vivos E-300..E-325 · sub-lote 1.C.B.

26 schemas tipados (uno por register_type) validan la shape de ``entry_data``
JSONB en tabla ``live_records``. Cada schema lleva los campos minimos que el
cliente debe mantener para que el registro vivo cumpla su funcion auditoria
ENAC. Discriminator manejado en wrapper ``LiveRecordCreate`` / ``LiveRecordRead``.

Bloques (paralelos a la enumeracion ENS Anexo II + practica ENAC):
- Activos:     E-300 inventario activos · E-301 sistemas · E-302 aplicaciones.
- Personas:    E-303 empleados · E-304 roles + accesos.
- Incidentes:  E-305 libro incidentes · E-306 vulnerabilidades · E-307 notif.
- Cambios:     E-308 libro cambios · E-309 materiales · E-310 excepciones.
- Proveedores: E-311 inventario · E-312 evaluaciones · E-313 adendas.
- Backup:      E-314 libro backups · E-315 restauraciones · E-316 integridad.
- Continuidad: E-317 BCP pruebas · E-318 DRP ejercicios · E-319 RTO/RPO.
- Auditoria:   E-320 internas · E-321 externas · E-322 hallazgos NC.
- Comite:      E-323 actas · E-324 decisiones · E-325 indicadores SGSI.

RGPD: E-303 stores ``dni_hash`` (NO DNI plano) y ``email_corporativo`` solo.
LOPDGDD art. 9 art. 5: NO datos sensibles en entry_data.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


# ─────────────────────────────────────────────────────────────────────────
# Bloque Activos · E-300, E-301, E-302
# ─────────────────────────────────────────────────────────────────────────


class E300InventoryActivoEntry(BaseModel):
    """E-300 · Inventario de activos."""
    model_config = ConfigDict(extra="forbid")

    codigo_activo: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    nombre: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    categoria_activo: Literal[
        "hardware", "software", "datos", "comunicaciones",
        "instalaciones", "personal", "servicios",
    ]
    propietario: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    ubicacion: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    criticidad: Literal["alta", "media", "baja"]
    fecha_alta: date
    fecha_baja: date | None = None
    observaciones: str | None = None


class E301InventorySistemaEntry(BaseModel):
    """E-301 · Inventario de sistemas."""
    model_config = ConfigDict(extra="forbid")

    codigo_sistema: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    nombre: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    tipo_sistema: Literal[
        "produccion", "preproduccion", "desarrollo", "test",
        "respaldo", "monitorizacion",
    ]
    categoria_ens: Literal["BASICA", "MEDIA", "ALTA"]
    responsable: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    fecha_alta: date
    fecha_baja: date | None = None
    componentes_principales: list[str] = Field(default_factory=list)


class E302InventoryAplicacionEntry(BaseModel):
    """E-302 · Inventario de aplicaciones."""
    model_config = ConfigDict(extra="forbid")

    codigo_aplicacion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    nombre: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    proveedor: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    version: str
    tipo_licencia: Literal["propietario", "open_source", "saas", "interno"]
    sistema_anfitrion: str | None = None
    fecha_alta: date
    fecha_baja: date | None = None
    procesa_datos_personales: bool = False


# ─────────────────────────────────────────────────────────────────────────
# Bloque Personas · E-303, E-304
# ─────────────────────────────────────────────────────────────────────────


class E303InventoryEmpleadoEntry(BaseModel):
    """E-303 · Inventario de empleados (RGPD: dni_hash, NO DNI plano)."""
    model_config = ConfigDict(extra="forbid")

    dni_hash: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    nombre_completo: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    email_corporativo: Annotated[str, StringConstraints(pattern=r"^[^@]+@[^@]+\.[^@]+$")]
    rol_principal: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    departamento: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    fecha_alta_organizacion: date
    fecha_baja_organizacion: date | None = None
    formacion_ens_completada: bool = False
    fecha_ultima_formacion: date | None = None


class E304RolesAccesosEntry(BaseModel):
    """E-304 · Roles + accesos asignados (matriz autorizacion)."""
    model_config = ConfigDict(extra="forbid")

    empleado_dni_hash: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    sistema_codigo: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    rol_asignado: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    permisos: list[str] = Field(default_factory=list)
    fecha_alta_acceso: date
    fecha_baja_acceso: date | None = None
    aprobador: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    justificacion: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Bloque Incidentes · E-305, E-306, E-307
# ─────────────────────────────────────────────────────────────────────────


_NIST_PHASE = Literal[
    "preparacion", "deteccion", "contencion",
    "erradicacion", "recuperacion", "lecciones_aprendidas",
]


class E305LibroIncidentesEntry(BaseModel):
    """E-305 · Libro de incidentes (M19 auto-population trigger)."""
    model_config = ConfigDict(extra="forbid")

    codigo_incidente: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    fecha_deteccion: datetime
    nivel_criticidad: Literal["critico", "alto", "medio", "bajo", "informativo"]
    descripcion_breve: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    descripcion_detallada: Annotated[str, StringConstraints(min_length=1)]
    activos_afectados: list[str] = Field(default_factory=list)
    notificado_lucia: bool = False
    notificado_aepd: bool = False
    fase_nist: _NIST_PHASE
    fecha_cierre: datetime | None = None
    leciones_aprendidas: str | None = None


class E306LibroVulnerabilidadesEntry(BaseModel):
    """E-306 · Libro de vulnerabilidades (CVE/CVSS)."""
    model_config = ConfigDict(extra="forbid")

    codigo_vulnerabilidad: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    cve_id: str | None = None
    cvss_score: Annotated[float, Field(ge=0.0, le=10.0)] | None = None
    descripcion: Annotated[str, StringConstraints(min_length=1)]
    activos_afectados: list[str] = Field(default_factory=list)
    fecha_deteccion: date
    fecha_remediacion: date | None = None
    estado: Literal["detectada", "en_remediacion", "mitigada", "cerrada", "aceptada"]
    plan_remediacion: str | None = None


class E307NotificacionesAutoridadesEntry(BaseModel):
    """E-307 · Notificaciones a autoridades (LUCIA, AEPD, CCN-CERT)."""
    model_config = ConfigDict(extra="forbid")

    codigo_notificacion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    autoridad: Literal["lucia", "aepd", "ccn_cert", "incibe", "otro"]
    incidente_codigo: str
    fecha_notificacion: datetime
    plazo_legal_horas: Annotated[int, Field(ge=1, le=720)]
    cumplido_en_plazo: bool
    referencia_externa: str | None = None
    estado_respuesta: Literal["pendiente", "recibida_ack", "investigacion", "cerrada"]


# ─────────────────────────────────────────────────────────────────────────
# Bloque Cambios · E-308, E-309, E-310
# ─────────────────────────────────────────────────────────────────────────


class E308LibroCambiosEntry(BaseModel):
    """E-308 · Libro de cambios (M28 auto-population trigger)."""
    model_config = ConfigDict(extra="forbid")

    codigo_cambio: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    tipo_cambio: Literal["estandar", "normal", "urgente", "emergencia"]
    descripcion: Annotated[str, StringConstraints(min_length=1)]
    sistemas_afectados: list[str] = Field(default_factory=list)
    fecha_solicitud: date
    fecha_implementacion: date | None = None
    solicitante: str
    aprobador: str | None = None
    rollback_plan: str | None = None
    resultado: Literal["pendiente", "implementado_ok", "implementado_con_issues", "rolled_back"] | None = None


class E309CambiosMaterialesEntry(BaseModel):
    """E-309 · Cambios materiales (impacto categoria ENS / cert ENAC)."""
    model_config = ConfigDict(extra="forbid")

    codigo_cambio_material: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    descripcion: Annotated[str, StringConstraints(min_length=1)]
    impacto_categoria_ens: Literal[
        "ninguno", "elevacion_basica_media", "elevacion_media_alta",
        "rebaja", "cambio_alcance",
    ]
    requiere_notificacion_entidad_acreditada: bool
    fecha_cambio: date
    aprobado_comite: bool = False
    fecha_aprobacion_comite: date | None = None
    documentos_actualizados: list[str] = Field(default_factory=list)


class E310ExcepcionesAutorizadasEntry(BaseModel):
    """E-310 · Excepciones autorizadas a medidas ENS (riesgo aceptado)."""
    model_config = ConfigDict(extra="forbid")

    codigo_excepcion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    medida_ens: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    motivo: Annotated[str, StringConstraints(min_length=1)]
    compensaciones: list[str] = Field(default_factory=list)
    fecha_aprobacion: date
    fecha_revision: date
    aprobador: str
    estado: Literal["activa", "en_revision", "cerrada_resuelta", "cerrada_no_aplicable"]


# ─────────────────────────────────────────────────────────────────────────
# Bloque Proveedores · E-311, E-312, E-313
# ─────────────────────────────────────────────────────────────────────────


class E311InventoryProveedoresEntry(BaseModel):
    """E-311 · Inventario de proveedores."""
    model_config = ConfigDict(extra="forbid")

    codigo_proveedor: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    razon_social: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    cif: Annotated[str, StringConstraints(min_length=8, max_length=15)]
    pais: Annotated[str, StringConstraints(min_length=2, max_length=2)]
    tipo_servicio: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    criticidad: Literal["alta", "media", "baja"]
    fecha_alta: date
    fecha_baja: date | None = None
    procesa_datos_personales: bool = False
    transferencia_internacional: bool = False


class E312EvaluacionesProveedoresEntry(BaseModel):
    """E-312 · Evaluaciones proveedores (M23 retainer auto-population trigger)."""
    model_config = ConfigDict(extra="forbid")

    codigo_evaluacion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    proveedor_codigo: str
    periodo: str
    fecha_evaluacion: date
    puntuacion_global: Annotated[float, Field(ge=0.0, le=10.0)]
    hallazgos: list[str] = Field(default_factory=list)
    acciones_correctivas: list[str] = Field(default_factory=list)
    evaluador: str
    decision: Literal["renovar", "renegociar", "rescindir", "monitorizar"]


class E313AdendasFirmadasEntry(BaseModel):
    """E-313 · Adendas firmadas (DPA RGPD art.28, SLAs ENS, etc.)."""
    model_config = ConfigDict(extra="forbid")

    codigo_adenda: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    proveedor_codigo: str
    tipo_adenda: Literal["dpa_rgpd", "sla_ens", "cybersec", "confidencialidad", "subprocesadores"]
    fecha_firma: date
    fecha_inicio_vigencia: date
    fecha_fin_vigencia: date | None = None
    firmante_proveedor: str
    firmante_cliente: str
    referencia_documento: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Bloque Backup · E-314, E-315, E-316
# ─────────────────────────────────────────────────────────────────────────


class E314LibroBackupsEntry(BaseModel):
    """E-314 · Libro de backups (registro per ejecucion)."""
    model_config = ConfigDict(extra="forbid")

    codigo_backup: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    sistema_codigo: str
    fecha_ejecucion: datetime
    tipo_backup: Literal["completo", "incremental", "diferencial", "snapshot"]
    tamano_gb: Annotated[float, Field(ge=0.0)]
    duracion_minutos: Annotated[int, Field(ge=0)]
    resultado: Literal["ok", "warning", "failed"]
    ubicacion_destino: str
    cifrado: bool = True


class E315PruebasRestauracionEntry(BaseModel):
    """E-315 · Pruebas de restauracion (ENS op.cont.3 verificacion)."""
    model_config = ConfigDict(extra="forbid")

    codigo_prueba: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    backup_codigo: str
    fecha_prueba: date
    tipo_restauracion: Literal["total", "parcial", "punto_en_tiempo"]
    duracion_minutos: Annotated[int, Field(ge=0)]
    resultado: Literal["ok", "ok_con_issues", "fallida"]
    operador: str
    notas: str | None = None
    rto_objetivo_minutos: Annotated[int, Field(ge=0)] | None = None
    rto_real_minutos: Annotated[int, Field(ge=0)] | None = None


class E316VerificacionesIntegridadEntry(BaseModel):
    """E-316 · Verificaciones integridad backups (checksums, hashes)."""
    model_config = ConfigDict(extra="forbid")

    codigo_verificacion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    backup_codigo: str
    fecha_verificacion: date
    algoritmo: Literal["sha256", "sha512", "blake3", "md5"]
    integridad_ok: bool
    hash_esperado: str | None = None
    hash_obtenido: str | None = None
    accion_correctiva: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Bloque Continuidad · E-317, E-318, E-319
# ─────────────────────────────────────────────────────────────────────────


class E317BCPPruebasEntry(BaseModel):
    """E-317 · BCP (Business Continuity Plan) pruebas."""
    model_config = ConfigDict(extra="forbid")

    codigo_prueba_bcp: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    fecha_prueba: date
    tipo_prueba: Literal["tabletop", "walkthrough", "simulacion", "full_test"]
    escenario_probado: Annotated[str, StringConstraints(min_length=1)]
    procesos_evaluados: list[str] = Field(default_factory=list)
    resultado_global: Literal["satisfactorio", "satisfactorio_con_mejoras", "insatisfactorio"]
    participantes: list[str] = Field(default_factory=list)
    informe_referencia: str | None = None


class E318DRPEjerciciosEntry(BaseModel):
    """E-318 · DRP (Disaster Recovery Plan) ejercicios."""
    model_config = ConfigDict(extra="forbid")

    codigo_ejercicio_drp: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    fecha_ejercicio: date
    sistemas_recuperados: list[str] = Field(default_factory=list)
    tipo_desastre_simulado: Literal[
        "perdida_datacenter", "fallo_red", "fallo_servidor",
        "ataque_ransomware", "perdida_proveedor_cloud",
    ]
    duracion_total_horas: Annotated[float, Field(ge=0.0)]
    resultado: Literal["ok", "ok_con_observaciones", "fallido"]
    observador_externo: str | None = None


class E319RTORPOMeasurementsEntry(BaseModel):
    """E-319 · RTO/RPO measurements per sistema critico."""
    model_config = ConfigDict(extra="forbid")

    codigo_medicion: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    sistema_codigo: str
    fecha_medicion: date
    rto_objetivo_minutos: Annotated[int, Field(ge=0)]
    rto_real_minutos: Annotated[int, Field(ge=0)]
    rpo_objetivo_minutos: Annotated[int, Field(ge=0)]
    rpo_real_minutos: Annotated[int, Field(ge=0)]
    cumple_objetivos: bool
    gap_analysis: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Bloque Auditoria · E-320, E-321, E-322
# ─────────────────────────────────────────────────────────────────────────


class E320AuditoriasInternasEntry(BaseModel):
    """E-320 · Auditorias internas SGSI."""
    model_config = ConfigDict(extra="forbid")

    codigo_auditoria: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    fecha_inicio: date
    fecha_fin: date | None = None
    alcance: Annotated[str, StringConstraints(min_length=1)]
    auditor_interno: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    medidas_revisadas: list[str] = Field(default_factory=list)
    hallazgos_count: Annotated[int, Field(ge=0)] = 0
    informe_referencia: str | None = None
    estado: Literal["planificada", "en_curso", "finalizada", "cancelada"]


class E321AuditoriasExternasEntry(BaseModel):
    """E-321 · Auditorias externas (entidad acreditada ENAC para MEDIA/ALTA)."""
    model_config = ConfigDict(extra="forbid")

    codigo_auditoria_ext: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    entidad_acreditada: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    fecha_inicio: date
    fecha_fin: date | None = None
    categoria_ens_evaluada: Literal["BASICA", "MEDIA", "ALTA"]
    alcance: Annotated[str, StringConstraints(min_length=1)]
    resultado: Literal["conforme", "conforme_con_observaciones", "no_conforme", "pendiente"] | None = None
    certificado_emitido: bool = False
    fecha_emision_certificado: date | None = None
    vigencia_certificado_anos: Annotated[int, Field(ge=1, le=5)] | None = None


class E322HallazgosNCEntry(BaseModel):
    """E-322 · Hallazgos NC (No Conformidad) + acciones correctivas."""
    model_config = ConfigDict(extra="forbid")

    codigo_hallazgo: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    auditoria_codigo: str
    severidad: Literal["mayor", "menor", "observacion"]
    medida_ens_afectada: str
    descripcion: Annotated[str, StringConstraints(min_length=1)]
    accion_correctiva: str
    responsable: str
    fecha_compromiso: date
    fecha_cierre_real: date | None = None
    estado: Literal["abierto", "en_remediacion", "verificado_cerrado", "diferido"]


# ─────────────────────────────────────────────────────────────────────────
# Bloque Comite · E-323, E-324, E-325
# ─────────────────────────────────────────────────────────────────────────


class E323ActasComiteEntry(BaseModel):
    """E-323 · Actas Comite SGSI (gobierno seguridad)."""
    model_config = ConfigDict(extra="forbid")

    codigo_acta: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    fecha_reunion: date
    asistentes: list[str] = Field(default_factory=list)
    ausentes_justificados: list[str] = Field(default_factory=list)
    temas_tratados: list[str] = Field(default_factory=list)
    duracion_minutos: Annotated[int, Field(ge=0)]
    siguiente_convocatoria: date | None = None
    referencia_documento: str | None = None


class E324DecisionesAprobadasEntry(BaseModel):
    """E-324 · Decisiones aprobadas por el Comite SGSI."""
    model_config = ConfigDict(extra="forbid")

    codigo_decision: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    acta_codigo: str
    fecha_decision: date
    asunto: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    descripcion: Annotated[str, StringConstraints(min_length=1)]
    responsable_implementacion: str
    fecha_compromiso_implementacion: date | None = None
    estado: Literal["pendiente", "en_implementacion", "implementada", "diferida", "cancelada"]


class E325IndicadoresSGSIEntry(BaseModel):
    """E-325 · Indicadores SGSI mensuales (KPI seguridad)."""
    model_config = ConfigDict(extra="forbid")

    codigo_indicador: Annotated[str, StringConstraints(min_length=1, max_length=50)]
    nombre: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    periodo: Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
    valor: float
    unidad: str
    objetivo: float | None = None
    cumple_objetivo: bool | None = None
    tendencia: Literal["mejora", "estable", "deterioro"] | None = None
    fuente_dato: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Discriminator wrapper + registry
# ─────────────────────────────────────────────────────────────────────────


ENTRY_SCHEMAS: dict[str, type[BaseModel]] = {
    "E-300": E300InventoryActivoEntry,
    "E-301": E301InventorySistemaEntry,
    "E-302": E302InventoryAplicacionEntry,
    "E-303": E303InventoryEmpleadoEntry,
    "E-304": E304RolesAccesosEntry,
    "E-305": E305LibroIncidentesEntry,
    "E-306": E306LibroVulnerabilidadesEntry,
    "E-307": E307NotificacionesAutoridadesEntry,
    "E-308": E308LibroCambiosEntry,
    "E-309": E309CambiosMaterialesEntry,
    "E-310": E310ExcepcionesAutorizadasEntry,
    "E-311": E311InventoryProveedoresEntry,
    "E-312": E312EvaluacionesProveedoresEntry,
    "E-313": E313AdendasFirmadasEntry,
    "E-314": E314LibroBackupsEntry,
    "E-315": E315PruebasRestauracionEntry,
    "E-316": E316VerificacionesIntegridadEntry,
    "E-317": E317BCPPruebasEntry,
    "E-318": E318DRPEjerciciosEntry,
    "E-319": E319RTORPOMeasurementsEntry,
    "E-320": E320AuditoriasInternasEntry,
    "E-321": E321AuditoriasExternasEntry,
    "E-322": E322HallazgosNCEntry,
    "E-323": E323ActasComiteEntry,
    "E-324": E324DecisionesAprobadasEntry,
    "E-325": E325IndicadoresSGSIEntry,
}


REGISTER_TYPE_LABELS: dict[str, str] = {
    "E-300": "Inventario de activos",
    "E-301": "Inventario de sistemas",
    "E-302": "Inventario de aplicaciones",
    "E-303": "Inventario de empleados",
    "E-304": "Roles y accesos",
    "E-305": "Libro de incidentes",
    "E-306": "Libro de vulnerabilidades",
    "E-307": "Notificaciones a autoridades",
    "E-308": "Libro de cambios",
    "E-309": "Cambios materiales",
    "E-310": "Excepciones autorizadas",
    "E-311": "Inventario de proveedores",
    "E-312": "Evaluaciones de proveedores",
    "E-313": "Adendas firmadas",
    "E-314": "Libro de backups",
    "E-315": "Pruebas de restauracion",
    "E-316": "Verificaciones de integridad",
    "E-317": "BCP pruebas",
    "E-318": "DRP ejercicios",
    "E-319": "RTO/RPO measurements",
    "E-320": "Auditorias internas",
    "E-321": "Auditorias externas",
    "E-322": "Hallazgos NC + acciones correctivas",
    "E-323": "Actas Comite SGSI",
    "E-324": "Decisiones aprobadas",
    "E-325": "Indicadores SGSI mensuales",
}


REGISTER_TYPE_BLOQUES: dict[str, str] = {
    **{k: "activos" for k in ("E-300", "E-301", "E-302")},
    **{k: "personas" for k in ("E-303", "E-304")},
    **{k: "incidentes" for k in ("E-305", "E-306", "E-307")},
    **{k: "cambios" for k in ("E-308", "E-309", "E-310")},
    **{k: "proveedores" for k in ("E-311", "E-312", "E-313")},
    **{k: "backup" for k in ("E-314", "E-315", "E-316")},
    **{k: "continuidad" for k in ("E-317", "E-318", "E-319")},
    **{k: "auditoria" for k in ("E-320", "E-321", "E-322")},
    **{k: "comite" for k in ("E-323", "E-324", "E-325")},
}


AnyEntryData = Union[
    E300InventoryActivoEntry, E301InventorySistemaEntry, E302InventoryAplicacionEntry,
    E303InventoryEmpleadoEntry, E304RolesAccesosEntry,
    E305LibroIncidentesEntry, E306LibroVulnerabilidadesEntry, E307NotificacionesAutoridadesEntry,
    E308LibroCambiosEntry, E309CambiosMaterialesEntry, E310ExcepcionesAutorizadasEntry,
    E311InventoryProveedoresEntry, E312EvaluacionesProveedoresEntry, E313AdendasFirmadasEntry,
    E314LibroBackupsEntry, E315PruebasRestauracionEntry, E316VerificacionesIntegridadEntry,
    E317BCPPruebasEntry, E318DRPEjerciciosEntry, E319RTORPOMeasurementsEntry,
    E320AuditoriasInternasEntry, E321AuditoriasExternasEntry, E322HallazgosNCEntry,
    E323ActasComiteEntry, E324DecisionesAprobadasEntry, E325IndicadoresSGSIEntry,
]


def validate_entry_data(register_type: str, entry_data: dict[str, Any]) -> dict[str, Any]:
    """Validate entry_data shape against the schema for register_type.

    Returns the validated dict (Pydantic model_dump). Raises ValueError if
    the register_type is unknown, or pydantic.ValidationError if the payload
    fails schema validation.
    """
    schema = ENTRY_SCHEMAS.get(register_type)
    if schema is None:
        raise ValueError(
            f"Unknown register_type {register_type!r}. "
            f"Valid types: {sorted(ENTRY_SCHEMAS.keys())}"
        )
    validated = schema.model_validate(entry_data)
    return validated.model_dump(mode="json")


# ─────────────────────────────────────────────────────────────────────────
# API request / response wrappers
# ─────────────────────────────────────────────────────────────────────────


class LiveRecordCreate(BaseModel):
    """Payload create. register_type validated via discriminator."""
    model_config = ConfigDict(extra="forbid")

    entry_data: dict[str, Any]


class LiveRecordUpdate(BaseModel):
    """Payload update (partial entry_data + optional status)."""
    model_config = ConfigDict(extra="forbid")

    entry_data: dict[str, Any] | None = None
    status: Literal["active", "archived"] | None = None


class LiveRecordRead(BaseModel):
    """Read shape (matches ORM LiveRecord columns)."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    register_type: str
    entry_data: dict[str, Any]
    status: Literal["active", "archived"]
    created_at: datetime
    created_by: uuid.UUID
    updated_at: datetime
    updated_by: uuid.UUID


class LiveRecordListResponse(BaseModel):
    """Paginated list response."""
    model_config = ConfigDict(extra="forbid")

    records: list[LiveRecordRead]
    total: int
    limit: int
    offset: int


class LiveRecordsDashboardBlock(BaseModel):
    """Dashboard summary entry per register_type."""
    model_config = ConfigDict(extra="forbid")

    register_type: str
    label: str
    bloque: str
    active_count: int
    archived_count: int


class LiveRecordsDashboardResponse(BaseModel):
    """Dashboard 26 register_types con counts."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID
    blocks: list[LiveRecordsDashboardBlock]
    total_active: int
