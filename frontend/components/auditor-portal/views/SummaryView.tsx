"use client";

/**
 * SummaryView · Phase 5.1 auditor portal · top-level overview read-only.
 *
 * Cliente branding propagated · friendly Spanish tone · NO admin nav leak.
 * Renders project metadata, categoría ENS, lifecycle state, audit status
 * + counts agregados (DdA · evidence · MAGERIT · pentest) para overview.
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, BadgeCheck, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getAuditorPortalSummary,
  type AuditorPortalSummary,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
}

const CATEGORIA_LABEL: Record<string, string> = {
  BASICA: "Básica",
  MEDIA: "Media",
  ALTA: "Alta",
};

const LIFECYCLE_LABEL: Record<string, string> = {
  diagnostico: "Diagnóstico inicial",
  implantacion: "Implantación",
  auditoria_dry_run: "Auditoría simulada (dry-run)",
  auditoria_externa: "Auditoría ENAC externa",
  certificado: "Certificado",
  renovacion: "Renovación",
};

export function SummaryView({ token }: Props) {
  const summary = useQuery<AuditorPortalSummary>({
    queryKey: ["auditor-portal", "summary", token],
    queryFn: () => getAuditorPortalSummary(token),
    enabled: Boolean(token),
    staleTime: 30_000,
    retry: false,
  });

  if (summary.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-summary-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando resumen del proyecto…
      </div>
    );
  }

  if (summary.isError || !summary.data) {
    return (
      <Alert variant="danger" data-testid="auditor-summary-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar el resumen</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  const { project, cliente, counts } = summary.data;
  const categoriaLabel = CATEGORIA_LABEL[project.categoria] ?? project.categoria;
  const lifecycleLabel = project.lifecycle_state
    ? LIFECYCLE_LABEL[project.lifecycle_state] ?? project.lifecycle_state
    : "No disponible";

  return (
    <div className="space-y-4" data-testid="auditor-summary-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BadgeCheck
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Resumen del proyecto
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Cliente
            </p>
            <p className="font-medium text-fulkro-ink-900">
              {cliente.razon_social}
            </p>
            {cliente.cif ? (
              <p className="text-[12px] text-fulkro-ink-500">{cliente.cif}</p>
            ) : null}
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Proyecto
            </p>
            <p className="font-medium text-fulkro-ink-900">{project.nombre}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Categoría ENS
            </p>
            <p
              className="font-medium text-fulkro-ink-900"
              data-testid="auditor-summary-categoria"
            >
              {categoriaLabel}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Estado del ciclo de vida
            </p>
            <p className="font-medium text-fulkro-ink-900">{lifecycleLabel}</p>
          </div>
          {project.certified_at ? (
            <div>
              <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
                Certificación
              </p>
              <p className="font-medium text-fulkro-ink-900">
                {new Date(project.certified_at).toLocaleDateString()}
              </p>
            </div>
          ) : null}
          {project.audit_passed_at ? (
            <div>
              <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
                Resultado auditoría
              </p>
              <p className="font-medium text-fulkro-ink-900">
                {project.audit_result ?? "Sin resultado registrado"}
              </p>
              <p className="text-[12px] text-fulkro-ink-500">
                Aprobada el{" "}
                {new Date(project.audit_passed_at).toLocaleDateString()}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Volumen del expediente</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div className="rounded-md border border-fulkro-ink-300/60 p-3">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              DdA · Medidas
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-summary-count-dda"
            >
              {counts.dda_entries}
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-300/60 p-3">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Evidencias
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-summary-count-evidence"
            >
              {counts.evidence_files}
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-300/60 p-3">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Análisis MAGERIT
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-summary-count-magerit"
            >
              {counts.magerit_analyses}
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-300/60 p-3">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Pentest runs
            </p>
            <p
              className="text-xl font-semibold text-fulkro-ink-900"
              data-testid="auditor-summary-count-pentest"
            >
              {counts.pentest_runs}
            </p>
          </div>
        </CardContent>
      </Card>

      <Alert>
        <AlertTitle>Acceso de solo lectura</AlertTitle>
        <AlertDescription>
          Toda interacción con este portal queda registrada en el registro de auditoría
          inmutable del cliente (hash chain Ed25519 verificable).
        </AlertDescription>
      </Alert>
    </div>
  );
}
