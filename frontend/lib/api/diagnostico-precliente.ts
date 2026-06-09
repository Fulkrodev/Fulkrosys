/**
 * Diagnóstico previo (lead account-less) · cliente API dedicado · Batch B.
 *
 * El lead entra por magic-link SIN cuenta. NO usa clientApi/api (esos llevan
 * cookie + CSRF de sesión). Autentica con headers X-Onboarding-Session-Id +
 * X-Onboarding-Session-Secret · el secret vive en el estado del componente
 * (devuelto por /consume), nunca en cookie.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";
const ROOT = `${API_BASE}/api/v1/onboarding`;

export interface DiagnosticoAuth {
  sessionId: string;
  sessionSecret: string;
}

export interface ConsumeResult {
  session_id: string;
  session_secret: string;
  template_nombre: string;
  tiempo_estimado_minutos: number;
  total_questions: number;
  answered_questions: number;
  progress_percentage: number;
  sections: string[];
}

export interface QuestionOption {
  value: string;
  label: string;
}

export interface QuestionValidation {
  required?: boolean;
  min_length?: number | null;
  max_length?: number | null;
}

export type QuestionKind =
  | "single_select"
  | "multi_select"
  | "text"
  | "long_text"
  | "number"
  | "boolean"
  | "email"
  | "url"
  | "date";

export interface DiagnosticoQuestion {
  id: string;
  type: QuestionKind;
  section: string;
  label: string;
  tooltip?: string | null;
  example?: string | null;
  placeholder?: string | null;
  options?: QuestionOption[] | null;
  validation: QuestionValidation;
}

export interface NextQuestionResult {
  done: boolean;
  question: DiagnosticoQuestion | null;
  progress_percentage: number;
  current_section: string | null;
  remaining_required: number;
}

export type AnswerValue = string | string[] | number | boolean;

/** Error con el status HTTP para distinguir 410 (caducado) / 401 / 403. */
export class DiagnosticoError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(auth: DiagnosticoAuth): HeadersInit {
  return {
    "X-Onboarding-Session-Id": auth.sessionId,
    "X-Onboarding-Session-Secret": auth.sessionSecret,
  };
}

async function parse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* sin cuerpo JSON */
    }
    throw new DiagnosticoError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export async function consumeDiagnosticoToken(
  token: string,
): Promise<ConsumeResult> {
  const resp = await fetch(`${ROOT}/consume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  return parse<ConsumeResult>(resp);
}

export interface ConsentText {
  version: string;
  text: string;
}

export async function getConsentText(
  auth: DiagnosticoAuth,
): Promise<ConsentText> {
  const resp = await fetch(`${ROOT}/me/consent-text`, {
    headers: authHeaders(auth),
  });
  return parse<ConsentText>(resp);
}

export async function recordConsent(auth: DiagnosticoAuth): Promise<void> {
  const resp = await fetch(`${ROOT}/me/consent`, {
    method: "POST",
    headers: { ...authHeaders(auth), "Content-Type": "application/json" },
    body: JSON.stringify({ consented: true }),
  });
  await parse<unknown>(resp);
}

export async function getNextQuestion(
  auth: DiagnosticoAuth,
): Promise<NextQuestionResult> {
  const resp = await fetch(`${ROOT}/me/next-question`, {
    headers: authHeaders(auth),
  });
  return parse<NextQuestionResult>(resp);
}

export async function saveAnswer(
  auth: DiagnosticoAuth,
  questionId: string,
  answerValue: AnswerValue,
): Promise<void> {
  const resp = await fetch(`${ROOT}/me/responses`, {
    method: "POST",
    headers: { ...authHeaders(auth), "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer_value: answerValue }),
  });
  await parse<unknown>(resp);
}

export async function submitDiagnostico(auth: DiagnosticoAuth): Promise<void> {
  const resp = await fetch(`${ROOT}/me/submit`, {
    method: "POST",
    headers: { ...authHeaders(auth), "Content-Type": "application/json" },
    body: JSON.stringify({ allow_partial: false }),
  });
  await parse<unknown>(resp);
}
