/**
 * API client · Motor 28 Change Governance.
 *
 * Endpoints servidos desde m28 con prefix `/api/v1/changes`:
 *   GET  /api/v1/changes/projects/{id}/changes/open
 *   POST /api/v1/changes/projects/{id}/changes
 *   POST /api/v1/changes/projects/{id}/changes/{cid}/assess
 *   GET  /api/v1/changes/projects/{id}/changes/{cid}/impact
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/changes";

export type MaterialityLevel = "MINOR" | "RELEVANT" | "MATERIAL";

export interface OpenChangeItem {
  change_id: string;
  state: string;
  description: string;
}

export interface ChangeIntakeBody {
  description: string;
  requested_by: string;
  proposed_date?: string | null;
}

export interface ChangeIntakeResponse {
  change_id: string;
  state: string;
}

export interface ChangeAssessmentOut {
  change_id: string;
  project_id: string;
  description: string;
  materiality_level: MaterialityLevel;
  materiality_score: number;
  impact_vector: Record<string, boolean>;
  required_documents: string[];
  required_workflows: string[];
  required_signoffs: string[];
  customer_actions: string[];
  deadline_policy: string;
  assessed_at: string;
}

export interface ChangeImpactDetail {
  change_id: string;
  impact_vector: Record<string, boolean>;
  materiality_level: MaterialityLevel;
  materiality_score: number;
}

/**
 * Sub-atom 1.D.D.B v3.11 · 10 binary questions canónicas del materiality
 * engine (m28.materiality_engine.IMPACT_QUESTIONS). MUST permanecer
 * sincronizado con backend — ver Anexo K matriz centralizada pattern
 * (1.C.C.B.fix) y constants.py m_live_records.
 */
export const IMPACT_QUESTIONS = [
  "affects_evidence",
  "affects_documentation",
  "affects_controls",
  "affects_overlay",
  "affects_roles",
  "affects_risk_analysis",
  "affects_dda",
  "affects_category",
  "affects_renewal",
  "requires_extraordinary",
] as const;

export type ImpactQuestion = (typeof IMPACT_QUESTIONS)[number];

export const IMPACT_QUESTION_LABELS: Record<ImpactQuestion, string> = {
  affects_evidence: "¿Afecta a las evidencias del SGSI?",
  affects_documentation:
    "¿Afecta a la documentación oficial (políticas / procedimientos)?",
  affects_controls: "¿Afecta a los controles implementados?",
  affects_overlay: "¿Afecta a algún overlay sectorial (RGPD / DORA / NIS2)?",
  affects_roles: "¿Afecta a los roles o responsabilidades del SGSI?",
  affects_risk_analysis: "¿Afecta al análisis de riesgos (MAGERIT)?",
  affects_dda: "¿Afecta a la Declaración de Aplicabilidad (DdA)?",
  affects_category: "¿Cambia la categoría ENS del sistema?",
  affects_renewal: "¿Afecta a la renovación de la certificación?",
  requires_extraordinary: "¿Requiere auditoría extraordinaria?",
};

export const MATERIALITY_LEVEL_LABELS: Record<MaterialityLevel, string> = {
  MINOR: "Menor",
  RELEVANT: "Relevante",
  MATERIAL: "Material",
};

export const MATERIALITY_LEVEL_VARIANTS: Record<
  MaterialityLevel,
  "success" | "warning" | "danger"
> = {
  MINOR: "success",
  RELEVANT: "warning",
  MATERIAL: "danger",
};

export const CHANGE_STATE_LABELS: Record<string, string> = {
  intake: "En intake",
  assessed: "Evaluado",
  approved: "Aprobado",
  rejected: "Rechazado",
  closed: "Cerrado",
};

export const CHANGE_STATE_VARIANTS: Record<
  string,
  "secondary" | "warning" | "success" | "danger"
> = {
  intake: "secondary",
  assessed: "warning",
  approved: "success",
  rejected: "danger",
  closed: "secondary",
};

export const changesApi = {
  listOpen: (projectId: string) =>
    api<OpenChangeItem[]>(`${BASE}/projects/${projectId}/changes/open`),

  intake: (projectId: string, body: ChangeIntakeBody) =>
    api<ChangeIntakeResponse>(`${BASE}/projects/${projectId}/changes`, {
      json: body,
    }),

  assess: (
    projectId: string,
    changeId: string,
    answers: Record<string, boolean>,
  ) =>
    api<ChangeAssessmentOut>(
      `${BASE}/projects/${projectId}/changes/${changeId}/assess`,
      { json: { answers } },
    ),

  getImpact: (projectId: string, changeId: string) =>
    api<ChangeImpactDetail>(
      `${BASE}/projects/${projectId}/changes/${changeId}/impact`,
    ),
};
