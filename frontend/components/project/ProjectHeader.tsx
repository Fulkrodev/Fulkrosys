/**
 * ProjectHeader · Composer cabecera del proyecto (FASE 9.B / MB-4.C.1).
 *
 * Backend: GET /api/v1/projects/{project_id}/header (composer cross-motor).
 * Aglutina:
 *   - Project (fase + categoría ENS + lifecycle_state + fechas)
 *   - Cliente (nombre + cif + sector + provincia)
 *   - RSEG + CISO contacts (M30)
 *   - Conformity snapshot (M27 · route_status + counts)
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, Loader2, ShieldCheck, UserCheck } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";

interface ContactInfo {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role_title: string;
  role_category: string;
}

interface ProjectHeaderResponse {
  project: {
    id: string;
    nombre: string;
    fase: string;
    categoria_objetivo: string | null;
    lifecycle_state: string | null;
    fecha_kickoff: string | null;
    fecha_objetivo_certificacion: string | null;
    certified_at: string | null;
  };
  cliente: {
    id: string;
    nombre: string;
    cif: string;
    sector: string | null;
    provincia: string | null;
  };
  rseg_contact: ContactInfo | null;
  ciso_contact: ContactInfo | null;
  conformity: {
    route_status: string | null;
    route_type: string | null;
    expiration_date: string | null;
    submissions_count: number;
    renewals_count: number;
    material_changes_count: number;
  };
}

const CATEGORIA_TONE: Record<string, "secondary" | "warning" | "success"> = {
  BASICA: "secondary",
  MEDIA: "warning",
  ALTA: "success",
};

export function ProjectHeader({ projectId }: { projectId: string }) {
  const { data, isLoading, isError, error } = useQuery<ProjectHeaderResponse>({
    queryKey: ["project-composer", "header", projectId],
    queryFn: () =>
      api<ProjectHeaderResponse>(`/api/v1/projects/${projectId}/header`),
    enabled: Boolean(projectId),
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> cargando proyecto…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar la cabecera</AlertTitle>
            <AlertDescription>
              {error instanceof Error ? error.message : "Error desconocido"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const { project, cliente, rseg_contact, ciso_contact, conformity } = data;
  const categoriaTone = project.categoria_objetivo
    ? CATEGORIA_TONE[project.categoria_objetivo] ?? "secondary"
    : "secondary";

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span
              style={{
                backgroundColor: "var(--fulkro-surface-glass-strong)",
                color: "var(--fulkro-subtitle)",
              }}
              className="mt-1 rounded-lg p-2.5"
            >
              <Building2 size={22} strokeWidth={2.2} />
            </span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-fulkro-ink-500">
                Proyecto
              </p>
              <CardTitle className="mt-0.5 text-lg font-semibold">
                {cliente.nombre}
              </CardTitle>
              <p className="mt-0.5 text-sm text-fulkro-ink-700">
                {project.nombre}
              </p>
              <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
                CIF {cliente.cif}
                {cliente.sector ? ` · ${cliente.sector}` : ""}
                {cliente.provincia ? ` · ${cliente.provincia}` : ""}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {project.categoria_objetivo ? (
              <Badge variant={categoriaTone}>
                ENS {project.categoria_objetivo}
              </Badge>
            ) : null}
            {project.lifecycle_state ? (
              <Badge variant="outline">{project.lifecycle_state}</Badge>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <Stat label="Fase actual" value={project.fase} />
          <Stat
            label="Conformidad"
            value={
              conformity.route_type ?? conformity.route_status ?? "no iniciada"
            }
            meta={
              conformity.expiration_date
                ? `expira ${new Date(conformity.expiration_date).toLocaleDateString()}`
                : null
            }
          />
          <Stat
            label="RSEG"
            icon={<UserCheck size={11} />}
            value={rseg_contact?.full_name ?? "—"}
            meta={rseg_contact?.email ?? null}
          />
          <Stat
            label="CISO"
            icon={<ShieldCheck size={11} />}
            value={ciso_contact?.full_name ?? "—"}
            meta={ciso_contact?.email ?? null}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  meta,
  icon,
}: {
  label: string;
  value: string;
  meta?: string | null;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-fulkro-ink-300/60 bg-white p-2.5">
      <p className="flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate text-sm font-semibold text-fulkro-ink-700">
        {value}
      </p>
      {meta ? (
        <p className="mt-0.5 truncate font-mono text-[10px] text-fulkro-ink-500">
          {meta}
        </p>
      ) : null}
    </div>
  );
}
