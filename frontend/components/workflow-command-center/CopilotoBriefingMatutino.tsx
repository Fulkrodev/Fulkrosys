/**
 * CopilotoBriefingMatutino · summary briefing stub · sub-atom 1.C.D.B.3 v3.8.
 *
 * Summary multi-cliente status del día · derivado de useCommandCenterMultiClient.
 * Stub LLM real defer 1.D.B.2 · UI ready zero refactor swap-in.
 */
"use client";

import { BellRing, Sparkles } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/skeleton";

import { fetchAdminNudges } from "@/lib/api/copiloto";
import { useCommandCenterMultiClient } from "@/hooks/useWorkflowCommandCenter";

/**
 * #22 Ola 5 · push proactivo admin: avisos de proyectos urgent que Marcos lleva
 * >72h sin abrir. Aparece en el sidebar (glanceable) en cualquier página admin ·
 * NO email · cooldown 7d server-side. Se nutre de /copilot/admin-nudges.
 */
function AdminNudgesSection() {
  const { data: nudges } = useQuery({
    queryKey: ["copilot-admin-nudges"],
    queryFn: () => fetchAdminNudges(5),
    staleTime: 60_000,
  });

  if (!nudges || nudges.length === 0) return null;

  return (
    <div
      className="rounded-md border border-violet-200 bg-violet-50 p-3 text-xs space-y-1.5"
      data-testid="copiloto-admin-nudges"
    >
      <div className="flex items-center gap-1.5 font-medium text-violet-900">
        <BellRing className="size-3" />
        Pendiente en otros proyectos ({nudges.length})
      </div>
      <ul className="space-y-1">
        {nudges.map((n) => (
          <li key={n.id}>
            {n.project_id ? (
              <Link
                href={`/admin/projects/${n.project_id}/workflow`}
                className="text-violet-900/85 hover:underline"
              >
                <span className="font-medium">
                  {n.project_nombre ?? "Proyecto"}
                </span>
                {n.message ? ` · ${n.message}` : ""}
              </Link>
            ) : (
              <span className="text-violet-900/85">{n.message}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function BriefingBody() {
  const { data, isLoading } = useCommandCenterMultiClient();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (!data) return null;

  const total =
    data.urgentes_hoy.length +
    data.esta_semana.length +
    data.en_marcha.length +
    data.proximos_30d.length;

  if (total === 0) {
    return (
      <div className="rounded-md bg-muted/40 p-3 text-xs">
        <div className="flex items-center gap-1.5 font-medium mb-1">
          <Sparkles className="size-3" />
          Sin clientes activos
        </div>
        <p className="text-foreground/70">
          Aprovecha para preparar pipeline · capturar leads o trabajo profundo.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5 text-xs">
      <p className="font-medium">Briefing matutino</p>
      <p className="text-foreground/80">
        Buenos días Marcos. <strong>{total}</strong>{" "}
        {total === 1 ? "cliente activo" : "clientes activos"} en portfolio:
      </p>
      <ul className="space-y-0.5 text-foreground/75">
        {data.urgentes_hoy.length > 0 && (
          <li>
            🔴 {data.urgentes_hoy.length} urgente
            {data.urgentes_hoy.length === 1 ? "" : "s"} hoy
          </li>
        )}
        {data.esta_semana.length > 0 && (
          <li>
            🟡 {data.esta_semana.length} esta semana
          </li>
        )}
        {data.en_marcha.length > 0 && (
          <li>
            🟢 {data.en_marcha.length} en marcha
          </li>
        )}
        {data.proximos_30d.length > 0 && (
          <li>
            📅 {data.proximos_30d.length} hito{data.proximos_30d.length === 1 ? "" : "s"} forecast 30d
          </li>
        )}
      </ul>
    </div>
  );
}

export function CopilotoBriefingMatutino() {
  // El push proactivo (#22) se muestra SIEMPRE arriba (independiente del
  // resumen multi-cliente) · es el aviso de proyectos que Marcos no toca.
  return (
    <div className="space-y-2">
      <AdminNudgesSection />
      <BriefingBody />
    </div>
  );
}
