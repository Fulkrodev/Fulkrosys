"use client";

import { AlertTriangle, Loader2, Square } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useKillRun, useVerificationRuns } from "@/hooks/useVerification";

const CANCELLABLE = new Set([
  "pending",
  "authorized",
  "scheduled",
  "phase1_running",
  "phase2_running",
  "phase3_validating",
]);

export function KillSwitchButton({ projectId }: { projectId: string }) {
  const runs = useVerificationRuns(projectId);
  const kill = useKillRun(projectId);
  const [confirming, setConfirming] = React.useState(false);

  const cancellable = (runs.data?.runs ?? []).filter((r) =>
    CANCELLABLE.has(r.status),
  );

  if (cancellable.length === 0) {
    return (
      <Button variant="outline" disabled className="gap-2 text-fulkro-ink-500">
        <Square size={14} /> Apagado de emergencia
      </Button>
    );
  }

  async function handleKill() {
    try {
      for (const r of cancellable) {
        await kill.mutateAsync(r.id);
      }
      toast.success(
        `Apagado de emergencia solicitado: ${cancellable.length} run(s) marcadas para cancelación`,
      );
      setConfirming(false);
    } catch (err) {
      toast.error("No se pudo ejecutar el apagado de emergencia", {
        description: (err as Error).message,
      });
    }
  }

  if (confirming) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-fulkro-danger/40 bg-fulkro-danger/5 px-3 py-1.5">
        <AlertTriangle size={14} className="text-fulkro-danger" />
        <span className="text-xs text-fulkro-danger">
          Matar {cancellable.length} run(s)?
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setConfirming(false)}
          disabled={kill.isPending}
          className="h-7 text-xs"
        >
          No
        </Button>
        <Button
          size="sm"
          onClick={handleKill}
          disabled={kill.isPending}
          className="h-7 gap-1 bg-fulkro-danger text-white hover:bg-fulkro-danger/90"
        >
          {kill.isPending && <Loader2 size={10} className="animate-spin" />}
          Confirmar
        </Button>
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      onClick={() => setConfirming(true)}
      className="gap-2 border-fulkro-danger/40 text-fulkro-danger hover:bg-fulkro-danger/10"
    >
      <Square size={14} /> Apagado de emergencia ({cancellable.length})
    </Button>
  );
}
