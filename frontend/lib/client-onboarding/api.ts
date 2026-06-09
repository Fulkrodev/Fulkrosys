"use client";

/**
 * Client Portal Onboarding API client (SAN-E v3.MB-4.3 PARTE B).
 *
 * Wraps Motor 16 portal endpoints (11 totales bajo
 * /api/v1/portal/onboarding/projects/{id}). Backend MB-4.2.bis 813c7a5.
 *
 * Auth: ClientUser session vía cookie + CSRF (clientApi helper existing
 * en frontend/lib/client-portal-api.ts).
 */

import { clientApi } from "@/lib/client-portal-api";

// =====================================================================
// Types (sync con backend portal_api.py)
// =====================================================================

export interface PortalStatus {
  session_id: string | null;
  estado: string | null;
  answered_questions: number;
  total_questions: number;
  progress_pct: number;
  template_id: string | null;
}

export interface PortalQuestion {
  id: string;
  type: string;
  section: string;
  label: string;
  tooltip?: string | null;
  example?: string | null;
  options?: { value: string; label: string }[] | null;
  validation: {
    required: boolean;
    min_length?: number | null;
    max_length?: number | null;
    min_value?: number | null;
    max_value?: number | null;
    regex?: string | null;
  };
  placeholder?: string | null;
}

export interface NextQuestionResponse {
  done: boolean;
  question: PortalQuestion | null;
  progress_percentage: number;
  current_section: string | null;
  remaining_required: number;
}

export interface PortalConnectorView {
  connector_type: string;
  available: boolean;
  connected: boolean;
  status: string;
  last_discovery_at: string | null;
  auth_method: "oauth" | "iam_access_key" | string;
}

export interface PortalLMSAssignment {
  id: string;
  course_codigo: string;
  course_titulo: string;
  asistente_nombre: string;
  asistente_email: string;
  estado: string;
  asignado_at: string | null;
  completado_at: string | null;
  quiz_score: number | null;
  quiz_pass: boolean | null;
}

export interface PortalLMSResponse {
  assignments: PortalLMSAssignment[];
  courses_available: Array<{
    codigo: string;
    titulo: string;
    duracion_minutos: number;
  }>;
}

export interface OAuthInitResponse {
  authorize_url: string;
  state: string;
}

export interface OAuthCallbackResponse {
  connected: boolean;
  connector_id: string;
  status: string;
}

export interface AWSCredentialsBody {
  access_key_id: string;
  secret_access_key: string;
  region: string;
}

export interface AWSCredentialsResponse {
  connected: boolean;
  connector_id: string;
  account_id: string | null;
  arn: string | null;
}

export interface FinishResponse {
  completed: boolean;
  completed_at: string | null;
  next_step_url: string | null;
}

// =====================================================================
// API functions
// =====================================================================

const PORTAL_BASE = "/portal/onboarding/projects";

// -------- Onboarding wizard --------

export async function getOnboardingStatus(projectId: string): Promise<PortalStatus> {
  return clientApi<PortalStatus>(`${PORTAL_BASE}/${projectId}/status`);
}

export async function getNextQuestion(projectId: string): Promise<NextQuestionResponse> {
  return clientApi<NextQuestionResponse>(
    `${PORTAL_BASE}/${projectId}/next-question`,
  );
}

export async function submitAnswer(
  projectId: string,
  payload: { question_id: string; answer: unknown },
): Promise<{
  question_id: string;
  saved: boolean;
  progress_percentage: number;
  state: string;
}> {
  return clientApi(`${PORTAL_BASE}/${projectId}/answer`, {
    method: "POST",
    json: payload,
  });
}

export async function finishOnboarding(projectId: string): Promise<FinishResponse> {
  return clientApi<FinishResponse>(`${PORTAL_BASE}/${projectId}/finish`, {
    method: "POST",
  });
}

// -------- Connectors --------

export async function listPortalConnectors(
  projectId: string,
): Promise<PortalConnectorView[]> {
  const res = await clientApi<{ connectors: PortalConnectorView[] }>(
    `${PORTAL_BASE}/${projectId}/connectors`,
  );
  return res.connectors;
}

export async function oauthInit(
  projectId: string,
  connectorType: string,
  payload: { redirect_uri: string },
): Promise<OAuthInitResponse> {
  return clientApi<OAuthInitResponse>(
    `${PORTAL_BASE}/${projectId}/connectors/${connectorType}/oauth-init`,
    { method: "POST", json: payload },
  );
}

export async function oauthCallback(
  projectId: string,
  connectorType: string,
  payload: { code: string; state: string },
): Promise<OAuthCallbackResponse> {
  return clientApi<OAuthCallbackResponse>(
    `${PORTAL_BASE}/${projectId}/connectors/${connectorType}/oauth-callback`,
    { method: "POST", json: payload },
  );
}

export async function awsCredentials(
  projectId: string,
  payload: AWSCredentialsBody,
): Promise<AWSCredentialsResponse> {
  return clientApi<AWSCredentialsResponse>(
    `${PORTAL_BASE}/${projectId}/connectors/aws/credentials`,
    { method: "POST", json: payload },
  );
}

export async function syncConnector(
  projectId: string,
  connectorType: string,
): Promise<{
  triggered: boolean;
  connector_type: string;
  status: string;
  note?: string;
}> {
  return clientApi(
    `${PORTAL_BASE}/${projectId}/connectors/${connectorType}/sync`,
    { method: "POST" },
  );
}

// -------- LMS --------

export async function listPortalLMS(projectId: string): Promise<PortalLMSResponse> {
  return clientApi<PortalLMSResponse>(`${PORTAL_BASE}/${projectId}/lms`);
}

export async function completeLMSAssignment(
  projectId: string,
  assignmentId: string,
): Promise<{ completed: boolean; assignment_id: string; completado_at: string }> {
  return clientApi(
    `${PORTAL_BASE}/${projectId}/lms/${assignmentId}/complete`,
    { method: "POST" },
  );
}
