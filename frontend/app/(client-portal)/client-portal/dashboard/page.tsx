"use client";

/**
 * Client portal dashboard · MB-7 atom 7.1 plan v6.
 *
 * Adaptive dashboard rebuild (3 zones) replaces legacy SummaryCard layout.
 * Backend source: GET /api/v1/client-portal/dashboard/adaptive.
 */
import { ClientDashboardV3 } from "@/components/client-portal/dashboard/ClientDashboardV3";

export default function ClientDashboardPage() {
  return <ClientDashboardV3 />;
}
