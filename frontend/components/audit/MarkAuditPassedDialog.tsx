"use client";

/**
 * MarkAuditPassedDialog · admin Marcos marca resultado auditoría ENAC.
 *
 * Sesión 3B-2B.6 Cluster 1 Phase 2 · post entrega ZIP firmado (Phase 1)
 * y feedback auditor offline · Marcos selecciona result (passed/observed/
 * correction_required/failed) + audit_report_ref opcional + confirma
 * cascade certify si result=passed (default true).
 *
 * Si result==passed AND cascade · backend chains mark_certified · lifecycle
 * advance CERTIFIED · Phase 3 workflow hook trigger retainer offer.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, AlertTriangle, XCircle, Wrench, type LucideIcon } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  markAuditPassed,
  type AuditResult,
  type MarkAuditPassedResponse,
} from "@/lib/api/audit-passed";

interface Props {
  projectId: string;
}

const RESULT_OPTIONS: Array<{
  value: AuditResult;
  label: string;
  description: string;
  icon: LucideIcon;
  variant: "success" | "warning" | "danger" | "info";
}> = [
  {
    value: "passed",
    label: "Pasada",
    description: "Auditoría favorable · cascada lifecycle CERTIFIED + oferta retainer",
    icon: CheckCircle2,
    variant: "success",
  },
  {
    value: "observed",
    label: "Con observaciones",
    description: "Observaciones menores · NO bloquean cert · feedback auditor",
    icon: AlertTriangle,
    variant: "warning",
  },
  {
    value: "correction_required",
    label: "Requiere correcciones",
    description: "Bloquea cert hasta resolver · plan de acción cliente",
    icon: Wrench,
    variant: "info",
  },
  {
    value: "failed",
    label: "No pasada",
    description: "Auditoría desfavorable · re-evaluar plan completo",
    icon: XCircle,
    variant: "danger",
  },
];

export function MarkAuditPassedDialog({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = React.useState<AuditResult | null>(null);
  const [reportRef, setReportRef] = React.useState("");
  const [cascade, setCascade] = React.useState(true);
  const [response, setResponse] = React.useState<MarkAuditPassedResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      markAuditPassed(projectId, {
        result: selected!,
        audit_report_ref: reportRef.trim() || null,
        cascade_certify: cascade,
      }),
    onSuccess: (data) => {
      setResponse(data);
      void queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      void queryClient.invalidateQueries({ queryKey: ["lifecycle", projectId] });
    },
  });

  if (response) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CheckCircle2 size={16} className="text-fulkro-success-700" />
            Resultado registrado
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-fulkro-ink-500">Resultado</p>
              <p className="font-medium">{response.result}</p>
            </div>
            <div>
              <p className="text-fulkro-ink-500">Estado proyecto</p>
              <p className="font-medium">{response.lifecycle_state}</p>
            </div>
            <div>
              <p className="text-fulkro-ink-500">Marcado en</p>
              <p className="font-mono text-[11px]">{response.audit_passed_at}</p>
            </div>
            {response.audit_report_ref ? (
              <div>
                <p className="text-fulkro-ink-500">Ref. informe</p>
                <p className="font-mono text-[11px]">{response.audit_report_ref}</p>
              </div>
            ) : null}
          </div>
          {response.certified_event_id ? (
            <Alert variant="success">
              <AlertTitle>Proyecto certificado · cascada activada</AlertTitle>
              <AlertDescription>
                Lifecycle CERTIFIED registrado · Phase 3 retainer offer
                quedará disponible automáticamente.
              </AlertDescription>
            </Alert>
          ) : null}
          {response.certified_skipped_reason ? (
            <Alert variant="info">
              <AlertTitle>Cascada certificación omitida</AlertTitle>
              <AlertDescription>{response.certified_skipped_reason}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CheckCircle2 size={16} /> Marcar resultado auditoría ENAC
        </CardTitle>
        <p className="mt-1 text-xs text-fulkro-ink-500">
          Marcos registra el veredicto del auditor tras revisar el ZIP firmado.
          Si resultado=Pasada · cascada lifecycle CERTIFIED + retainer offer.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label className="text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
            Resultado auditoría
          </Label>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {RESULT_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const active = selected === opt.value;
              return (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => setSelected(opt.value)}
                  className={`flex items-start gap-2 rounded-md border px-3 py-2 text-left text-xs transition-colors ${
                    active
                      ? "border-fulkro-primary-700 bg-fulkro-primary-700/5"
                      : "border-fulkro-ink-300/60 hover:bg-fulkro-ink-50"
                  }`}
                  data-testid={`audit-result-option-${opt.value}`}
                >
                  <Icon size={14} className="mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium text-fulkro-ink-700">{opt.label}</p>
                    <p className="mt-0.5 text-[11px] leading-snug text-fulkro-ink-500">
                      {opt.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="audit-report-ref" className="text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
            Referencia informe auditor (opcional)
          </Label>
          <Input
            id="audit-report-ref"
            value={reportRef}
            onChange={(e) => setReportRef(e.target.value)}
            placeholder="E-702-ENAC-001 · número certificado · etc"
            maxLength={120}
          />
        </div>

        {selected === "passed" ? (
          <label className="flex items-start gap-2 text-xs text-fulkro-ink-700">
            <input
              type="checkbox"
              checked={cascade}
              onChange={(e) => setCascade(e.target.checked)}
              className="mt-0.5"
              data-testid="audit-cascade-checkbox"
            />
            <span>
              <span className="font-medium">Cascada certificación automática.</span>
              {" "}
              Si marcado, registrará lifecycle CERTIFIED + habilitará oferta
              retainer cliente (recomendado · desmarcar solo si quieres separar el
              registro del estado certificado).
            </span>
          </label>
        ) : null}

        {mutation.isError ? (
          <Alert variant="danger">
            <AlertTitle>Error al marcar resultado</AlertTitle>
            <AlertDescription>
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Error desconocido"}
            </AlertDescription>
          </Alert>
        ) : null}

        <Button
          type="button"
          variant="primary"
          size="md"
          disabled={!selected || mutation.isPending}
          onClick={() => mutation.mutate()}
          data-testid="audit-mark-submit"
        >
          {mutation.isPending ? "Registrando…" : "Registrar resultado"}
        </Button>
      </CardContent>
    </Card>
  );
}
