"use client";

/**
 * /client-portal/continuidad · cuestionario de continuidad (BIA/DRP) + aprobación.
 * feat/fulkro-100 (2026-06-12).
 *
 * R29 cliente friendly · cliente-mínimo: el cliente APORTA su tolerancia y
 * APRUEBA el Plan de Continuidad que prepara su consultor. Sync admin↔cliente
 * realtime via SSE (continuidad.*).
 */
import { useEffect, useState } from "react";

import { ContinuidadClienteView } from "@/components/client-portal/ContinuidadClienteView";
import { clientApi } from "@/lib/client-portal-api";

interface ClientMeResponse {
  project_id: string | null;
}

export default function ClienteContinuidadPage() {
  const [projectId, setProjectId] = useState<string | null>(null);

  useEffect(() => {
    void clientApi<ClientMeResponse>("/client-auth/me")
      .then((data) => setProjectId(data?.project_id ?? null))
      .catch(() => setProjectId(null));
  }, []);

  return (
    <div className="space-y-4 p-4 md:p-6">
      <h1 className="text-2xl font-bold">Continuidad de tu negocio</h1>
      <p className="text-sm text-muted-foreground">
        Nos ayudas a entender qué es lo más importante de tu actividad para
        protegerla. Con eso, tu consultor prepara tu Plan de Continuidad y tú solo
        tienes que revisarlo y aprobarlo.
      </p>
      <ContinuidadClienteView projectId={projectId} />
    </div>
  );
}
