/**
 * Admin Financial API client (SAN-E v3.MB-3.2).
 *
 * Wired al backend M15 billing (commits MB-3.F + existing CRUD):
 *   GET    /api/v1/projects/{id}/financial-summary  (MB-3.F)
 *   GET    /api/v1/projects/{id}/aapp-billing/status (MB-3.F)
 *   POST   /api/v1/projects/{id}/invoices/{id}/send  (MB-3.F)
 *   GET    /api/v1/projects/{id}/invoices            (existing)
 *   GET    /api/v1/projects/{id}/invoices/{id}       (existing)
 *   GET    /api/v1/projects/{id}/invoices/{id}/pdf   (existing · stream)
 *   POST   /api/v1/projects/{id}/invoices/{id}/mark-paid (existing)
 *   POST   /api/v1/projects/{id}/invoices/{id}/cancel (existing)
 *   POST   /api/v1/projects/{id}/invoices/from-milestone (existing)
 */
import { api } from "@/lib/api";

export type EstadoPago =
  | "pendiente"
  | "vencida"
  | "pagada"
  | "anulada";

export type AAPPStage = "ok" | "pending" | "failed" | "n/a";

export interface FinancialTotals {
  invoiced: number;
  paid: number;
  outstanding: number;
}

export interface NextMilestone {
  amount_eur: number | null;
  label: string | null;
  milestone_index: number | null;
  billing_trigger: string | null;
}

export interface FinancialSummary {
  project_id: string;
  totals: FinancialTotals;
  next_milestone: NextMilestone | null;
  // #45 E0 · ordinal canónico (0-based) de projects.fase · base del timeline.
  current_phase_index: number | null;
  invoices_count: number;
  invoices_paid_count: number;
  invoices_pending_count: number;
  invoices_overdue_count: number;
}

export interface AAPPBillingStatus {
  project_id: string;
  has_active_aapp_invoice: boolean;
  invoice_id?: string;
  invoice_number?: string;
  total_amount?: number | null;
  stage_facturae_xades: AAPPStage;
  stage_face: AAPPStage;
  stage_verifactu: AAPPStage;
  current_status?: string;
  next_action?: string;
}

export interface Invoice {
  id: string;
  numero_correlativo: string | null;
  fecha_emision: string | null;
  fecha_vencimiento: string | null;
  total: number | null;
  base_imponible: number | null;
  iva_importe: number | null;
  estado_pago: EstadoPago | null;
  concepto: string | null;
  verifactu_hash: string | null;
  verifactu_enviado_at: string | null;
  pdf_path: string | null;
}

export interface InvoiceSendResponse {
  invoice_id: string;
  estado_pago: EstadoPago | null;
  sent_at: string;
  next_step: string;
}

const projectBase = (projectId: string) => `/api/v1/projects/${projectId}`;

export function getFinancialSummary(
  projectId: string,
): Promise<FinancialSummary> {
  return api<FinancialSummary>(`${projectBase(projectId)}/financial-summary`);
}

export function getAAPPBillingStatus(
  projectId: string,
): Promise<AAPPBillingStatus> {
  return api<AAPPBillingStatus>(`${projectBase(projectId)}/aapp-billing/status`);
}

export function listInvoices(projectId: string): Promise<Invoice[]> {
  return api<Invoice[]>(`${projectBase(projectId)}/invoices`);
}

export function getInvoicePdfUrl(projectId: string, invoiceId: string): string {
  return `${projectBase(projectId)}/invoices/${invoiceId}/pdf`;
}

export function sendInvoice(
  projectId: string,
  invoiceId: string,
): Promise<InvoiceSendResponse> {
  return api<InvoiceSendResponse>(
    `${projectBase(projectId)}/invoices/${invoiceId}/send`,
    { method: "POST", json: {} },
  );
}

export function markInvoicePaid(
  projectId: string,
  invoiceId: string,
): Promise<Invoice> {
  return api<Invoice>(
    `${projectBase(projectId)}/invoices/${invoiceId}/mark-paid`,
    { method: "POST", json: {} },
  );
}

export function cancelInvoice(
  projectId: string,
  invoiceId: string,
  reason?: string,
): Promise<Invoice> {
  return api<Invoice>(
    `${projectBase(projectId)}/invoices/${invoiceId}/cancel`,
    { method: "POST", json: { reason: reason ?? null } },
  );
}

export function generateInvoiceFromMilestone(
  projectId: string,
  milestoneIndex: number,
): Promise<Invoice> {
  return api<Invoice>(
    `${projectBase(projectId)}/invoices/from-milestone`,
    { method: "POST", json: { milestone_index: milestoneIndex } },
  );
}
