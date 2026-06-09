"use client";

/**
 * AdminAttestationGate · Gate 2 humano (doc §14 · solo categoría ALTA).
 *
 * Visible ÚNICAMENTE cuando autopilot_status === "paused_gate2". El pipeline
 * automatizado se detiene y espera la validación cualificada: es el pentester
 * acreditado (CPSTIC/OSCP) quien revisa los hallazgos, emite su opinión y
 * firma la atestación. Tras atestar, el run cierra (autopilot_status →
 * completed) y queda evidencia append-only de la firma humana.
 *
 * Esto NO es opcional para Alta: la norma exige personal cualificado (doc §14).
 */
import * as React from "react";
import { Loader2, ShieldCheck, UserCheck } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import type { AutopilotStatus } from "@/lib/api/autopilot";
import { useAttestRun } from "@/hooks/useAutopilot";

interface AdminAttestationGateProps {
  projectId: string;
  runId: string | null;
  autopilotStatus: AutopilotStatus | null;
}

export function AdminAttestationGate({
  projectId,
  runId,
  autopilotStatus,
}: AdminAttestationGateProps) {
  const attestMutation = useAttestRun(projectId);
  const [attestedBy, setAttestedBy] = React.useState("");
  const [cert, setCert] = React.useState("");
  const [opinion, setOpinion] = React.useState("");

  // Gate 2 SOLO aplica al run pausado a la espera de validación (categoría ALTA).
  if (autopilotStatus !== "paused_gate2" || !runId) return null;

  const canSubmit = attestedBy.trim().length > 0 && !attestMutation.isPending;

  async function handleAttest() {
    if (!runId) return;
    try {
      await attestMutation.mutateAsync({
        runId,
        body: {
          attested_by: attestedBy.trim(),
          cert: cert.trim() || undefined,
          opinion: opinion.trim() || undefined,
        },
      });
      toast.success("Atestación registrada", {
        description: `Run validado y cerrado por ${attestedBy.trim()}.`,
      });
    } catch (err) {
      toast.error("No se pudo registrar la atestación", {
        description: (err as Error).message,
      });
    }
  }

  return (
    <Card
      className="border-fulkro-warning/50"
      data-testid="admin-attestation-gate"
    >
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck size={20} className="text-fulkro-warning" />
          Gate 2 · Atestación del pentester acreditado
        </CardTitle>
        <CardDescription>
          El pipeline está pausado a la espera de validación humana cualificada.{" "}
          <TooltipENS
            text="Categoría ALTA exige que un pentester acreditado (CPSTIC / OSCP) revise los hallazgos, valide el alcance y firme la atestación. Es personal cualificado, requisito normativo (doc §14)."
            icon="info"
            iconSize={13}
          />
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Alert variant="warning">
          <UserCheck size={16} />
          <AlertTitle>Validación cualificada requerida</AlertTitle>
          <AlertDescription>
            El autopilot completó el pipeline automatizado y se detuvo en Gate 2.
            Es el <strong>pentester acreditado</strong> quien valida y firma:
            esta atestación deja evidencia append-only para la auditoría ENAC.
          </AlertDescription>
        </Alert>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
              Atestado por <span className="text-fulkro-danger">*</span>
            </span>
            <input
              type="text"
              value={attestedBy}
              onChange={(e) => setAttestedBy(e.target.value)}
              placeholder="Nombre del pentester acreditado"
              aria-label="Nombre del pentester acreditado"
              required
              className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-fulkro-primary-500/40"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
              Acreditación{" "}
              <TooltipENS
                text="Certificación profesional: CPSTIC (CCN), OSCP, OSCE, CRTO… que avala la competencia del firmante."
                icon="info"
                iconSize={12}
              />
            </span>
            <input
              type="text"
              value={cert}
              onChange={(e) => setCert(e.target.value)}
              placeholder="p. ej. OSCP · CPSTIC"
              aria-label="Acreditación del pentester"
              className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-fulkro-primary-500/40"
            />
          </label>
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
            Opinión / dictamen
          </span>
          <textarea
            value={opinion}
            onChange={(e) => setOpinion(e.target.value)}
            rows={4}
            placeholder="Valoración del pentester sobre el alcance probado, hallazgos verificados y conclusión de la verificación."
            aria-label="Opinión del pentester"
            className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-fulkro-primary-500/40"
          />
        </label>

        <div className="flex items-center justify-end gap-2">
          <Button
            onClick={handleAttest}
            disabled={!canSubmit}
            className="gap-2"
            data-testid="admin-attestation-submit"
            aria-label="Firmar atestación y cerrar el run"
          >
            {attestMutation.isPending && (
              <Loader2 size={16} className="animate-spin" />
            )}
            <ShieldCheck size={16} />
            Atestar y cerrar run
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
