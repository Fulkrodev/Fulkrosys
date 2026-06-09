"use client";

/**
 * Admin Onboarding API client (SAN-E v3.MB-4.3 PARTE A).
 *
 * Wraps Motor 16 admin endpoints (33 totales bajo /api/v1/onboarding).
 * Backend M16 catálogo de templates predefinidos · admin selecciona +
 * crea sessions · cliente recibe wizard correspondiente.
 *
 * NO existe edición CRUD del tree de preguntas · templates son JSON
 * cargados via catalog_loader. Admin panel = read-only viewer + sessions.
 */

import { api } from "@/lib/api";

// =====================================================================
// Enums backend (sync con backend/app/motors/m16_onboarding/enums.py)
// =====================================================================

export type Sector =
  | "servicios_profesionales"
  | "fintech"
  | "sanidad_privada"
  | "industria"
  | "saas_tech"
  | "retail_ecommerce"
  | "energia"
  | "logistica"
  | "educacion_privada"
  | "generico";

export type Role =
  | "sponsor"
  | "ti_cto"
  | "legal_dpo"
  | "rrhh"
  | "operaciones"
  | "compras"
  | "usuario_final";

export type SessionState =
  | "created"
  | "sent"
  | "in_progress"
  | "completed"
  | "expired"
  | "cancelled";

export type QuestionType =
  | "single_select"
  | "multi_select"
  | "text"
  | "long_text"
  | "number"
  | "date"
  | "boolean"
  | "email"
  | "url";

// =====================================================================
// Catalog · Templates · Questions
// =====================================================================

export interface QuestionOption {
  value: string;
  label: string;
}

export interface BranchingCondition {
  question_id: string;
  operator: "equals" | "not_equals" | "in" | "contains";
  value: unknown;
}

export interface QuestionValidation {
  required: boolean;
  min_length?: number | null;
  max_length?: number | null;
  min_value?: number | null;
  max_value?: number | null;
  regex?: string | null;
}

export interface OnboardingQuestion {
  id: string;
  type: QuestionType;
  section: string;
  label: string;
  tooltip?: string | null;
  example?: string | null;
  options?: QuestionOption[] | null;
  validation: QuestionValidation;
  placeholder?: string | null;
  skip_if?: BranchingCondition | null;
}

export interface TemplateSummary {
  id: string;
  version: string;
  sector: Sector;
  role: Role;
  nombre: string;
  descripcion: string;
  tiempo_estimado_minutos: number;
  language: string;
  total_questions: number;
}

export interface CatalogResponse {
  total: number;
  templates: TemplateSummary[];
  available_sectors: Sector[];
}

export interface OnboardingTemplateDetail extends TemplateSummary {
  questions: OnboardingQuestion[];
  sections: string[];
}

// =====================================================================
// Sessions
// =====================================================================

export interface SessionSummary {
  id: string;
  project_id: string;
  template_id: string | null;
  sector: string | null;
  role: string | null;
  interlocutor_email: string | null;
  interlocutor_name: string | null;
  state: SessionState | null;
  total_questions: number;
  answered_questions: number;
  progress_percentage: number;
  created_at: string;
  sent_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
}

export interface SessionDetail extends SessionSummary {
  magic_link_id: string | null;
  language: string | null;
  metadata_extra: Record<string, unknown> | null;
}

export interface CreateSessionBody {
  sector: Sector;
  role: Role;
  interlocutor_email: string;
  interlocutor_name?: string;
  ttl_hours?: number;
  language?: string;
  metadata_extra?: Record<string, unknown>;
}

export interface CreateSessionResponse {
  session_id: string;
  template_id: string;
  template_nombre: string;
  tiempo_estimado_minutos: number;
  total_questions: number;
  magic_link_id: string;
  magic_link_url: string;
  otp: string | null;
  expires_at: string;
  state: SessionState;
}

// =====================================================================
// Connectors admin (read-only · status global per project)
// =====================================================================

export interface ConnectorAdminStatus {
  provider: string;
  configured: boolean;
  status: string;
  last_discovery_at: string | null;
  scopes: string | null;
}

// =====================================================================
// LMS admin
// =====================================================================

export interface LMSCourse {
  codigo: string;
  titulo: string;
  duracion_minutos: number;
  framework?: string;
  sector?: string;
  descripcion?: string;
}

export interface LMSAssignmentAdmin {
  id: string;
  course_codigo: string;
  course_titulo: string;
  asistente_nombre: string;
  asistente_email: string;
  estado: "assigned" | "in_progress" | "completed" | "failed" | "expired";
  asignado_at: string | null;
  iniciado_at: string | null;
  completado_at: string | null;
  due_date: string | null;
  quiz_score: number | null;
  quiz_pass: boolean | null;
}

export interface AssignCourseBody {
  course_codigo: string;
  asistente_nombre: string;
  asistente_email: string;
  asistente_cargo?: string;
  asistente_organizacion?: string;
  due_date?: string;
}

export interface LMSProgressSummary {
  total_assignments: number;
  por_estado: Record<string, number>;
  proximos_due: number;
}

// =====================================================================
// API functions
// =====================================================================

const ADMIN_BASE = "/api/v1/onboarding";

// -------- Catalog --------

export async function getCatalog(): Promise<CatalogResponse> {
  return api<CatalogResponse>(`${ADMIN_BASE}/catalog`);
}

export async function getTemplateDetail(
  templateId: string,
): Promise<OnboardingTemplateDetail> {
  return api<OnboardingTemplateDetail>(
    `${ADMIN_BASE}/catalog/${encodeURIComponent(templateId)}`,
  );
}

// -------- Sessions --------

export async function listProjectSessions(
  projectId: string,
): Promise<SessionSummary[]> {
  return api<SessionSummary[]>(
    `${ADMIN_BASE}/projects/${projectId}/sessions`,
  );
}

export async function listExpiredSessions(
  projectId: string,
): Promise<SessionSummary[]> {
  return api<SessionSummary[]>(
    `${ADMIN_BASE}/projects/${projectId}/sessions/expired`,
  );
}

export async function getSessionDetail(
  sessionId: string,
): Promise<SessionDetail> {
  return api<SessionDetail>(`${ADMIN_BASE}/sessions/${sessionId}`);
}

export async function createSession(
  projectId: string,
  body: CreateSessionBody,
): Promise<CreateSessionResponse> {
  return api<CreateSessionResponse>(
    `${ADMIN_BASE}/projects/${projectId}/sessions`,
    { method: "POST", json: body },
  );
}

export async function cancelSession(
  sessionId: string,
  reason?: string,
): Promise<{ session_id: string; state: SessionState; magic_link_revoked: boolean }> {
  return api<{ session_id: string; state: SessionState; magic_link_revoked: boolean }>(
    `${ADMIN_BASE}/sessions/${sessionId}/cancel`,
    { method: "POST", json: { reason } },
  );
}

export async function markSessionSent(
  sessionId: string,
): Promise<{ session_id: string; state: SessionState; sent_at: string }> {
  return api<{ session_id: string; state: SessionState; sent_at: string }>(
    `${ADMIN_BASE}/sessions/${sessionId}/mark-sent`,
    { method: "POST" },
  );
}

// -------- Connectors admin --------

export async function listProjectConnectors(
  projectId: string,
): Promise<ConnectorAdminStatus[]> {
  const res = await api<{ connectors: ConnectorAdminStatus[] } | ConnectorAdminStatus[]>(
    `${ADMIN_BASE}/projects/${projectId}/connectors`,
  );
  if (Array.isArray(res)) return res;
  return res.connectors;
}

export async function validateConnector(
  projectId: string,
  provider: string,
): Promise<{ valid: boolean; error?: string }> {
  return api<{ valid: boolean; error?: string }>(
    `${ADMIN_BASE}/projects/${projectId}/connectors/${provider}/validate`,
    { method: "POST" },
  );
}

// -------- LMS --------

export async function listLMSCourses(): Promise<LMSCourse[]> {
  const res = await api<LMSCourse[] | { courses: LMSCourse[] }>(
    `${ADMIN_BASE}/lms/courses`,
  );
  return Array.isArray(res) ? res : res.courses;
}

export async function getLMSCourseDetail(codigo: string): Promise<LMSCourse> {
  return api<LMSCourse>(
    `${ADMIN_BASE}/lms/courses/${encodeURIComponent(codigo)}`,
  );
}

export async function listProjectLMSAssignments(
  projectId: string,
): Promise<LMSAssignmentAdmin[]> {
  const res = await api<
    LMSAssignmentAdmin[] | { assignments: LMSAssignmentAdmin[] }
  >(`${ADMIN_BASE}/projects/${projectId}/lms/assignments`);
  return Array.isArray(res) ? res : res.assignments;
}

export async function getProjectLMSProgress(
  projectId: string,
): Promise<LMSProgressSummary> {
  return api<LMSProgressSummary>(
    `${ADMIN_BASE}/projects/${projectId}/lms/progress`,
  );
}

export async function assignCourseToEmployee(
  projectId: string,
  body: AssignCourseBody,
): Promise<LMSAssignmentAdmin> {
  return api<LMSAssignmentAdmin>(
    `${ADMIN_BASE}/projects/${projectId}/lms/assign`,
    { method: "POST", json: body },
  );
}

// -------- Export --------

export async function exportCategorization(
  projectId: string,
): Promise<Record<string, unknown>> {
  return api<Record<string, unknown>>(
    `${ADMIN_BASE}/projects/${projectId}/onboarding/export-categorization`,
  );
}
