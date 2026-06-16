/** Shared DTOs mirroring the FastAPI backend schemas + Sprint 2 UI contracts. */

export type RagStatus = "green" | "amber" | "red";

export interface MeResponse {
  id: string;
  email: string;
  display_name: string | null;
  must_change_password: boolean;
  webauthn_credentials: number;
  totp_enabled: boolean;
  // Role-aware claims (ADR-013 + ADR-015): role identidad de BD,
  // is_owner derivado. Backend los devuelve desde commit fbcfdf4.
  // Frontend los consume en AuthGuard (3.D) + login redirect.
  role: string;
  is_owner: boolean;
}

export interface LoginResponse {
  mfa_ticket: string;
  webauthn: PublicKeyCredentialRequestOptionsJSON | null;
  totp_available: boolean;
  webauthn_available: boolean;
}

export interface MfaVerifyResponse {
  csrf_token: string;
  expires_at: string;
}

export interface PublicKeyCredentialRequestOptionsJSON {
  publicKey?: {
    challenge: string;
    rpId?: string;
    timeout?: number;
    userVerification?: "required" | "preferred" | "discouraged";
    allowCredentials?: Array<{
      id: string;
      type: "public-key";
      transports?: string[];
    }>;
  };
}

/** ──────────── Core entities (real backend: /api/v1/clients, /projects) ──────────── */

export interface Client {
  id: string;
  nombre: string;
  cif: string;
  sector?: string | null;
  contacto_email?: string | null;
  contacto_telefono?: string | null;
  lead_source?: string | null;
  /** CRITICAL #1 · project_id resuelto (1 proyecto = 1 cliente). El selector
   * navega con ESTE id (client.id da 404 en /projects/{id}/header). */
  project_id?: string | null;
  /** Derived on the frontend until the backend exposes health/RAG for clients. */
  rag?: RagStatus;
}

export interface Project {
  id: string;
  client_id: string;
  nombre: string;
  fase?: string | null;
  lifecycle_state?: string | null;
  categoria_objetivo?: string | null;
  estado?: string | null;
}

/** ──────────── Dashboard (K.1) — backed by GET /api/v1/dashboard/* ──────────── */

export interface DashboardKpis {
  active_projects: number;
  leads_count: number;
  leads_value_eur: number;
  retainers_active: number;
  mrr_eur: number;
  treasury_30d_eur: number;
  treasury_trend_pct: number;
  projects_rag: RagStatus;
}

export interface MyDayItem {
  id: string;
  type: "review_docs" | "signature" | "meeting" | "other";
  title: string;
  /** Deep-link target within the app. */
  href?: string;
  count?: number;
  scheduledAt?: string;
}

export interface DashboardAlert {
  id: string;
  severity: RagStatus;
  project?: string;
  message: string;
  createdAt: string;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type:
    | "evidence_generated"
    | "scan_completed"
    | "proposal_sent"
    | "document_signed"
    | "agent_run"
    | "other";
  description: string;
  project_slug?: string;
  agent_id?: number;
}

/** ──────────── Pipeline (K.2) — backed by GET/PATCH /api/v1/commercial/leads ──────────── */

export type LeadStage =
  | "new"
  | "qualifying"
  | "meeting_exploratory"
  | "proposal_sent"
  | "negotiation"
  | "won"
  | "lost"
  | "paused";

export const LEAD_STAGES: Array<{ id: LeadStage; label: string }> = [
  { id: "new", label: "Nuevo" },
  { id: "qualifying", label: "Cualificando" },
  { id: "meeting_exploratory", label: "Reunión explor." },
  { id: "proposal_sent", label: "Propuesta enviada" },
  { id: "negotiation", label: "Negociación" },
  { id: "won", label: "Cerrado ganado" },
  { id: "lost", label: "Cerrado perdido" },
  { id: "paused", label: "En pausa" },
];

export interface Lead {
  id: string;
  empresa: string;
  cif?: string;
  sector?: string;
  score: number; // 0–100 qualifying score
  rag: RagStatus;
  value_eur: number;
  stage: LeadStage;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  source?: string;
  pliego_attached?: boolean;
  last_touched_at: string;
  lost_reason?: string;
  notes?: string;
}
