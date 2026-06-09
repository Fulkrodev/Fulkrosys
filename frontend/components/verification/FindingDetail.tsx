"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCcw,
  ShieldQuestion,
  X,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  usePatchFinding,
  useRetestFinding,
} from "@/hooks/useVerification";
import type {
  FindingStatus,
  FindingSummary,
  Severity,
} from "@/lib/verification-types";
import { cn } from "@/lib/utils";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-fulkro-danger text-white",
  high: "bg-fulkro-danger-500 text-white",
  medium: "bg-fulkro-warning text-white",
  low: "bg-fulkro-info text-white",
  info: "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-muted)]",
};

const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "abierto",
  needs_review: "revisar",
  remediated: "remediado",
  accepted_risk: "riesgo aceptado",
  false_positive: "falso positivo",
};

interface Props {
  projectId: string;
  finding: FindingSummary;
  onClose: () => void;
}

export function FindingDetail({ projectId, finding, onClose }: Props) {
  const patch = usePatchFinding(projectId);
  const retest = useRetestFinding(projectId);

  const [showFP, setShowFP] = React.useState(false);
  const [fpReason, setFpReason] = React.useState("");
  const [showAccept, setShowAccept] = React.useState(false);
  const [acceptJust, setAcceptJust] = React.useState("");
  const [acceptApproved, setAcceptApproved] = React.useState("");

  async function markFP() {
    if (!fpReason.trim()) {
      toast.error("Indica un motivo de falso positivo");
      return;
    }
    await patch.mutateAsync({
      findingId: finding.id,
      body: { status: "false_positive", false_positive_reason: fpReason },
    });
    toast.success("Marcado como falso positivo");
    setShowFP(false);
    onClose();
  }

  async function markAccepted() {
    if (!acceptJust.trim() || !acceptApproved.trim()) {
      toast.error("Justificación y aprobador son obligatorios");
      return;
    }
    await patch.mutateAsync({
      findingId: finding.id,
      body: {
        status: "accepted_risk",
        accepted_risk_justification: acceptJust,
        accepted_risk_approved_by: acceptApproved,
      },
    });
    toast.success("Riesgo aceptado registrado");
    setShowAccept(false);
    onClose();
  }

  async function fireRetest() {
    try {
      const result = await retest.mutateAsync({
        findingId: finding.id,
        body: { triggered_by: "marcos" },
      });
      toast.success(`Re-test: ${result.result ?? "sin resultado"}`, {
        description: result.result_detail ?? "",
      });
    } catch (err) {
      toast.error("Re-test falló", {
        description: (err as Error).message,
      });
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-fulkro-primary-700/30 p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="finding-detail-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-hidden rounded-lg border border-[color:var(--fulkro-surface-glass-border)] bg-white shadow-ink"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-fulkro-ink-300/40 p-4">
          <div className="flex items-start gap-2">
            <span
              className={cn(
                "mt-0.5 rounded px-2 py-0.5 text-[11px] font-semibold uppercase",
                SEVERITY_STYLES[finding.severity],
              )}
            >
              {finding.severity}
            </span>
            <div>
              <h2
                id="finding-detail-title"
                className="text-xl font-bold text-[color:var(--fulkro-title)]"
              >
                {finding.title}
              </h2>
              <p className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                {finding.id.slice(0, 8)}… · {finding.affected_host}
                {finding.affected_port ? `:${finding.affected_port}` : ""}
              </p>
            </div>
          </div>
          <button
            type="button"
            aria-label="Cerrar"
            onClick={onClose}
            className="rounded p-1 text-fulkro-ink-500 hover:bg-fulkro-ink-100"
          >
            <X size={16} />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-4">
          <dl className="grid gap-3 md:grid-cols-2">
            <Field label="CVE" value={finding.cve_id ?? "—"} mono />
            <Field
              label="CVSS v3.1"
              value={finding.cvss_score?.toFixed(1) ?? "—"}
            />
            <Field
              label="Medida ENS primaria"
              value={finding.ens_primary_measure ?? "—"}
              mono
            />
            <Field
              label="Clasificación ZFP"
              value={`${finding.zfp_gate5_classification} · confianza ${finding.confidence_score.toFixed(2)}`}
            />
            <Field label="Estado" value={STATUS_LABEL[finding.status]} />
            <Field
              label="Prioridad remediación"
              value={finding.remediation_priority?.toString() ?? "—"}
            />
          </dl>

          <div className="mt-4 rounded border border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] p-3 text-base font-medium text-[color:var(--fulkro-body)]">
            <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Cadena de evidencia
            </p>
            <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
              El backend preserva raw_outputs y hashes SHA-256 por herramienta.
              Accede al detalle de custodia y mapeo MITRE desde el informe E-702
              generado para el run actual.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-fulkro-ink-300/40 bg-fulkro-ink-100/50 p-3">
          <Button
            onClick={fireRetest}
            disabled={retest.isPending}
            className="gap-2"
          >
            {retest.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <RefreshCcw size={14} />
            )}
            Re-test dirigido
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowFP((v) => !v)}
            disabled={patch.isPending}
            className="gap-2 border-[color:var(--fulkro-surface-glass-border)]"
          >
            <ShieldQuestion size={14} /> Marcar FP
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowAccept((v) => !v)}
            disabled={patch.isPending}
            className="gap-2 border-fulkro-warning/40 text-fulkro-warning"
          >
            <AlertTriangle size={14} /> Aceptar riesgo
          </Button>
          {finding.status !== "remediated" && (
            <Button
              variant="outline"
              onClick={async () => {
                await patch.mutateAsync({
                  findingId: finding.id,
                  body: { status: "remediated" },
                });
                toast.success("Marcado como remediado");
                onClose();
              }}
              disabled={patch.isPending}
              className="gap-2 border-fulkro-success/40 text-fulkro-success"
            >
              <CheckCircle2 size={14} /> Marcar remediado
            </Button>
          )}
        </div>

        {showFP && (
          <div className="border-t border-fulkro-ink-300/40 bg-fulkro-ink-100/30 p-4">
            <Label htmlFor="fp-reason" className="text-xs">
              Motivo del falso positivo
            </Label>
            <Input
              id="fp-reason"
              value={fpReason}
              onChange={(e) => setFpReason(e.target.value)}
              placeholder="Ej. banner engañoso, herramienta detecta versión incorrecta…"
              className="mt-1"
            />
            <div className="mt-2 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFP(false)}
              >
                Cancelar
              </Button>
              <Button size="sm" onClick={markFP} disabled={patch.isPending}>
                Confirmar
              </Button>
            </div>
          </div>
        )}

        {showAccept && (
          <div className="border-t border-fulkro-ink-300/40 bg-fulkro-ink-100/30 p-4">
            <div className="flex flex-col gap-2">
              <div>
                <Label htmlFor="acc-just" className="text-xs">
                  Justificación
                </Label>
                <Input
                  id="acc-just"
                  value={acceptJust}
                  onChange={(e) => setAcceptJust(e.target.value)}
                  placeholder="Riesgo asumido por dirección: exposición mitigada por control X"
                />
              </div>
              <div>
                <Label htmlFor="acc-by" className="text-xs">
                  Aprobado por
                </Label>
                <Input
                  id="acc-by"
                  value={acceptApproved}
                  onChange={(e) => setAcceptApproved(e.target.value)}
                  placeholder="Consejera Delegada — Maria Pérez"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAccept(false)}
                >
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  onClick={markAccepted}
                  disabled={patch.isPending}
                >
                  Registrar aceptación
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-0.5 text-sm text-fulkro-primary-700",
          mono && "font-mono text-[13px]",
        )}
      >
        {value}
      </dd>
    </div>
  );
}
