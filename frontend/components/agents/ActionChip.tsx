"use client";

import {
  FileText,
  Link as LinkIcon,
  Loader2,
  Navigation,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { invokeAgent } from "@/lib/api/agents";
import type { SuggestedAction } from "@/lib/sprint4-types";

const ICONS: Record<SuggestedAction["kind"], LucideIcon> = {
  invoke_agent: Sparkles,
  open_magic_link: LinkIcon,
  generate_doc: FileText,
  navigate: Navigation,
};

function asString(v: unknown): string | undefined {
  return typeof v === "string" && v.length > 0 ? v : undefined;
}

/**
 * Chip de acción sugerida por el copiloto (Agente 14).
 *
 * S14 fix campaña auditoría: antes era un stub (toast "wiring con backend real
 * en siguiente sprint"). Ahora EJECUTA de verdad los 4 kinds leyendo `payload`:
 *  - navigate / generate_doc → router.push(payload.url) (sección project-scoped real)
 *  - open_magic_link        → window.open(payload.url) en pestaña nueva
 *  - invoke_agent           → POST /api/v1/agents/{id}/invoke (api/agents.ts)
 */
export function ActionChip({ action }: { action: SuggestedAction }) {
  const Icon = ICONS[action.kind];
  const router = useRouter();
  const [busy, setBusy] = React.useState(false);
  const payload = action.payload ?? {};

  async function run() {
    try {
      switch (action.kind) {
        case "navigate":
        case "generate_doc": {
          const url = asString(payload.url) ?? asString(payload.href);
          if (!url) {
            toast.error("Acción sin destino configurado");
            return;
          }
          router.push(url);
          return;
        }
        case "open_magic_link": {
          const url = asString(payload.url) ?? asString(payload.href);
          if (!url) {
            toast.error("Enlace no disponible");
            return;
          }
          window.open(url, "_blank", "noopener,noreferrer");
          return;
        }
        case "invoke_agent": {
          const agentId = Number(payload.agent_id ?? payload.agentId);
          const message = asString(payload.message) ?? action.label;
          if (!Number.isFinite(agentId) || agentId <= 0) {
            toast.error("Agente no especificado");
            return;
          }
          setBusy(true);
          await invokeAgent(agentId, {
            message,
            project_id: asString(payload.project_id),
          });
          toast.success(`${action.label} ejecutado`);
          return;
        }
        default:
          toast.error("Tipo de acción no soportado");
      }
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : `No se pudo ejecutar ${action.label}`,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={busy}
      onClick={() => void run()}
    >
      {busy ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
      {action.label}
    </Button>
  );
}
