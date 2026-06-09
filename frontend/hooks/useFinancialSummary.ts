"use client";

/**
 * useFinancialSummary · TanStack Query hook (SAN-E v3.MB-3.2).
 *
 * Wraps lib/admin-financial/api · 3 queries + 4 mutations.
 * Auto-invalidate queryKeys tras mutation success.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type FinancialSummary,
  type AAPPBillingStatus,
  type Invoice,
  cancelInvoice,
  generateInvoiceFromMilestone,
  getAAPPBillingStatus,
  getFinancialSummary,
  listInvoices,
  markInvoicePaid,
  sendInvoice,
} from "@/lib/admin-financial/api";

export const summaryKey = (projectId: string) =>
  ["financial-summary", projectId] as const;
export const aappKey = (projectId: string) =>
  ["aapp-billing-status", projectId] as const;
export const invoicesKey = (projectId: string) =>
  ["invoices", projectId] as const;

export function useFinancialSummary(projectId: string) {
  const qc = useQueryClient();

  const summary = useQuery<FinancialSummary>({
    queryKey: summaryKey(projectId),
    queryFn: () => getFinancialSummary(projectId),
    enabled: Boolean(projectId),
  });

  const aapp = useQuery<AAPPBillingStatus>({
    queryKey: aappKey(projectId),
    queryFn: () => getAAPPBillingStatus(projectId),
    enabled: Boolean(projectId),
  });

  const invoices = useQuery<Invoice[]>({
    queryKey: invoicesKey(projectId),
    queryFn: () => listInvoices(projectId),
    enabled: Boolean(projectId),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: summaryKey(projectId) });
    qc.invalidateQueries({ queryKey: aappKey(projectId) });
    qc.invalidateQueries({ queryKey: invoicesKey(projectId) });
  };

  const generateMutation = useMutation({
    mutationFn: (milestoneIndex: number) =>
      generateInvoiceFromMilestone(projectId, milestoneIndex),
    onSuccess: invalidateAll,
  });

  const sendMutation = useMutation({
    mutationFn: (invoiceId: string) => sendInvoice(projectId, invoiceId),
    onSuccess: invalidateAll,
  });

  const markPaidMutation = useMutation({
    mutationFn: (invoiceId: string) => markInvoicePaid(projectId, invoiceId),
    onSuccess: invalidateAll,
  });

  const cancelMutation = useMutation({
    mutationFn: (vars: { invoiceId: string; reason?: string }) =>
      cancelInvoice(projectId, vars.invoiceId, vars.reason),
    onSuccess: invalidateAll,
  });

  return {
    summary,
    aapp,
    invoices,
    generate: generateMutation,
    send: sendMutation,
    markPaid: markPaidMutation,
    cancel: cancelMutation,
  };
}
