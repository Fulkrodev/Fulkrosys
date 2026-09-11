/**
 * API client · sub-atom 1.D.F.0.A v3.11 · ProjectDiagnosticoWizard.
 *
 * Endpoint atomic: POST /api/v1/admin/diagnostico-wizard/create-project
 * Crea cliente + proyecto + dims + M01 system + M02 magerit + departments
 * + cockpit user en 1 transacción.
 */
import { api } from "@/lib/api";

export type SectorEns =
  | "aapp"
  | "privado_licita_aapp"
  | "privado_proveedor_aapp"
  | "otros";

export type TipoOrganizacion =
  | "pyme"
  | "gran_empresa"
  | "sector_publico"
  | "ong";

export type TamanoEmpleados =
  | "micro"
  | "pequeno"
  | "mediano"
  | "grande"
  | "enterprise";

export type Arquitectura =
  | "on_premise"
  | "hibrido"
  | "cloud_native"
  | "multi_cloud"
  | "hyperscaler";

export type DpoDesignado = "interno" | "externo" | "no_designado";
export type EquipoTiTamano = "sin_equipo" | "1_3" | "4_10" | "11_30" | "gt30";
export type Geografia = "spain" | "ue" | "global" | "apac" | "latam";
/** N1 · NO_AFECTADA no es un nivel, es la ausencia de adscripcion.
 *  RD 311/2022 Anexo I punto 3: "Si una dimension de seguridad no se ve
 *  afectada, no se adscribira a ningun nivel". Antes no existia y las cinco
 *  dimensiones arrancaban en BAJO, arrastrando medidas que la norma no exige. */
export type ImpactLevel = "NO_AFECTADA" | "BAJO" | "MEDIO" | "ALTO";
export type Categoria = "BASICA" | "MEDIA" | "ALTA";
export type ActivoTipo =
  | "datos"
  | "servicios"
  | "infraestructura"
  | "software"
  | "personal";

export interface Step1DatosCliente {
  razon_social: string;
  cif: string;
  sector_industrial?: string | null;
  domicilio_fiscal?: string | null;
  web?: string | null;
  contacto_email?: string | null;
  contacto_telefono?: string | null;
  persona_contacto?: string | null;
}

export interface Step2ContextoENS {
  sector_ens: SectorEns;
  tipo_organizacion: TipoOrganizacion;
  tamano_empleados: TamanoEmpleados;
  sites_oficinas: number;
  it_interno: boolean;
  ciso_interno: boolean;
  dpo_designado: DpoDesignado;
  equipo_ti_tamano: EquipoTiTamano;
  geografia_operacion: Geografia;
  arquitectura_sistemas: Arquitectura;
}

export interface EnsDimsValoracion {
  confidencialidad: ImpactLevel;
  integridad: ImpactLevel;
  disponibilidad: ImpactLevel;
  autenticidad: ImpactLevel;
  trazabilidad: ImpactLevel;
}

export interface Step3CategoriaPreliminar {
  categoria_preliminar: Categoria;
  dims_anexo_i: EnsDimsValoracion;
  justificacion?: string | null;
  // #5 (Sub-bloque E) · suelo de categoría heredado de la AAPP contratante
  // (null = sin herencia). Marcos lo fija desde el pliego/contrato (decisión A).
  // Piso DURO: eleva categoria_objetivo (solo sube). Sibling de papel_aapp.
  categoria_heredada_aapp?: Categoria | null;
}

export interface ActivoCritico {
  nombre: string;
  tipo: ActivoTipo;
  descripcion?: string | null;
}

export interface Step4ActivosCriticos {
  activos: ActivoCritico[];
  dependencias_cloud: string[];
}

export interface Step5FirstUser {
  email: string;
  full_name: string;
  cargo?: string | null;
  send_magic_link: boolean;
}

export interface CreateProjectDiagnosticoRequest {
  step1_datos_cliente: Step1DatosCliente;
  step2_contexto_ens: Step2ContextoENS;
  step3_categoria: Step3CategoriaPreliminar;
  step4_activos: Step4ActivosCriticos;
  step5_first_user: Step5FirstUser;
  // #7.5 · lead origen (hidratación). Si el lead tiene proyecto ligero, se
  // promueve ese mismo (decisión 2-A · no duplica).
  lead_id?: string | null;
}

// #7.5 · prefill del wizard desde un lead (hidratación).
export interface WizardPrefillResponse {
  lead_id: string;
  razon_social?: string | null;
  cif?: string | null;
  sector_industrial?: string | null;
  contacto_email?: string | null;
  contacto_telefono?: string | null;
  // lead.categoria_objetivo_ens es String(20) libre en backend (no enum
  // validado) → tipado honesto como string, no Categoria.
  categoria_preliminar?: string | null;
  papel_aapp?: string | null;
  has_lightweight_project: boolean;
}

export interface CreateProjectDiagnosticoResponse {
  client_id: string;
  project_id: string;
  magerit_analysis_id: string | null;
  initial_system_id: string | null;
  initial_information_type_id: string | null;
  cockpit_user_id: string | null;
  departments_created_count: number;
  magic_link_sent: boolean;
  dims_captured_count: number;
  summary: string;
}

export const projectDiagnosticoApi = {
  createProjectWithDiagnosis: (body: CreateProjectDiagnosticoRequest) =>
    api<CreateProjectDiagnosticoResponse>(
      "/api/v1/admin/diagnostico-wizard/create-project",
      { json: body },
    ),
  // #7.5 · prefill del wizard desde un lead (hidratación).
  prefillFromLead: (leadId: string) =>
    api<WizardPrefillResponse>(
      `/api/v1/admin/diagnostico-wizard/prefill?lead_id=${encodeURIComponent(leadId)}`,
    ),
};

// ════════════════════════════════════════════════════════════════════
// Labels for UI (TooltipENS-friendly per term)
// ════════════════════════════════════════════════════════════════════

export const SECTOR_ENS_LABELS: Record<SectorEns, string> = {
  aapp: "AAPP directa",
  privado_licita_aapp: "Privado licita AAPP",
  privado_proveedor_aapp: "Privado proveedor AAPP",
  otros: "Otros",
};

export const TIPO_ORG_LABELS: Record<TipoOrganizacion, string> = {
  pyme: "PYME",
  gran_empresa: "Gran empresa",
  sector_publico: "Sector público",
  ong: "ONG",
};

export const TAMANO_EMPLEADOS_LABELS: Record<TamanoEmpleados, string> = {
  micro: "Micro (<10)",
  pequeno: "Pequeña (10-50)",
  mediano: "Mediana (50-250)",
  grande: "Grande (250-1000)",
  enterprise: "Enterprise (1000+)",
};

export const EQUIPO_TI_LABELS: Record<EquipoTiTamano, string> = {
  sin_equipo: "Sin equipo TI propio",
  "1_3": "1-3 personas",
  "4_10": "4-10 personas",
  "11_30": "11-30 personas",
  gt30: "Más de 30",
};

export const ARQUITECTURA_LABELS: Record<Arquitectura, string> = {
  on_premise: "On-premise",
  hibrido: "Híbrido",
  cloud_native: "Cloud-native",
  multi_cloud: "Multi-cloud",
  hyperscaler: "Hyperscaler único",
};

export const DPO_LABELS: Record<DpoDesignado, string> = {
  interno: "DPO interno designado",
  externo: "DPO externo contratado",
  no_designado: "Sin DPO designado",
};

export const GEOGRAFIA_LABELS: Record<Geografia, string> = {
  spain: "España",
  ue: "Unión Europea",
  global: "Global",
  apac: "Asia-Pacífico",
  latam: "Latinoamérica",
};

export const CATEGORIA_LABELS: Record<Categoria, string> = {
  BASICA: "BÁSICA",
  MEDIA: "MEDIA",
  ALTA: "ALTA",
};

export const ACTIVO_TIPO_LABELS: Record<ActivoTipo, string> = {
  datos: "Datos / Información",
  servicios: "Servicios",
  infraestructura: "Infraestructura",
  software: "Software / Aplicaciones",
  personal: "Personal / Equipo",
};

export const IMPACT_LABELS: Record<ImpactLevel, string> = {
  NO_AFECTADA: "No afectada",
  BAJO: "Bajo",
  MEDIO: "Medio",
  ALTO: "Alto",
};

/**
 * 5 dimensiones ENS Anexo I · cada una se valora Bajo/Medio/Alto.
 * Glossario terms vinculables a glosario-ens.ts.
 */
export const ENS_DIM_LABELS = {
  confidencialidad: "Confidencialidad",
  integridad: "Integridad",
  disponibilidad: "Disponibilidad",
  autenticidad: "Autenticidad",
  trazabilidad: "Trazabilidad",
} as const;
