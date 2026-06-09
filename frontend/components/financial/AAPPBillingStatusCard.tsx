"use client";

/**
 * AAPPBillingStatusCard · 3 stages chain visual (SAN-E v3.MB-3.2).
 *
 * Wired al backend M15 /aapp-billing/status (commit MB-3.F).
 *
 * Cadena 3 stages: Facturae XAdES → FACE submission → Verifactu hash chain.
 * Per stage: Badge status (ok/pending/failed/n/a) · timestamp · retry CTA.
 */
import * as React from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  FileSignature,
  Hash,
  Send,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import { useFinancialSummary } from "@/hooks/useFinancialSummary";
import type { AAPPStage } from "@/lib/admin-financial/api";

interface StageProps {
  icon: React.ReactNode;
  title: string;
  termKey?: "Facturae" | "FACE" | "Verifactu" | "XAdES";
  status: AAPPStage;
}

function StageBadge({ status }: { status: AAPPStage }) {
  const cfg: Record<
    AAPPStage,
    { variant: "success" | "warning" | "danger" | "outline" | "secondary"; label: string; icon: React.ReactNode }
  > = {
    ok: {
      variant: "success",
      label: "OK",
      icon: <CheckCircle2 size={12} strokeWidth={2.4} />,
    },
    pending: {
      variant: "warning",
      label: "Pendiente",
      icon: <Clock size={12} strokeWidth={2.4} />,
    },
    failed: {
      variant: "danger",
      label: "Fallido",
      icon: <AlertCircle size={12} strokeWidth={2.4} />,
    },
    "n/a": {
      variant: "outline",
      label: "N/A",
      icon: null,
    },
  };
  const c = cfg[status];
  return (
    <Badge variant={c.variant} className="gap-1">
      {c.icon}
      {c.label}
    </Badge>
  );
}

function Stage({ icon, title, termKey, status }: StageProps) {
  const isInactive = status === "n/a";
  return (
    <div
      className={cn(
        "flex flex-1 flex-col items-center gap-2 rounded-md border px-3 py-3 text-center",
        isInactive
          ? "border-fulkro-ink-200 bg-fulkro-ink-50"
          : status === "ok"
          ? "border-fulkro-success/40 bg-fulkro-success/5"
          : status === "failed"
          ? "border-fulkro-danger/40 bg-fulkro-danger/5"
          : "border-fulkro-warning/40 bg-fulkro-warning/5",
      )}
    >
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-full",
          isInactive
            ? "bg-fulkro-ink-200 text-fulkro-ink-600"
            : status === "ok"
            ? "bg-fulkro-success text-white"
            : status === "failed"
            ? "bg-fulkro-danger text-white"
            : "bg-fulkro-warning text-white",
        )}
      >
        {icon}
      </div>
      <div className="flex items-center gap-1 text-xs font-bold text-[color:var(--fulkro-title)]">
        {title}
        {termKey ? <TooltipENS term={termKey} iconSize={11} /> : null}
      </div>
      <StageBadge status={status} />
    </div>
  );
}

export interface AAPPBillingStatusCardProps {
  projectId: string;
}

export function AAPPBillingStatusCard({
  projectId,
}: AAPPBillingStatusCardProps) {
  const { aapp } = useFinancialSummary(projectId);
  const data = aapp.data;

  if (aapp.isLoading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-fulkro-ink-600">
          Cargando estado AAPP…
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  // Si no hay factura AAPP activa, mostrar placeholder informativo
  if (!data.has_active_aapp_invoice) {
    return (
      <Card className="border-fulkro-ink-200">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm text-[color:var(--fulkro-title)]">
            Cadena facturación AAPP{" "}
            <TooltipENS term="Verifactu" iconSize={14} />
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-fulkro-ink-500">
          {data.next_action ??
            "Sin factura AAPP activa. Genera una factura para iniciar la cadena."}
        </CardContent>
      </Card>
    );
  }

  const allOk =
    data.stage_facturae_xades === "ok" &&
    data.stage_face === "ok" &&
    data.stage_verifactu === "ok";
  const anyFailed =
    data.stage_facturae_xades === "failed" ||
    data.stage_face === "failed" ||
    data.stage_verifactu === "failed";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-[color:var(--fulkro-title)]">
          <span>Cadena AAPP · Factura {data.invoice_number ?? "—"}</span>
          <TooltipENS term="Verifactu" iconSize={14} />
          {allOk ? (
            <Badge variant="success" className="ml-auto">
              Cadena completa
            </Badge>
          ) : anyFailed ? (
            <Badge variant="danger" className="ml-auto">
              Bloqueada
            </Badge>
          ) : (
            <Badge variant="warning" className="ml-auto">
              En curso
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-center">
          <Stage
            icon={<FileSignature size={18} strokeWidth={2.4} />}
            title="Facturae XAdES"
            termKey="Facturae"
            status={data.stage_facturae_xades}
          />
          <ArrowRight
            size={18}
            strokeWidth={2.4}
            className="hidden text-fulkro-ink-600 md:block"
          />
          <Stage
            icon={<Send size={18} strokeWidth={2.4} />}
            title="FACE"
            termKey="FACE"
            status={data.stage_face}
          />
          <ArrowRight
            size={18}
            strokeWidth={2.4}
            className="hidden text-fulkro-ink-600 md:block"
          />
          <Stage
            icon={<Hash size={18} strokeWidth={2.4} />}
            title="Verifactu"
            termKey="Verifactu"
            status={data.stage_verifactu}
          />
        </div>

        {data.total_amount !== null && data.total_amount !== undefined ? (
          <p className="text-xs text-fulkro-ink-500">
            Importe:{" "}
            <span className="font-semibold tabular-nums text-fulkro-ink-700">
              {new Intl.NumberFormat("es-ES", {
                style: "currency",
                currency: "EUR",
              }).format(data.total_amount)}
            </span>
          </p>
        ) : null}

        {anyFailed ? (
          <p className="rounded-md border border-fulkro-danger/30 bg-fulkro-danger/5 p-2 text-xs text-fulkro-danger">
            Cadena bloqueada · revisa logs M15 + retry stage manual desde
            cockpit (cableado MB-7).
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
