/** Sprint 4 DTOs — meeting, audit mode, pentest console, magic links, copilot. */
import type { RagStatus } from "./types";

/** ──────────── Copilot (Agent 14) ──────────── */

export interface Citation {
  id: string;
  framework: string; // "RD 311/2022"
  article: string; // "Art. 12"
  excerpt: string;
  chunk_id?: string;
  measure?: string;
  preview?: string;
}

export interface CopilotMessageMetadata {
  confidence?: number;
  corpus_gap?: boolean;
  chunks_used?: Array<{
    chunk_id: string;
    source: string;
    preview: string;
    score: number;
  }>;
  model_used?: string;
}

export interface SuggestedAction {
  id: string;
  label: string;
  kind: "invoke_agent" | "open_magic_link" | "generate_doc" | "navigate";
  payload?: Record<string, unknown>;
}

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  actions?: SuggestedAction[];
  createdAt: string;
  streaming?: boolean;
  metadata?: CopilotMessageMetadata;
}

/** ──────────── Meeting (K.4, Agent 18) ──────────── */

export interface MeetingNotes {
  contexto: string;
  informacion: string;
  madurez: string;
  plazos: string;
  presupuesto: string;
  equipo: string;
}

export interface MeetingLiveOutput {
  category: { value: "BASICA" | "MEDIA" | "ALTA"; confidence_pct: number };
  maturity: { level: "L1" | "L2" | "L3" | "L4" | "L5"; hours_estimate: number };
  feasibility: { months: number; note: string };
  risks: Array<{ id: string; severity: RagStatus; title: string }>;
  quick_wins: Array<{ id: string; title: string; impact: RagStatus }>;
}

export interface MeetingSession {
  id: string;
  lead_id: string | null;
  lead_name: string;
  started_at: string;
  duration_minutes: number;
  notes: MeetingNotes;
  live_output: MeetingLiveOutput | null;
  status: "active" | "closed";
}

/** ──────────── Audit mode (K.5) ──────────── */

export interface AuditSearchHit {
  id: string;
  evidence_code: string;
  title: string;
  relevance: number;
  signed: boolean;
  uploaded_at: string;
  preview: string;
}

export interface AuditQuery {
  id: string;
  query: string;
  results: number;
  status: "matched" | "no_evidence" | "partial";
  asked_at: string;
}

/** ──────────── Pentest console (M8 + 14 MCPs) ──────────── */

export type McpStatus = "idle" | "running" | "completed" | "error" | "disabled";

export interface McpServerState {
  id: string;
  name: string;
  description: string;
  tools: number;
  status: McpStatus;
  findings_count: number;
}

export interface PentestScope {
  targets: string[];
  exclusions: string[];
  signed_by: string[];
  signed_at: string;
}

export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface PentestFinding {
  id: string;
  title: string;
  severity: FindingSeverity;
  cvss: number;
  mapped_measure: string;
  asset: string;
  tool: string;
  detected_at: string;
  status: "new" | "triaged" | "reported";
}

export interface PendingAction {
  id: string;
  tool: string;
  description: string;
  risk: RagStatus;
  proposed_at: string;
}

export interface PentestEngagement {
  run_id: string;
  status: "idle" | "running" | "paused" | "stopped" | "completed";
  current_phase: number;
  total_phases: number;
  current_phase_name: string;
  progress_pct: number;
  scope: PentestScope;
  mcp_servers: McpServerState[];
  findings: PentestFinding[];
  pending_actions: PendingAction[];
  started_at: string;
}

/** ──────────── Magic link public pages (M12) ──────────── */

export type MagicLinkPurpose =
  | "sign"
  | "upload_evidence"
  | "onboarding_survey"
  | "view";

export interface MagicLinkContext {
  token: string;
  purpose: MagicLinkPurpose;
  client_name: string;
  project_name: string;
  expires_at: string;
  requires_otp: boolean;
}

export interface SignDocumentPayload extends MagicLinkContext {
  document_code: string;
  document_title: string;
  preview_snippet: string;
  signatory_role: string;
}

export interface SurveyQuestion {
  id: string;
  text: string;
  type: "short" | "long" | "choice" | "scale";
  options?: string[];
  required?: boolean;
}

export interface SurveyPayload extends MagicLinkContext {
  sector: string;
  role: string;
  questions: SurveyQuestion[];
}

export interface UploadPayload extends MagicLinkContext {
  expected_measure: string;
  expected_count: number;
  instructions: string;
}
