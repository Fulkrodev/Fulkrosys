/**
 * Continuidad de negocio (BIA/DRP) · cliente API client · feat/fulkro-100.
 *
 * Endpoints backend (ADR-013 require_client_user · cliente-mínimo):
 *   GET  /client-portal/continuidad/questionnaire        · lee su cuestionario
 *   POST /client-portal/continuidad/questionnaire        · guarda/actualiza
 *   GET  /client-portal/continuidad/drafts               · borradores BIA/DRP de Marcos
 *   POST /client-portal/continuidad/drafts/{id}/approve  · APRUEBA (binding)
 *   POST /client-portal/continuidad/drafts/{id}/comment  · solicita cambios
 *
 * R29 cliente-friendly. Sync admin↔cliente realtime (SSE continuidad.*).
 */
import { clientApi } from "@/lib/client-portal-api";

export interface ProcesoCritico {
  nombre: string;
  descripcion?: string | null;
}

export interface ActivoCore {
  nombre: string;
  tipo?: string | null;
}

export interface ContinuidadQuestionnaire {
  id: string;
  project_id: string;
  submitted_at: string;
  updated_at: string;
  procesos_criticos?: ProcesoCritico[] | null;
  rto_horas_tolerancia?: number | null;
  rpo_horas_tolerancia?: number | null;
  impacto_diario_eur?: string | null;
  activos_core?: ActivoCore[] | null;
  notas_cliente?: string | null;
  completed: boolean;
}

export interface ContinuidadQuestionnaireInput {
  procesos_criticos?: ProcesoCritico[];
  rto_horas_tolerancia?: number | null;
  rpo_horas_tolerancia?: number | null;
  // Same representation as the read model (Numeric serialized as string).
  // Backend accepts a numeric string for its Decimal field, so read+write agree.
  impacto_diario_eur?: string | null;
  activos_core?: ActivoCore[];
  notas_cliente?: string | null;
  completed: boolean;
}

export interface ContinuidadDraft {
  artifact_type: string; // "bia" | "drp"
  draft_id: string;
  summary: string;
  rto_hours?: number | null;
  rpo_hours?: number | null;
  daily_impact_eur?: string | null;
}

export interface ContinuidadApproval {
  id: string;
  artifact_type: string;
  draft_id?: string | null;
  action: string;
  comment_text?: string | null;
  created_at: string;
}

export const continuidadApi = {
  getQuestionnaire: () =>
    clientApi<ContinuidadQuestionnaire | null>(
      "/client-portal/continuidad/questionnaire",
    ),
  saveQuestionnaire: (input: ContinuidadQuestionnaireInput) =>
    clientApi<ContinuidadQuestionnaire>(
      "/client-portal/continuidad/questionnaire",
      { json: input },
    ),
  listDrafts: () =>
    clientApi<{ drafts: ContinuidadDraft[] }>(
      "/client-portal/continuidad/drafts",
    ),
  approveDraft: (draftId: string, artifactType: string, comment?: string) =>
    clientApi<ContinuidadApproval>(
      `/client-portal/continuidad/drafts/${draftId}/approve`,
      { json: { artifact_type: artifactType, comment_text: comment ?? null } },
    ),
  commentDraft: (draftId: string, artifactType: string, comment: string) =>
    clientApi<ContinuidadApproval>(
      `/client-portal/continuidad/drafts/${draftId}/comment`,
      { json: { artifact_type: artifactType, comment_text: comment } },
    ),
};
