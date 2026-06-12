"use client";

/**
 * Client portal dashboard · MB-7 atom 7.1 plan v6.
 *
 * Adaptive dashboard rebuild (3 zones) replaces legacy SummaryCard layout.
 * Backend source: GET /api/v1/client-portal/dashboard/adaptive.
 */
import { useEffect, useState } from "react";

import { ClientDashboardV3 } from "@/components/client-portal/dashboard/ClientDashboardV3";
import { CoachNextStepCard } from "@/components/client-portal/coach/CoachNextStepCard";
import { clientApi } from "@/lib/client-portal-api";

interface ClientMeResponse {
  project_id: string | null;
}

export default function ClientDashboardPage() {
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    void clientApi<ClientMeResponse>("/client-auth/me")
      .then((d) => setProjectId(d?.project_id ?? null))
      .catch(() => setProjectId(null));
  }, []);

  return (
    <div className="space-y-4">
      {/* Ola 2 · el copiloto guía al cliente con su siguiente paso (R29). */}
      <CoachNextStepCard projectId={projectId} />
      <ClientDashboardV3 />
    </div>
  );
}
