/**
 * Admin AAPP billing API client (SAN-C MB-11.3).
 *
 * Endpoints backend (api/v1 m15_billing.invoices_aapp_api):
 *   POST /api/v1/projects/{id}/invoices/aapp · crea draft
 *   GET  /api/v1/projects/{id}/invoices/aapp · lista
 *   POST /api/v1/invoices/aapp/{id}/generate-facturae · XML 3.2.x
 *   POST /api/v1/invoices/aapp/{id}/submit-face · stub manual portal
 *   GET  /api/v1/invoices/aapp/{id}/late-interest · Ley 3/2004
 */
"use client";

import { api } from "@/lib/api";

export interface InvoiceAappCreate {
  invoice_number: string;
  amount_eur: string;
  dir3_oficina_contable: string;
  dir3_organo_gestor: string;
  dir3_unidad_tramitadora: string;
  payment_due_date?: string;
  issue_date?: string;
  description?: string;
}

export interface InvoiceAapp {
  id: string;
  project_id: string;
  invoice_number: string;
  amount_eur: string;
  dir3_oficina_contable: string;
  dir3_organo_gestor: string;
  dir3_unidad_tramitadora: string;
  status: string;
  payment_due_date: string | null;
  paid_at: string | null;
  interest_owed_eur: string | null;
  submitted_to_face_at: string | null;
  face_reference: string | null;
}

export interface FacturaeGenerationResponse {
  invoice_id: string;
  xml_size_bytes: number;
  xades_signed: boolean;
  xades_skip_reason: string | null;
}

export interface FaceSubmitResponse {
  submission_method: string;
  face_portal_url: string;
  xml_attached: boolean;
  xml_signed: boolean;
  manual_steps: string[];
  warning_no_signature: string | null;
}

export interface LateInterestResponse {
  invoice_id: string;
  amount_eur: string;
  interest_owed_eur: string;
  days_late: number;
  bce_rate_pct: string;
  total_rate_pct: string;
}

const PROJECTS = "/api/v1/projects";
const INVOICES = "/api/v1/invoices/aapp";

export async function createInvoiceAapp(
  projectId: string,
  body: InvoiceAappCreate,
): Promise<InvoiceAapp> {
  return api<InvoiceAapp>(`${PROJECTS}/${projectId}/invoices/aapp`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listInvoicesAapp(
  projectId: string,
): Promise<InvoiceAapp[]> {
  return api<InvoiceAapp[]>(`${PROJECTS}/${projectId}/invoices/aapp`);
}

export async function generateFacturae(
  invoiceId: string,
): Promise<FacturaeGenerationResponse> {
  return api<FacturaeGenerationResponse>(
    `${INVOICES}/${invoiceId}/generate-facturae`,
    { method: "POST" },
  );
}

export async function submitFace(
  invoiceId: string,
): Promise<FaceSubmitResponse> {
  return api<FaceSubmitResponse>(`${INVOICES}/${invoiceId}/submit-face`, {
    method: "POST",
  });
}

export async function getLateInterest(
  invoiceId: string,
  todayOverride?: string,
): Promise<LateInterestResponse> {
  const qs = todayOverride ? `?today_override=${todayOverride}` : "";
  return api<LateInterestResponse>(
    `${INVOICES}/${invoiceId}/late-interest${qs}`,
  );
}
