/**
 * Admin Meetings schemas TypeScript (sub-bloque 7.B.1 FASE 7).
 *
 * Espejo de backend/app/motors/m_meetings/schemas.py. Mantener
 * sincronizado manualmente al cambiar contratos backend.
 *
 * NOTA — H1 audit pre-frontend:
 *   sprint4-types.ts contiene tipos meeting legacy (`MeetingSession`,
 *   `MeetingNotes`, `MeetingLiveOutput`) NO eliminados (otros callers
 *   fuera scope FASE 7 los usan). Aquí definimos shapes nuevos
 *   coherentes con backend ExploratoryMeetingRow ampliado.
 */

// ────────────────────────────────────────────────────────────────────
// Type aliases (sincronizar CHECK constraints migration e8b3c5d70a91)
// ────────────────────────────────────────────────────────────────────

export const MEETING_PLATFORMS = [
  "google_meet",
  "zoom",
  "teams",
  "presencial",
  "jitsi",
  "other",
] as const;
export type MeetingPlatform = (typeof MEETING_PLATFORMS)[number];

export const MEETING_ETAPAS_K = [
  "K.1",
  "K.2",
  "K.3",
  "K.4",
  "K.5",
  "K.6",
  "other",
] as const;
export type MeetingEtapaK = (typeof MEETING_ETAPAS_K)[number];

export const MEETING_STATUSES = [
  "scheduled",
  "in_progress",
  "completed",
  "cancelled",
] as const;
export type MeetingStatus = (typeof MEETING_STATUSES)[number];

export const POST_ACTION_TYPES = [
  "propuesta",
  "create_project",
  "k6_signature",
  "email_summary",
] as const;
export type PostActionType = (typeof POST_ACTION_TYPES)[number];

export const PLATFORM_LABELS: Record<MeetingPlatform, string> = {
  google_meet: "Google Meet",
  zoom: "Zoom",
  teams: "MS Teams",
  presencial: "Presencial",
  jitsi: "Jitsi",
  other: "Otra",
};

export const ETAPA_K_LABELS: Record<MeetingEtapaK, string> = {
  "K.1": "K.1 Lead inicial",
  "K.2": "K.2 Cualificación",
  "K.3": "K.3 Pre-propuesta",
  "K.4": "K.4 Reunión exploratoria",
  "K.5": "K.5 Propuesta enviada",
  "K.6": "K.6 Firma contrato",
  other: "Otra",
};

export const STATUS_LABELS: Record<MeetingStatus, string> = {
  scheduled: "Programada",
  in_progress: "En curso",
  completed: "Completada",
  cancelled: "Cancelada",
};

// ────────────────────────────────────────────────────────────────────
// Inputs (espejo MeetingCreate / Update / Complete / Cancel / PostAction)
// ────────────────────────────────────────────────────────────────────

export interface MeetingCreate {
  client_id: string;
  project_id?: string | null;
  title: string;
  platform?: MeetingPlatform | null;
  meeting_url?: string | null;
  etapa_k?: MeetingEtapaK | null;
  interlocutor_contact_id?: string | null;
  scheduled_at?: string | null; // ISO datetime
  lead_source?: string | null;
}

export interface MeetingUpdate {
  title?: string;
  platform?: MeetingPlatform | null;
  meeting_url?: string | null;
  etapa_k?: MeetingEtapaK | null;
  interlocutor_contact_id?: string | null;
  scheduled_at?: string | null;
  project_id?: string | null;
  notes_markdown?: string | null;
}

export interface MeetingComplete {
  notes_markdown?: string | null;
  duration_minutes?: number | null;
  outputs_agente_18?: Record<string, unknown> | null;
}

export interface MeetingCancel {
  reason?: string | null;
}

export interface MeetingPostActionRequest {
  action_type: PostActionType;
  payload?: Record<string, unknown>;
}

export interface MeetingPostActionResponse {
  action_type: PostActionType;
  success: boolean;
  result?: Record<string, unknown>;
  error_message?: string | null;
}

// ────────────────────────────────────────────────────────────────────
// Outputs
// ────────────────────────────────────────────────────────────────────

export interface MeetingContactSummary {
  contact_id: string;
  full_name: string;
  role_title: string;
  role_category: string;
  email: string;
  notes_excerpt?: string | null;
}

export interface MeetingDetail {
  id: string;
  client_id: string;
  project_id?: string | null;
  title: string;
  platform?: MeetingPlatform | null;
  meeting_url?: string | null;
  etapa_k?: MeetingEtapaK | null;
  interlocutor_contact_id?: string | null;
  interlocutor?: MeetingContactSummary | null;
  meeting_date?: string | null;
  duration_minutes?: number | null;
  status: MeetingStatus;
  completed_at?: string | null;
  cancelled_at?: string | null;
  notes_markdown?: string | null;
  notes_html_sanitized?: string | null;
  sse_session_id?: string | null;
  outputs_agente_18?: Record<string, unknown> | null;
  lead_source?: string | null;
  conversion_status: string;
  proposal_generated_id?: string | null;
  created_at?: string | null;
}

export interface MeetingListItem {
  id: string;
  client_id: string;
  project_id?: string | null;
  title: string;
  platform?: MeetingPlatform | null;
  etapa_k?: MeetingEtapaK | null;
  interlocutor_contact_id?: string | null;
  interlocutor_name?: string | null;
  meeting_date?: string | null;
  status: MeetingStatus;
  duration_minutes?: number | null;
  has_notes: boolean;
}

export interface MeetingSearchResult {
  id: string;
  client_id: string;
  title: string;
  meeting_date?: string | null;
  status: MeetingStatus;
  snippet: string;
}

export interface SSEStartResponse {
  sse_session_id: string;
  stream_url: string;
}

// ────────────────────────────────────────────────────────────────────
// SSE event types — emitidos por POST /agents/18/meeting-update/stream
// ────────────────────────────────────────────────────────────────────

export type SSEProgressPhase = "thinking" | "validating_schema";

export interface SSEEventProgress {
  type: "progress";
  phase: SSEProgressPhase;
  ts?: number;
}

export interface SSEEventInsight {
  type: "insight";
  data: {
    categoria_ens?: string;
    confianza_categoria?: number;
    rationale_categoria?: string;
    madurez_actual?: string;
    horas_marcos_estimadas?: number;
    viabilidad_temporal?: string;
    riesgos_detectados?: Array<Record<string, unknown>>;
    quick_wins_sugeridas?: Array<Record<string, unknown>>;
    preguntas_pendientes?: Array<Record<string, unknown>>;
  };
}

export interface SSEEventDone {
  type: "done";
  latency_ms: number;
  tokens_input?: number | null;
  tokens_output?: number | null;
  schema_valid?: boolean;
  fallback_used?: boolean;
}

export interface SSEEventError {
  type: "error";
  error: string;
}

export type SSEEvent = SSEEventProgress | SSEEventInsight | SSEEventDone | SSEEventError;

// ────────────────────────────────────────────────────────────────────
// Filtros UI inbox
// ────────────────────────────────────────────────────────────────────

export interface MeetingsFilters {
  client_id?: string | null;
  project_id?: string | null;
  status?: MeetingStatus | null;
  limit?: number;
}
