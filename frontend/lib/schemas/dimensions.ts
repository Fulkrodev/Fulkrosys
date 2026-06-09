/**
 * Zod schemas · M01 Dimensions (sub-atom 1.C.D.A.0.2 v3.8).
 *
 * Mirror exacto de Pydantic backend (ProjectDimensionsUpdate). Defaults
 * coinciden con backend CHECK constraints.
 */
import { z } from "zod";

export const TamanoEmpleadosEnum = z.enum([
  "micro",
  "pequeno",
  "mediano",
  "grande",
  "enterprise",
]);
export const MadurezEnsEnum = z.enum(["L0", "L1", "L2", "L3", "L4", "L5"]);
export const GeografiaEnum = z.enum(["spain", "ue", "global", "apac", "latam"]);
export const AplicaNis2Enum = z.enum(["no", "esencial", "importante"]);
export const AplicaDoraEnum = z.enum([
  "no",
  "entidad_financiera",
  "proveedor_ict_critico",
]);
export const AplicaAiActEnum = z.enum([
  "no",
  "alto_riesgo",
  "gpai",
  "limitado",
]);
export const DpoDesignadoEnum = z.enum(["interno", "externo", "no_designado"]);
export const ArquitecturaEnum = z.enum([
  "on_premise",
  "hibrido",
  "cloud_native",
  "multi_cloud",
  "hyperscaler",
]);
export const MultiTenancyEnum = z.enum([
  "single",
  "multi_tenant",
  "marketplace",
]);
export const EquipoTiTamanoEnum = z.enum([
  "sin_equipo",
  "1_3",
  "4_10",
  "11_30",
  "gt30",
]);
export const UrgenciaEnum = z.enum([
  "no_urge",
  "6m",
  "3m",
  "1m",
  "urgent_30d",
]);
export const PresupuestoEnum = z.enum([
  "minimo",
  "estandar",
  "generoso",
  "premium",
]);
export const CompromisoEnum = z.enum([
  "proactivo",
  "reactivo",
  "reluctante",
]);
export const HorasSemanaEnum = z.enum([
  "lt5h",
  "5_15h",
  "15_40h",
  "full_time",
]);

export const CertificacionPreviaEnum = z.enum([
  "ISO27001",
  "SOC2",
  "PCI-DSS",
  "ENS-expirado",
  "HIPAA",
  "GDPR-cert",
  "ninguna",
]);

// Form wizard schema (16 dims editables · 3 dims existing read-only desde page)
export const DimensionsWizardSchema = z.object({
  // Step 1: Empresa básica
  tamano_empleados: TamanoEmpleadosEnum,
  geografia_operacion: GeografiaEnum,
  // Step 2: Madurez actual
  madurez_ens_actual: MadurezEnsEnum,
  certificaciones_previas: z.array(z.string()).default([]),
  equipo_ti_tamano: EquipoTiTamanoEnum,
  dpo_designado: DpoDesignadoEnum,
  // Step 3: Marcos legales
  aplica_nis2: AplicaNis2Enum,
  aplica_dora: AplicaDoraEnum,
  aplica_ai_act: AplicaAiActEnum,
  procesa_datos_sensibles_rgpd9: z.boolean(),
  // Step 4: Arquitectura
  arquitectura_sistemas: ArquitecturaEnum,
  multi_tenancy: MultiTenancyEnum,
  // Step 5: Operacional
  urgencia_certificacion: UrgenciaEnum,
  presupuesto_disponible: PresupuestoEnum,
  compromiso_interno: CompromisoEnum,
  horas_cliente_semana: HorasSemanaEnum,
});

export type DimensionsWizardFormValues = z.infer<typeof DimensionsWizardSchema>;

// === Labels human-friendly para forms · español ===

export const TAMANO_EMPLEADOS_LABELS: Record<
  z.infer<typeof TamanoEmpleadosEnum>,
  string
> = {
  micro: "Micro (<10 empleados)",
  pequeno: "Pequeña (10-50)",
  mediano: "Mediana (50-200)",
  grande: "Grande (200-500)",
  enterprise: "Enterprise (>500)",
};

export const MADUREZ_ENS_LABELS: Record<
  z.infer<typeof MadurezEnsEnum>,
  string
> = {
  L0: "L0 · sin ENS · cero implementado",
  L1: "L1 · inicial ad-hoc · procesos informales",
  L2: "L2 · repetible · procesos básicos documentados",
  L3: "L3 · definido · políticas + procedimientos completos",
  L4: "L4 · gestionado · métricas + indicadores",
  L5: "L5 · optimizado · mejora continua",
};

export const GEOGRAFIA_LABELS: Record<z.infer<typeof GeografiaEnum>, string> = {
  spain: "España",
  ue: "Unión Europea",
  global: "Global",
  apac: "Asia-Pacífico",
  latam: "Latinoamérica",
};

export const APLICA_NIS2_LABELS: Record<
  z.infer<typeof AplicaNis2Enum>,
  string
> = {
  no: "No aplica",
  esencial: "Sí · entidad esencial",
  importante: "Sí · entidad importante",
};

export const APLICA_DORA_LABELS: Record<
  z.infer<typeof AplicaDoraEnum>,
  string
> = {
  no: "No aplica",
  entidad_financiera: "Sí · entidad financiera regulada",
  proveedor_ict_critico: "Sí · proveedor ICT crítico de entidad financiera",
};

export const APLICA_AI_ACT_LABELS: Record<
  z.infer<typeof AplicaAiActEnum>,
  string
> = {
  no: "No aplica",
  alto_riesgo: "Alto riesgo · Anexo III",
  gpai: "GPAI · modelo propósito general",
  limitado: "Riesgo limitado · obligaciones transparencia",
};

export const DPO_LABELS: Record<z.infer<typeof DpoDesignadoEnum>, string> = {
  interno: "DPO interno designado",
  externo: "DPO externo contratado",
  no_designado: "No designado",
};

export const ARQUITECTURA_LABELS: Record<
  z.infer<typeof ArquitecturaEnum>,
  string
> = {
  on_premise: "On-premise (servidores propios)",
  hibrido: "Híbrido (on-premise + cloud)",
  cloud_native: "Cloud-native (SaaS · serverless)",
  multi_cloud: "Multi-cloud (2+ proveedores)",
  hyperscaler: "Hyperscaler (AWS · GCP · Azure exclusivo)",
};

export const MULTI_TENANCY_LABELS: Record<
  z.infer<typeof MultiTenancyEnum>,
  string
> = {
  single: "Single-tenant (un cliente por instancia)",
  multi_tenant: "Multi-tenant (múltiples clientes compartidos)",
  marketplace: "Marketplace · agregador",
};

export const EQUIPO_TI_LABELS: Record<
  z.infer<typeof EquipoTiTamanoEnum>,
  string
> = {
  sin_equipo: "Sin equipo TI propio (externalizado completo)",
  "1_3": "Pequeño (1-3 personas)",
  "4_10": "Mediano (4-10 personas)",
  "11_30": "Grande (11-30 personas)",
  gt30: "Enterprise (>30 personas)",
};

export const URGENCIA_LABELS: Record<z.infer<typeof UrgenciaEnum>, string> = {
  no_urge: "Sin urgencia · planificación tranquila",
  "6m": "Target 6 meses",
  "3m": "Target 3 meses",
  "1m": "Target 1 mes",
  urgent_30d: "URGENTE · <30 días (sólo si imprescindible)",
};

export const PRESUPUESTO_LABELS: Record<
  z.infer<typeof PresupuestoEnum>,
  string
> = {
  minimo: "Mínimo · sólo imprescindible",
  estandar: "Estándar · tarifa habitual",
  generoso: "Generoso · permite herramientas premium",
  premium: "Premium · sin restricciones",
};

export const COMPROMISO_LABELS: Record<
  z.infer<typeof CompromisoEnum>,
  string
> = {
  proactivo: "Proactivo · cliente lidera el proceso",
  reactivo: "Reactivo · responde cuando se le pide",
  reluctante: "Reluctante · cumple por obligación",
};

export const HORAS_SEMANA_LABELS: Record<
  z.infer<typeof HorasSemanaEnum>,
  string
> = {
  lt5h: "Menos de 5h/semana",
  "5_15h": "5-15h/semana (típico)",
  "15_40h": "15-40h/semana (intensivo)",
  full_time: "Full-time · dedicado al proyecto",
};

// === Tooltips ENS contextuales (R30 sostenido · asume cero ENS) ===

export const DIMENSION_TOOLTIPS: Record<string, string> = {
  madurez_ens_actual:
    "Nivel de madurez ENS actual. L0 = no implementado nada · L5 = ENS optimizado con mejora continua. Auditor evalúa salto desde L actual hasta target requerido por categoría.",
  aplica_nis2:
    "Directiva UE 2022/2555 sobre ciberseguridad. Aplica si la empresa opera en sectores críticos (energía · sanidad · transporte · banca · admin pública · digital infrastructure). Esencial > Importante según tamaño + sector.",
  aplica_dora:
    "Reglamento UE 2022/2554 sobre resiliencia operativa digital del sector financiero. Aplica si tu empresa procesa servicios financieros o es proveedor ICT crítico de entidades financieras.",
  aplica_ai_act:
    "Reglamento UE 2024/1689 sobre IA. Alto riesgo = sistemas IA en Anexo III (recursos humanos · credit scoring · law enforcement · etc). GPAI = modelos propósito general. Limitado = chatbots públicos requieren transparencia.",
  procesa_datos_sensibles_rgpd9:
    "Datos especiales RGPD art.9 · biométricos · salud · político · religioso · sexual orientation · racial · sindical · genético. Si procesas alguno · DPIA (Data Protection Impact Assessment) es obligatorio + DPO recomendado.",
  dpo_designado:
    "Data Protection Officer (RGPD art.37-39). Obligatorio si procesas datos especiales a gran escala · monitorización sistemática · admin pública. Puede ser interno o externo (consultor).",
  arquitectura_sistemas:
    "Modelo arquitectónico predominante de los sistemas a certificar. Afecta scope pentest · controles infra · responsabilidades proveedor cloud (modelo responsabilidad compartida).",
  multi_tenancy:
    "Si una instancia atiende a múltiples clientes (multi-tenant) requiere controles adicionales de isolación · separación datos · etc. (ENS Anexo II mp.com.4 + mp.info.*).",
  equipo_ti_tamano:
    "Tamaño del equipo TI propio del cliente. Si sin_equipo · Marcos asume responsable TI virtual con riesgo mayor. Afecta velocidad implementación + responsable RACI.",
  certificaciones_previas:
    "Certificaciones de ciberseguridad/calidad previas. ISO 27001 · SOC2 · PCI-DSS · etc. Permiten reuso evidencias + procedimientos · acelerar implementación ENS.",
  urgencia_certificacion:
    "Plazo objetivo certificación ENS. <30 días = altísimo riesgo · puede requerir +30% urgencia tarifa. 6m es plazo típico saludable.",
  presupuesto_disponible:
    "Presupuesto disponible para el proyecto. Afecta scope de herramientas premium (pentest profundo · DLP · SIEM · etc) y plantillas premium.",
  compromiso_interno:
    "Cuán implicado/comprometido está el cliente con el proceso. Reluctante = cumple por obligación legal · proactivo = quiere mejorar genuinamente. Marcos adapta approach.",
  horas_cliente_semana:
    "Horas que el cliente dedicará al proyecto ENS por semana. Lt5h = proyecto muy lento (12+ meses) · 15-40h = pace intensivo (3-4 meses cierre).",
};
