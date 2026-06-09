/**
 * API client MB-18 auto-billing + retainer churn (ADR-040).
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

import type {
  ChurnRiskRow,
  ClientImplementationPayments,
  ClientInvoiceRow,
  FinanceKpis,
  ImplementationPaymentsView,
  MarkPaidRequest,
  MarkPaidResponse,
  PendingPaymentRow,
  RegenerateMilestonesResponse,
  RetainerRiskLevel,
  RetainerTransitionRequest,
  RetainerTransitionResponse,
  ScanChurnResponse,
} from "./schemas";

// ──────────── Admin · finance ────────────

export async function getFinanceKpisAdmin(): Promise<FinanceKpis> {
  return api<FinanceKpis>("/api/v1/admin/finance/kpis");
}

export async function listPendingPaymentsAdmin(): Promise<PendingPaymentRow[]> {
  return api<PendingPaymentRow[]>("/api/v1/admin/finance/pending-payments");
}

export async function markMilestonePaidAdmin(
  milestoneId: string,
  payload: MarkPaidRequest = {},
): Promise<MarkPaidResponse> {
  return api<MarkPaidResponse>(
    `/api/v1/admin/finance/milestones/${milestoneId}/mark-paid`,
    { method: "POST", json: payload },
  );
}

export async function regenerateContractMilestonesAdmin(
  contractId: string,
): Promise<RegenerateMilestonesResponse> {
  return api<RegenerateMilestonesResponse>(
    `/api/v1/admin/contracts/${contractId}/milestones/regenerate`,
    { method: "POST" },
  );
}

// ──────────── Admin · retainer ────────────

export async function listChurnRiskAdmin(
  riskLevel?: RetainerRiskLevel,
): Promise<ChurnRiskRow[]> {
  const path = riskLevel
    ? `/api/v1/admin/retainers/churn-risk?risk_level=${riskLevel}`
    : "/api/v1/admin/retainers/churn-risk";
  return api<ChurnRiskRow[]>(path);
}

export async function transitionRetainerAdmin(
  retainerId: string,
  payload: RetainerTransitionRequest,
): Promise<RetainerTransitionResponse> {
  return api<RetainerTransitionResponse>(
    `/api/v1/admin/retainers/${retainerId}/transition`,
    { method: "POST", json: payload },
  );
}

export async function triggerScanChurnAdmin(): Promise<ScanChurnResponse> {
  return api<ScanChurnResponse>(
    "/api/v1/admin/retainers/scan-churn",
    { method: "POST" },
  );
}

// ──────────── #45 · vista implementación × pagos ────────────

export async function getImplementationPaymentsAdmin(
  projectId: string,
): Promise<ImplementationPaymentsView> {
  return api<ImplementationPaymentsView>(
    `/api/v1/admin/finance/projects/${projectId}/implementation-payments`,
  );
}

export async function getMyImplementationPayments(): Promise<ClientImplementationPayments> {
  return clientApi<ClientImplementationPayments>(
    "/portal/billing/implementation-payments",
  );
}

// ──────────── Cliente · billing ────────────

export async function listMyInvoices(): Promise<ClientInvoiceRow[]> {
  return clientApi<ClientInvoiceRow[]>("/portal/billing/invoices");
}
