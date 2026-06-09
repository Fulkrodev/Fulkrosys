/**
 * Frontend API · M01 Dimensions (sub-atom 1.C.D.A.0.2 v3.8).
 *
 * 19 dimensiones canónico · single source of truth `projects` table.
 *
 * - GET  /api/v1/projects/{id}/dimensions     (admin + cliente)
 * - PATCH /api/v1/admin/projects/{id}/dimensions  (Marcos only)
 *
 * OPS-044 sostenido · usamos `api()` wrapper que recibe path completo.
 */
import { api } from "@/lib/api";

export type TamanoEmpleados =
  | "micro"
  | "pequeno"
  | "mediano"
  | "grande"
  | "enterprise";
export type MadurezEns = "L0" | "L1" | "L2" | "L3" | "L4" | "L5";
export type Geografia = "spain" | "ue" | "global" | "apac" | "latam";
export type AplicaNis2 = "no" | "esencial" | "importante";
export type AplicaDora =
  | "no"
  | "entidad_financiera"
  | "proveedor_ict_critico";
export type AplicaAiAct = "no" | "alto_riesgo" | "gpai" | "limitado";
export type DpoDesignado = "interno" | "externo" | "no_designado";
export type Arquitectura =
  | "on_premise"
  | "hibrido"
  | "cloud_native"
  | "multi_cloud"
  | "hyperscaler";
export type MultiTenancy = "single" | "multi_tenant" | "marketplace";
export type EquipoTiTamano = "sin_equipo" | "1_3" | "4_10" | "11_30" | "gt30";
export type Urgencia = "no_urge" | "6m" | "3m" | "1m" | "urgent_30d";
export type Presupuesto = "minimo" | "estandar" | "generoso" | "premium";
export type Compromiso = "proactivo" | "reactivo" | "reluctante";
export type HorasSemana = "lt5h" | "5_15h" | "15_40h" | "full_time";

export interface ProjectDimensionsRead {
  categoria_objetivo: string | null;
  archetype: string | null;
  fase: string;
  tamano_empleados: TamanoEmpleados;
  madurez_ens_actual: MadurezEns;
  geografia_operacion: Geografia;
  procesa_datos_sensibles_rgpd9: boolean;
  aplica_nis2: AplicaNis2;
  aplica_dora: AplicaDora;
  aplica_ai_act: AplicaAiAct;
  dpo_designado: DpoDesignado;
  arquitectura_sistemas: Arquitectura;
  multi_tenancy: MultiTenancy;
  equipo_ti_tamano: EquipoTiTamano;
  certificaciones_previas: string[];
  urgencia_certificacion: Urgencia;
  presupuesto_disponible: Presupuesto;
  compromiso_interno: Compromiso;
  horas_cliente_semana: HorasSemana;
  dims_captured_count: number;
  dims_total: number;
}

export type ProjectDimensionsUpdate = Partial<
  Omit<
    ProjectDimensionsRead,
    | "categoria_objetivo"
    | "archetype"
    | "fase"
    | "dims_captured_count"
    | "dims_total"
  >
>;

export async function getProjectDimensions(
  projectId: string,
): Promise<ProjectDimensionsRead> {
  return api<ProjectDimensionsRead>(
    `/api/v1/projects/${projectId}/dimensions`,
  );
}

export async function updateProjectDimensions(
  projectId: string,
  payload: ProjectDimensionsUpdate,
): Promise<ProjectDimensionsRead> {
  return api<ProjectDimensionsRead>(
    `/api/v1/admin/projects/${projectId}/dimensions`,
    {
      method: "PATCH",
      json: payload,
    },
  );
}
