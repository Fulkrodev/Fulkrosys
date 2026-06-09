/**
 * Zod schemas live_records · sub-atom 1.C.B fase 4c.
 *
 * Mirror Pydantic backend (backend/app/motors/m_live_records/schemas.py).
 * Validacion FRONTEND coexiste con la del backend · este es client-side UX
 * (errores inline en form) · el backend rechaza con HTTP 422 si bypass.
 *
 * Cada schema acompaña FIELD_CONFIG (metadata UI: label · type · options)
 * que LiveRecordCreate consume para render dinamico del form.
 */
import { z } from "zod";

import type { RegisterType } from "@/lib/types/live-records";


export type FieldKind =
  | "text"
  | "textarea"
  | "date"
  | "datetime"
  | "number"
  | "select"
  | "boolean"
  | "list-string";


export interface FieldConfig {
  key: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  placeholder?: string;
  options?: readonly string[];
  helpText?: string;
}


// ─── Schemas Zod (subset campos requeridos · UX no exige todos) ───────────


const e300 = z.object({
  codigo_activo: z.string().min(1).max(50),
  nombre: z.string().min(1).max(200),
  categoria_activo: z.enum([
    "hardware", "software", "datos", "comunicaciones",
    "instalaciones", "personal", "servicios",
  ]),
  propietario: z.string().min(1).max(200),
  ubicacion: z.string().min(1).max(200),
  criticidad: z.enum(["alta", "media", "baja"]),
  fecha_alta: z.string().min(1),
  fecha_baja: z.string().optional().nullable(),
  observaciones: z.string().optional().nullable(),
});

const e301 = z.object({
  codigo_sistema: z.string().min(1).max(50),
  nombre: z.string().min(1).max(200),
  tipo_sistema: z.enum([
    "produccion", "preproduccion", "desarrollo",
    "test", "respaldo", "monitorizacion",
  ]),
  categoria_ens: z.enum(["BASICA", "MEDIA", "ALTA"]),
  responsable: z.string().min(1).max(200),
  fecha_alta: z.string().min(1),
  fecha_baja: z.string().optional().nullable(),
});

const e302 = z.object({
  codigo_aplicacion: z.string().min(1).max(50),
  nombre: z.string().min(1).max(200),
  proveedor: z.string().min(1).max(200),
  version: z.string().min(1),
  tipo_licencia: z.enum(["propietario", "open_source", "saas", "interno"]),
  sistema_anfitrion: z.string().optional().nullable(),
  fecha_alta: z.string().min(1),
  fecha_baja: z.string().optional().nullable(),
  procesa_datos_personales: z.boolean().default(false),
});

const e303 = z.object({
  dni_hash: z.string().min(8).max(128),
  nombre_completo: z.string().min(1).max(200),
  email_corporativo: z.string().email(),
  rol_principal: z.string().min(1).max(100),
  departamento: z.string().min(1).max(100),
  fecha_alta_organizacion: z.string().min(1),
  fecha_baja_organizacion: z.string().optional().nullable(),
  formacion_ens_completada: z.boolean().default(false),
});

const e304 = z.object({
  empleado_dni_hash: z.string().min(8).max(128),
  sistema_codigo: z.string().min(1).max(50),
  rol_asignado: z.string().min(1).max(100),
  permisos: z.array(z.string()).default([]),
  fecha_alta_acceso: z.string().min(1),
  fecha_baja_acceso: z.string().optional().nullable(),
  aprobador: z.string().min(1).max(200),
  justificacion: z.string().optional().nullable(),
});

const e305 = z.object({
  codigo_incidente: z.string().min(1).max(50),
  fecha_deteccion: z.string().min(1),
  nivel_criticidad: z.enum([
    "critico", "alto", "medio", "bajo", "informativo",
  ]),
  descripcion_breve: z.string().min(1).max(200),
  descripcion_detallada: z.string().min(1),
  notificado_lucia: z.boolean().default(false),
  notificado_aepd: z.boolean().default(false),
  fase_nist: z.enum([
    "preparacion", "deteccion", "contencion",
    "erradicacion", "recuperacion", "lecciones_aprendidas",
  ]),
});

const e306 = z.object({
  codigo_vulnerabilidad: z.string().min(1).max(50),
  cve_id: z.string().optional().nullable(),
  cvss_score: z.number().min(0).max(10).optional().nullable(),
  descripcion: z.string().min(1),
  fecha_deteccion: z.string().min(1),
  estado: z.enum([
    "detectada", "en_remediacion", "mitigada", "cerrada", "aceptada",
  ]),
});

const e307 = z.object({
  codigo_notificacion: z.string().min(1).max(50),
  autoridad: z.enum(["lucia", "aepd", "ccn_cert", "incibe", "otro"]),
  incidente_codigo: z.string().min(1),
  fecha_notificacion: z.string().min(1),
  plazo_legal_horas: z.number().int().min(1).max(720),
  cumplido_en_plazo: z.boolean(),
  estado_respuesta: z.enum([
    "pendiente", "recibida_ack", "investigacion", "cerrada",
  ]),
});

const e308 = z.object({
  codigo_cambio: z.string().min(1).max(50),
  tipo_cambio: z.enum(["estandar", "normal", "urgente", "emergencia"]),
  descripcion: z.string().min(1),
  fecha_solicitud: z.string().min(1),
  solicitante: z.string().min(1),
});

const e309 = z.object({
  codigo_cambio_material: z.string().min(1).max(50),
  descripcion: z.string().min(1),
  impacto_categoria_ens: z.enum([
    "ninguno", "elevacion_basica_media",
    "elevacion_media_alta", "rebaja", "cambio_alcance",
  ]),
  requiere_notificacion_entidad_acreditada: z.boolean(),
  fecha_cambio: z.string().min(1),
  aprobado_comite: z.boolean().default(false),
});

const e310 = z.object({
  codigo_excepcion: z.string().min(1).max(50),
  medida_ens: z.string().min(1).max(50),
  motivo: z.string().min(1),
  fecha_aprobacion: z.string().min(1),
  fecha_revision: z.string().min(1),
  aprobador: z.string().min(1),
  estado: z.enum([
    "activa", "en_revision", "cerrada_resuelta", "cerrada_no_aplicable",
  ]),
});

const e311 = z.object({
  codigo_proveedor: z.string().min(1).max(50),
  razon_social: z.string().min(1).max(300),
  cif: z.string().min(8).max(15),
  pais: z.string().length(2),
  tipo_servicio: z.string().min(1).max(200),
  criticidad: z.enum(["alta", "media", "baja"]),
  fecha_alta: z.string().min(1),
  procesa_datos_personales: z.boolean().default(false),
});

const e312 = z.object({
  codigo_evaluacion: z.string().min(1).max(50),
  proveedor_codigo: z.string().min(1),
  periodo: z.string().min(1),
  fecha_evaluacion: z.string().min(1),
  puntuacion_global: z.number().min(0).max(10),
  evaluador: z.string().min(1),
  decision: z.enum(["renovar", "renegociar", "rescindir", "monitorizar"]),
});

const e313 = z.object({
  codigo_adenda: z.string().min(1).max(50),
  proveedor_codigo: z.string().min(1),
  tipo_adenda: z.enum([
    "dpa_rgpd", "sla_ens", "cybersec",
    "confidencialidad", "subprocesadores",
  ]),
  fecha_firma: z.string().min(1),
  fecha_inicio_vigencia: z.string().min(1),
  firmante_proveedor: z.string().min(1),
  firmante_cliente: z.string().min(1),
});

const e314 = z.object({
  codigo_backup: z.string().min(1).max(50),
  sistema_codigo: z.string().min(1),
  fecha_ejecucion: z.string().min(1),
  tipo_backup: z.enum(["completo", "incremental", "diferencial", "snapshot"]),
  tamano_gb: z.number().min(0),
  duracion_minutos: z.number().int().min(0),
  resultado: z.enum(["ok", "warning", "failed"]),
  ubicacion_destino: z.string().min(1),
  cifrado: z.boolean().default(true),
});

const e315 = z.object({
  codigo_prueba: z.string().min(1).max(50),
  backup_codigo: z.string().min(1),
  fecha_prueba: z.string().min(1),
  tipo_restauracion: z.enum(["total", "parcial", "punto_en_tiempo"]),
  duracion_minutos: z.number().int().min(0),
  resultado: z.enum(["ok", "ok_con_issues", "fallida"]),
  operador: z.string().min(1),
});

const e316 = z.object({
  codigo_verificacion: z.string().min(1).max(50),
  backup_codigo: z.string().min(1),
  fecha_verificacion: z.string().min(1),
  algoritmo: z.enum(["sha256", "sha512", "blake3", "md5"]),
  integridad_ok: z.boolean(),
});

const e317 = z.object({
  codigo_prueba_bcp: z.string().min(1).max(50),
  fecha_prueba: z.string().min(1),
  tipo_prueba: z.enum(["tabletop", "walkthrough", "simulacion", "full_test"]),
  escenario_probado: z.string().min(1),
  resultado_global: z.enum([
    "satisfactorio", "satisfactorio_con_mejoras", "insatisfactorio",
  ]),
});

const e318 = z.object({
  codigo_ejercicio_drp: z.string().min(1).max(50),
  fecha_ejercicio: z.string().min(1),
  tipo_desastre_simulado: z.enum([
    "perdida_datacenter", "fallo_red", "fallo_servidor",
    "ataque_ransomware", "perdida_proveedor_cloud",
  ]),
  duracion_total_horas: z.number().min(0),
  resultado: z.enum(["ok", "ok_con_observaciones", "fallido"]),
});

const e319 = z.object({
  codigo_medicion: z.string().min(1).max(50),
  sistema_codigo: z.string().min(1),
  fecha_medicion: z.string().min(1),
  rto_objetivo_minutos: z.number().int().min(0),
  rto_real_minutos: z.number().int().min(0),
  rpo_objetivo_minutos: z.number().int().min(0),
  rpo_real_minutos: z.number().int().min(0),
  cumple_objetivos: z.boolean(),
});

const e320 = z.object({
  codigo_auditoria: z.string().min(1).max(50),
  fecha_inicio: z.string().min(1),
  alcance: z.string().min(1),
  auditor_interno: z.string().min(1).max(200),
  estado: z.enum(["planificada", "en_curso", "finalizada", "cancelada"]),
});

const e321 = z.object({
  codigo_auditoria_ext: z.string().min(1).max(50),
  entidad_acreditada: z.string().min(1).max(200),
  fecha_inicio: z.string().min(1),
  categoria_ens_evaluada: z.enum(["BASICA", "MEDIA", "ALTA"]),
  alcance: z.string().min(1),
});

const e322 = z.object({
  codigo_hallazgo: z.string().min(1).max(50),
  auditoria_codigo: z.string().min(1),
  severidad: z.enum(["mayor", "menor", "observacion"]),
  medida_ens_afectada: z.string().min(1),
  descripcion: z.string().min(1),
  accion_correctiva: z.string().min(1),
  responsable: z.string().min(1),
  fecha_compromiso: z.string().min(1),
  estado: z.enum([
    "abierto", "en_remediacion", "verificado_cerrado", "diferido",
  ]),
});

const e323 = z.object({
  codigo_acta: z.string().min(1).max(50),
  fecha_reunion: z.string().min(1),
  duracion_minutos: z.number().int().min(0),
});

const e324 = z.object({
  codigo_decision: z.string().min(1).max(50),
  acta_codigo: z.string().min(1),
  fecha_decision: z.string().min(1),
  asunto: z.string().min(1).max(300),
  descripcion: z.string().min(1),
  responsable_implementacion: z.string().min(1),
  estado: z.enum([
    "pendiente", "en_implementacion", "implementada", "diferida", "cancelada",
  ]),
});

const e325 = z.object({
  codigo_indicador: z.string().min(1).max(50),
  nombre: z.string().min(1).max(200),
  periodo: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/, "Periodo formato YYYY-MM"),
  valor: z.number(),
  unidad: z.string().min(1),
});


export const ENTRY_ZOD_SCHEMAS: Record<RegisterType, z.ZodObject<z.ZodRawShape>> = {
  "E-300": e300, "E-301": e301, "E-302": e302,
  "E-303": e303, "E-304": e304,
  "E-305": e305, "E-306": e306, "E-307": e307,
  "E-308": e308, "E-309": e309, "E-310": e310,
  "E-311": e311, "E-312": e312, "E-313": e313,
  "E-314": e314, "E-315": e315, "E-316": e316,
  "E-317": e317, "E-318": e318, "E-319": e319,
  "E-320": e320, "E-321": e321, "E-322": e322,
  "E-323": e323, "E-324": e324, "E-325": e325,
};


// ─── Field configs · drive dynamic form rendering ─────────────────────────


function t(key: string, label: string, required = false): FieldConfig {
  return { key, label, kind: "text", required };
}
function ta(key: string, label: string, required = false): FieldConfig {
  return { key, label, kind: "textarea", required };
}
function d(key: string, label: string, required = false): FieldConfig {
  return { key, label, kind: "date", required };
}
function dt(key: string, label: string, required = false): FieldConfig {
  return { key, label, kind: "datetime", required };
}
function n(key: string, label: string, required = false): FieldConfig {
  return { key, label, kind: "number", required };
}
function s(key: string, label: string, options: readonly string[], required = false): FieldConfig {
  return { key, label, kind: "select", options, required };
}
function b(key: string, label: string): FieldConfig {
  return { key, label, kind: "boolean" };
}


export const FIELD_CONFIGS: Record<RegisterType, readonly FieldConfig[]> = {
  "E-300": [
    t("codigo_activo", "Código activo", true),
    t("nombre", "Nombre", true),
    s("categoria_activo", "Categoría", ["hardware", "software", "datos", "comunicaciones", "instalaciones", "personal", "servicios"], true),
    t("propietario", "Propietario", true),
    t("ubicacion", "Ubicación", true),
    s("criticidad", "Criticidad", ["alta", "media", "baja"], true),
    d("fecha_alta", "Fecha alta", true),
    d("fecha_baja", "Fecha baja"),
    ta("observaciones", "Observaciones"),
  ],
  "E-301": [
    t("codigo_sistema", "Código sistema", true),
    t("nombre", "Nombre", true),
    s("tipo_sistema", "Tipo", ["produccion", "preproduccion", "desarrollo", "test", "respaldo", "monitorizacion"], true),
    s("categoria_ens", "Categoría ENS", ["BASICA", "MEDIA", "ALTA"], true),
    t("responsable", "Responsable", true),
    d("fecha_alta", "Fecha alta", true),
    d("fecha_baja", "Fecha baja"),
  ],
  "E-302": [
    t("codigo_aplicacion", "Código aplicación", true),
    t("nombre", "Nombre", true),
    t("proveedor", "Proveedor", true),
    t("version", "Versión", true),
    s("tipo_licencia", "Tipo licencia", ["propietario", "open_source", "saas", "interno"], true),
    t("sistema_anfitrion", "Sistema anfitrión"),
    d("fecha_alta", "Fecha alta", true),
    d("fecha_baja", "Fecha baja"),
    b("procesa_datos_personales", "Procesa datos personales"),
  ],
  "E-303": [
    t("dni_hash", "DNI (hash)", true),
    t("nombre_completo", "Nombre completo", true),
    t("email_corporativo", "Email corporativo", true),
    t("rol_principal", "Rol principal", true),
    t("departamento", "Departamento", true),
    d("fecha_alta_organizacion", "Fecha alta", true),
    d("fecha_baja_organizacion", "Fecha baja"),
    b("formacion_ens_completada", "Formación ENS completada"),
  ],
  "E-304": [
    t("empleado_dni_hash", "Empleado (DNI hash)", true),
    t("sistema_codigo", "Sistema", true),
    t("rol_asignado", "Rol", true),
    d("fecha_alta_acceso", "Fecha alta acceso", true),
    d("fecha_baja_acceso", "Fecha baja acceso"),
    t("aprobador", "Aprobador", true),
    ta("justificacion", "Justificación"),
  ],
  "E-305": [
    t("codigo_incidente", "Código incidente", true),
    dt("fecha_deteccion", "Fecha detección", true),
    s("nivel_criticidad", "Nivel criticidad", ["critico", "alto", "medio", "bajo", "informativo"], true),
    t("descripcion_breve", "Descripción breve", true),
    ta("descripcion_detallada", "Descripción detallada", true),
    s("fase_nist", "Fase NIST", ["preparacion", "deteccion", "contencion", "erradicacion", "recuperacion", "lecciones_aprendidas"], true),
    b("notificado_lucia", "Notificado a LUCIA"),
    b("notificado_aepd", "Notificado a AEPD"),
  ],
  "E-306": [
    t("codigo_vulnerabilidad", "Código vulnerabilidad", true),
    t("cve_id", "CVE ID"),
    n("cvss_score", "CVSS Score (0-10)"),
    ta("descripcion", "Descripción", true),
    d("fecha_deteccion", "Fecha detección", true),
    s("estado", "Estado", ["detectada", "en_remediacion", "mitigada", "cerrada", "aceptada"], true),
  ],
  "E-307": [
    t("codigo_notificacion", "Código notificación", true),
    s("autoridad", "Autoridad", ["lucia", "aepd", "ccn_cert", "incibe", "otro"], true),
    t("incidente_codigo", "Código incidente", true),
    dt("fecha_notificacion", "Fecha notificación", true),
    n("plazo_legal_horas", "Plazo legal (horas)", true),
    b("cumplido_en_plazo", "Cumplido en plazo"),
    s("estado_respuesta", "Estado respuesta", ["pendiente", "recibida_ack", "investigacion", "cerrada"], true),
  ],
  "E-308": [
    t("codigo_cambio", "Código cambio", true),
    s("tipo_cambio", "Tipo", ["estandar", "normal", "urgente", "emergencia"], true),
    ta("descripcion", "Descripción", true),
    d("fecha_solicitud", "Fecha solicitud", true),
    t("solicitante", "Solicitante", true),
  ],
  "E-309": [
    t("codigo_cambio_material", "Código cambio material", true),
    ta("descripcion", "Descripción", true),
    s("impacto_categoria_ens", "Impacto categoría", ["ninguno", "elevacion_basica_media", "elevacion_media_alta", "rebaja", "cambio_alcance"], true),
    b("requiere_notificacion_entidad_acreditada", "Requiere notificar entidad acreditada"),
    d("fecha_cambio", "Fecha cambio", true),
    b("aprobado_comite", "Aprobado por Comité"),
  ],
  "E-310": [
    t("codigo_excepcion", "Código excepción", true),
    t("medida_ens", "Medida ENS", true),
    ta("motivo", "Motivo", true),
    d("fecha_aprobacion", "Fecha aprobación", true),
    d("fecha_revision", "Fecha revisión", true),
    t("aprobador", "Aprobador", true),
    s("estado", "Estado", ["activa", "en_revision", "cerrada_resuelta", "cerrada_no_aplicable"], true),
  ],
  "E-311": [
    t("codigo_proveedor", "Código proveedor", true),
    t("razon_social", "Razón social", true),
    t("cif", "CIF", true),
    t("pais", "País (ISO-2)", true),
    t("tipo_servicio", "Tipo servicio", true),
    s("criticidad", "Criticidad", ["alta", "media", "baja"], true),
    d("fecha_alta", "Fecha alta", true),
    b("procesa_datos_personales", "Procesa datos personales"),
  ],
  "E-312": [
    t("codigo_evaluacion", "Código evaluación", true),
    t("proveedor_codigo", "Proveedor", true),
    t("periodo", "Periodo", true),
    d("fecha_evaluacion", "Fecha evaluación", true),
    n("puntuacion_global", "Puntuación (0-10)", true),
    t("evaluador", "Evaluador", true),
    s("decision", "Decisión", ["renovar", "renegociar", "rescindir", "monitorizar"], true),
  ],
  "E-313": [
    t("codigo_adenda", "Código adenda", true),
    t("proveedor_codigo", "Proveedor", true),
    s("tipo_adenda", "Tipo", ["dpa_rgpd", "sla_ens", "cybersec", "confidencialidad", "subprocesadores"], true),
    d("fecha_firma", "Fecha firma", true),
    d("fecha_inicio_vigencia", "Inicio vigencia", true),
    t("firmante_proveedor", "Firmante proveedor", true),
    t("firmante_cliente", "Firmante cliente", true),
  ],
  "E-314": [
    t("codigo_backup", "Código backup", true),
    t("sistema_codigo", "Sistema", true),
    dt("fecha_ejecucion", "Fecha ejecución", true),
    s("tipo_backup", "Tipo", ["completo", "incremental", "diferencial", "snapshot"], true),
    n("tamano_gb", "Tamaño (GB)", true),
    n("duracion_minutos", "Duración (min)", true),
    s("resultado", "Resultado", ["ok", "warning", "failed"], true),
    t("ubicacion_destino", "Destino", true),
    b("cifrado", "Cifrado"),
  ],
  "E-315": [
    t("codigo_prueba", "Código prueba", true),
    t("backup_codigo", "Backup", true),
    d("fecha_prueba", "Fecha prueba", true),
    s("tipo_restauracion", "Tipo", ["total", "parcial", "punto_en_tiempo"], true),
    n("duracion_minutos", "Duración (min)", true),
    s("resultado", "Resultado", ["ok", "ok_con_issues", "fallida"], true),
    t("operador", "Operador", true),
  ],
  "E-316": [
    t("codigo_verificacion", "Código verificación", true),
    t("backup_codigo", "Backup", true),
    d("fecha_verificacion", "Fecha verificación", true),
    s("algoritmo", "Algoritmo", ["sha256", "sha512", "blake3", "md5"], true),
    b("integridad_ok", "Integridad OK"),
  ],
  "E-317": [
    t("codigo_prueba_bcp", "Código prueba BCP", true),
    d("fecha_prueba", "Fecha prueba", true),
    s("tipo_prueba", "Tipo", ["tabletop", "walkthrough", "simulacion", "full_test"], true),
    ta("escenario_probado", "Escenario", true),
    s("resultado_global", "Resultado", ["satisfactorio", "satisfactorio_con_mejoras", "insatisfactorio"], true),
  ],
  "E-318": [
    t("codigo_ejercicio_drp", "Código ejercicio DRP", true),
    d("fecha_ejercicio", "Fecha ejercicio", true),
    s("tipo_desastre_simulado", "Desastre simulado", ["perdida_datacenter", "fallo_red", "fallo_servidor", "ataque_ransomware", "perdida_proveedor_cloud"], true),
    n("duracion_total_horas", "Duración (horas)", true),
    s("resultado", "Resultado", ["ok", "ok_con_observaciones", "fallido"], true),
  ],
  "E-319": [
    t("codigo_medicion", "Código medición", true),
    t("sistema_codigo", "Sistema", true),
    d("fecha_medicion", "Fecha medición", true),
    n("rto_objetivo_minutos", "RTO objetivo (min)", true),
    n("rto_real_minutos", "RTO real (min)", true),
    n("rpo_objetivo_minutos", "RPO objetivo (min)", true),
    n("rpo_real_minutos", "RPO real (min)", true),
    b("cumple_objetivos", "Cumple objetivos"),
  ],
  "E-320": [
    t("codigo_auditoria", "Código auditoría", true),
    d("fecha_inicio", "Fecha inicio", true),
    ta("alcance", "Alcance", true),
    t("auditor_interno", "Auditor interno", true),
    s("estado", "Estado", ["planificada", "en_curso", "finalizada", "cancelada"], true),
  ],
  "E-321": [
    t("codigo_auditoria_ext", "Código auditoría externa", true),
    t("entidad_acreditada", "Entidad acreditada ENAC", true),
    d("fecha_inicio", "Fecha inicio", true),
    s("categoria_ens_evaluada", "Categoría evaluada", ["BASICA", "MEDIA", "ALTA"], true),
    ta("alcance", "Alcance", true),
  ],
  "E-322": [
    t("codigo_hallazgo", "Código hallazgo", true),
    t("auditoria_codigo", "Auditoría", true),
    s("severidad", "Severidad", ["mayor", "menor", "observacion"], true),
    t("medida_ens_afectada", "Medida ENS afectada", true),
    ta("descripcion", "Descripción", true),
    ta("accion_correctiva", "Acción correctiva", true),
    t("responsable", "Responsable", true),
    d("fecha_compromiso", "Fecha compromiso", true),
    s("estado", "Estado", ["abierto", "en_remediacion", "verificado_cerrado", "diferido"], true),
  ],
  "E-323": [
    t("codigo_acta", "Código acta", true),
    d("fecha_reunion", "Fecha reunión", true),
    n("duracion_minutos", "Duración (min)", true),
  ],
  "E-324": [
    t("codigo_decision", "Código decisión", true),
    t("acta_codigo", "Acta", true),
    d("fecha_decision", "Fecha decisión", true),
    t("asunto", "Asunto", true),
    ta("descripcion", "Descripción", true),
    t("responsable_implementacion", "Responsable", true),
    s("estado", "Estado", ["pendiente", "en_implementacion", "implementada", "diferida", "cancelada"], true),
  ],
  "E-325": [
    t("codigo_indicador", "Código indicador", true),
    t("nombre", "Nombre", true),
    t("periodo", "Periodo (YYYY-MM)", true),
    n("valor", "Valor", true),
    t("unidad", "Unidad", true),
  ],
};


export function getZodSchema(registerType: RegisterType): z.ZodObject<z.ZodRawShape> {
  return ENTRY_ZOD_SCHEMAS[registerType];
}


export function getFieldConfig(registerType: RegisterType): readonly FieldConfig[] {
  return FIELD_CONFIGS[registerType];
}
