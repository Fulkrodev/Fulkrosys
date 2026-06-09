"use client";

/**
 * AdminAnnotationsReview · CLUSTER 3 Phase C1.3 · admin annotation review.
 *
 * Lista todas las anotaciones del proyecto creadas por auditor portal users
 * + form respuesta por anotación + status workflow (open → admin_reviewed →
 * resolved | dismissed). Project-scoped (R23 admin) · breadcrumb /admin/projects/{id}.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ClipboardCheck, Loader2 } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  type AdminAnnotationPatchRequest,
  type AnnotationListResponse,
  type AnnotationOut,
  type AnnotationStatus,
  SEVERITY_LABEL,
  SEVERITY_VARIANT,
  STATUS_LABEL,
  STATUS_VARIANT,
  TARGET_TYPE_LABEL,
  listAnnotationsAdmin,
  patchAnnotationAdmin,
} from "@/lib/api/auditor-annotations";

interface Props {
  projectId: string;
}

const STATUS_FILTER_VALUES: { value: AnnotationStatus | "all"; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "open", label: "Abiertas" },
  { value: "admin_reviewed", label: "Revisadas" },
  { value: "resolved", label: "Resueltas" },
  { value: "dismissed", label: "Descartadas" },
];

export function AdminAnnotationsReview({ projectId }: Props) {
  const [statusFilter, setStatusFilter] = React.useState<
    AnnotationStatus | "all"
  >("all");

  const query = useQuery<AnnotationListResponse>({
    queryKey: ["admin", "audit", "annotations", projectId, statusFilter],
    queryFn: () =>
      listAnnotationsAdmin(
        projectId,
        statusFilter !== "all" ? { status: statusFilter } : undefined,
      ),
    staleTime: 15_000,
  });

  return (
    <div className="space-y-4" data-testid="admin-annotations-review">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ClipboardCheck
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Anotaciones del auditor
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor="admin-annotations-status-filter">Estado</Label>
            <Select
              value={statusFilter}
              onValueChange={(v) =>
                setStatusFilter(v as AnnotationStatus | "all")
              }
            >
              <SelectTrigger
                id="admin-annotations-status-filter"
                className="w-48"
                aria-label="Filtrar anotaciones por estado"
                data-testid="admin-annotations-status-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_FILTER_VALUES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {query.data ? (
              <span
                className="text-fulkro-ink-500"
                data-testid="admin-annotations-total"
              >
                {query.data.total} anotaciones
              </span>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <div
          className="flex items-center gap-2 text-sm text-fulkro-ink-500"
          data-testid="admin-annotations-loading"
        >
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Cargando anotaciones…
        </div>
      ) : null}

      {query.isError ? (
        <Alert variant="danger" data-testid="admin-annotations-error">
          <AlertCircle size={14} aria-hidden="true" />
          <AlertTitle>No se pudieron cargar las anotaciones</AlertTitle>
          <AlertDescription>
            Reintenta más tarde.
          </AlertDescription>
        </Alert>
      ) : null}

      {query.data && query.data.items.length === 0 ? (
        <Alert>
          <AlertTitle>Sin anotaciones</AlertTitle>
          <AlertDescription>
            No hay anotaciones para los filtros aplicados.
          </AlertDescription>
        </Alert>
      ) : null}

      {query.data?.items.map((a) => (
        <AdminAnnotationCard
          key={a.id}
          projectId={projectId}
          annotation={a}
        />
      ))}
    </div>
  );
}

function AdminAnnotationCard({
  projectId,
  annotation,
}: {
  projectId: string;
  annotation: AnnotationOut;
}) {
  const queryClient = useQueryClient();
  const [response, setResponse] = React.useState(
    annotation.admin_response ?? "",
  );
  const [status, setStatus] = React.useState<AnnotationStatus>(annotation.status);

  const patchMut = useMutation({
    mutationFn: async () => {
      const body: AdminAnnotationPatchRequest = {};
      if (response.trim() !== (annotation.admin_response ?? "")) {
        body.admin_response = response.trim();
      }
      if (status !== annotation.status) {
        body.status = status;
      }
      if (!body.admin_response && !body.status) {
        throw new Error("No hay cambios por guardar");
      }
      return patchAnnotationAdmin(projectId, annotation.id, body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "audit", "annotations", projectId],
      });
    },
  });

  return (
    <Card data-testid={`admin-annotation-card-${annotation.id}`}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <Badge variant={SEVERITY_VARIANT[annotation.flag_severity]}>
            {SEVERITY_LABEL[annotation.flag_severity]}
          </Badge>
          <span className="text-sm text-fulkro-ink-900">
            {TARGET_TYPE_LABEL[annotation.target_type]}
          </span>
          <Badge variant={STATUS_VARIANT[annotation.status]}>
            {STATUS_LABEL[annotation.status]}
          </Badge>
          <span className="text-[11px] text-fulkro-ink-500">
            {new Date(annotation.created_at).toLocaleString()}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-50 p-3">
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Anotación del auditor
          </p>
          <p className="whitespace-pre-wrap text-fulkro-ink-900">
            {annotation.annotation_text}
          </p>
          <p className="mt-1 text-[10px] font-mono text-fulkro-ink-500">
            target_id: {annotation.target_id}
          </p>
        </div>

        <div>
          <Label htmlFor={`admin-response-${annotation.id}`}>
            Respuesta del consultor
          </Label>
          <Textarea
            id={`admin-response-${annotation.id}`}
            rows={3}
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="Documenta la respuesta para el auditor (queda en audit log)…"
            data-testid={`admin-annotation-response-${annotation.id}`}
            aria-label="Respuesta del consultor"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Label htmlFor={`admin-status-${annotation.id}`}>Nuevo estado</Label>
          <Select
            value={status}
            onValueChange={(v) => setStatus(v as AnnotationStatus)}
          >
            <SelectTrigger
              id={`admin-status-${annotation.id}`}
              className="w-48"
              aria-label="Nuevo estado de la anotación"
              data-testid={`admin-annotation-status-${annotation.id}`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">Abierta</SelectItem>
              <SelectItem value="admin_reviewed">Revisada</SelectItem>
              <SelectItem value="resolved">Resuelta</SelectItem>
              <SelectItem value="dismissed">Descartada</SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => patchMut.mutate()}
            disabled={patchMut.isPending}
            data-testid={`admin-annotation-submit-${annotation.id}`}
          >
            {patchMut.isPending ? "Guardando…" : "Guardar respuesta"}
          </Button>
        </div>

        {patchMut.isError ? (
          <Alert variant="danger">
            <AlertCircle size={14} aria-hidden="true" />
            <AlertTitle>No se pudo guardar la respuesta</AlertTitle>
            <AlertDescription>
              {patchMut.error instanceof Error
                ? patchMut.error.message
                : "Error desconocido"}
            </AlertDescription>
          </Alert>
        ) : null}

        {annotation.admin_responded_at ? (
          <p className="text-[11px] text-fulkro-ink-500">
            Última respuesta: {annotation.admin_responded_by ?? "—"} ·{" "}
            {new Date(annotation.admin_responded_at).toLocaleString()}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
