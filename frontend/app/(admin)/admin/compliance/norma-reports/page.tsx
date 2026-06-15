"use client";

/**
 * /admin/compliance/norma-reports · per-norma compliance posture dashboard.
 *
 * Lists every registered norma plugin (RGPD, NIS2, ISO 27001, ...) with
 * its latest score, status badge and a "Run report" button that triggers
 * an ad-hoc generation via the admin API.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  ExternalLink,
  FileText,
  Loader2,
  PlayCircle,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listNormas,
  runNormaReport,
  type NormaSummary,
} from "@/lib/admin-compliance-monitor/norma-api";
import { cn } from "@/lib/utils";


const STATUS_DOT: Record<NonNullable<NormaSummary["latest_status"]>, string> = {
  green: "bg-emerald-500",
  yellow: "bg-amber-500",
  red: "bg-red-500",
  unknown: "bg-slate-400",
};

const STATUS_BADGE_VARIANT: Record<
  NonNullable<NormaSummary["latest_status"]>,
  "success" | "warning" | "danger" | "outline"
> = {
  green: "success",
  yellow: "warning",
  red: "danger",
  unknown: "outline",
};

const PRIORITY_BADGE_VARIANT: Record<string, "danger" | "warning" | "outline"> = {
  critical: "danger",
  high: "warning",
  medium: "outline",
  low: "outline",
};


function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


export default function NormaReportsPage() {
  const qc = useQueryClient();
  const normasQuery = useQuery({
    queryKey: ["compliance", "normas"],
    queryFn: listNormas,
    refetchInterval: 60_000,
  });
  const runMutation = useMutation({
    mutationFn: runNormaReport,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance", "normas"] });
    },
  });

  const normas = normasQuery.data ?? [];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <ShieldCheck className="h-6 w-6" />
          Reportes por Normativa
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Estado de cumplimiento agregado por norma regulatoria
          (RGPD · LOPDGDD · LSSI-CE · NIS2 · AEPD cookies · ISO 27001 · ENS).
          Cada plugin agrega los checks pertinentes del Self-Monitoring y
          calcula un score ponderado.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {normasQuery.isLoading
          ? [...Array(7)].map((_, i) => <Skeleton key={i} className="h-44 w-full" />)
          : normas.map((norma) => (
              <NormaCard
                key={norma.norma_key}
                norma={norma}
                pending={
                  runMutation.isPending &&
                  runMutation.variables === norma.norma_key
                }
                onRun={() => runMutation.mutate(norma.norma_key)}
              />
            ))}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Sobre los reportes por normativa</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-700">
          <p>
            Cada normativa es un <strong>plugin</strong> autodescubierto al
            arrancar la aplicación. Añadir una nueva norma (DORA · AI Act ·
            NIS3 cuando proceda) es crear un nuevo archivo en{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
              backend/app/motors/m_compliance_monitor/normas/
            </code>{" "}
            y registrarla con <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">NormaRegistry.register()</code>.
            No hay que modificar el motor.
          </p>
          <p>
            La planificación Celery se construye automáticamente desde el
            registro (semanal / mensual / trimestral según el plugin).
            Cuando el score baja del 85 % o la norma es <em>critical</em>,
            FULKRO genera un email a Marcos.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}


function NormaCard({
  norma,
  pending,
  onRun,
}: {
  norma: NormaSummary;
  pending: boolean;
  onRun: () => void;
}) {
  const status = norma.latest_status ?? "unknown";
  const score = norma.latest_score;

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{norma.norma_name}</CardTitle>
            <a
              href={norma.regulatory_basis_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-xs text-slate-500 hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              base regulatoria
            </a>
          </div>
          <Badge variant={PRIORITY_BADGE_VARIANT[norma.priority] ?? "outline"}>
            {norma.priority}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-slate-900">
              {score !== null ? `${score.toFixed(1)}%` : "—"}
            </span>
            <span
              className={cn(
                "inline-block h-2.5 w-2.5 rounded-full",
                STATUS_DOT[status],
              )}
              aria-hidden
            />
            <Badge variant={STATUS_BADGE_VARIANT[status]}>{status}</Badge>
          </div>
          <div className="mt-3 flex items-center gap-1 text-xs text-slate-500">
            <CalendarDays className="h-3 w-3" />
            Último reporte: {formatDate(norma.latest_generated_at)}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Frecuencia <code>{norma.frequency}</code> ·{" "}
            {norma.checks_owned.length} checks
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={onRun}
          >
            {pending ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <PlayCircle className="mr-1 h-4 w-4" />
            )}
            Generar reporte
          </Button>
          <Link
            href={`/admin/compliance/norma-reports/${norma.norma_key}`}
            className="inline-flex items-center rounded-md px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            <FileText className="mr-1 h-4 w-4" />
            Historial
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
