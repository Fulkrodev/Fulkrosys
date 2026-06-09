/**
 * API client for public legal/trust endpoints (atom 9.bis.5).
 *
 * Mirrors `backend/app/motors/m_compliance_monitor/public_api.py`.
 * Endpoints are unauthenticated.
 */
import { api } from "@/lib/api";
import type {
  ComplianceStatusPublic,
  SubProcessorSubscribeResult,
} from "./schemas";

export async function getPublicComplianceStatus(): Promise<ComplianceStatusPublic> {
  return api<ComplianceStatusPublic>("/api/v1/legal/compliance/status");
}

export async function subscribeSubProcessorUpdates(
  email: string,
  consent: boolean,
): Promise<SubProcessorSubscribeResult> {
  return api<SubProcessorSubscribeResult>(
    "/api/v1/legal/sub-processor-notifications/subscribe",
    {
      method: "POST",
      json: { email, consent },
    },
  );
}
