"use client";

/**
 * AutopilotSection · compositor cliente que une AutopilotPanel +
 * AdminAttestationGate + EvidencePackView compartiendo el run activo.
 *
 * Mantiene el estado mínimo (run_id + autopilot_status) que el panel descubre
 * (vía SSE/polling) y lo propaga al Gate 2 y al pack de evidencia. Se embebe en
 * la página de verificación sin tocar el contenido server-rendered existente.
 */
import * as React from "react";

import type { AutopilotStatus } from "@/lib/api/autopilot";
import { AdminAttestationGate } from "@/components/verification/AdminAttestationGate";
import { AutopilotPanel } from "@/components/verification/AutopilotPanel";
import { EvidencePackView } from "@/components/verification/EvidencePackView";

export function AutopilotSection({ projectId }: { projectId: string }) {
  const [runId, setRunId] = React.useState<string | null>(null);
  const [status, setStatus] = React.useState<AutopilotStatus | null>(null);

  const handleRunChange = React.useCallback(
    (nextRunId: string | null, nextStatus: AutopilotStatus | null) => {
      setRunId(nextRunId);
      setStatus(nextStatus);
    },
    [],
  );

  // El pack de evidencia solo es significativo en estados con resultado.
  const evidenceRunId =
    status === "completed" ||
    status === "partial" ||
    status === "paused_gate2"
      ? runId
      : null;

  return (
    <section
      className="flex flex-col gap-5"
      aria-label="Autopilot de verificación M8"
      data-testid="autopilot-section"
    >
      <AutopilotPanel projectId={projectId} onRunChange={handleRunChange} />
      <AdminAttestationGate
        projectId={projectId}
        runId={runId}
        autopilotStatus={status}
      />
      <EvidencePackView projectId={projectId} runId={evidenceRunId} />
    </section>
  );
}
