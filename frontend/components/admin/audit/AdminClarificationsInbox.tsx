"use client";

/**
 * AdminClarificationsInbox · CLUSTER 3 Phase C2.3 · SSE realtime admin inbox.
 *
 * Lista clarifications del proyecto · filter status + priority · inline form
 * respuesta per row · SSE subscribe useProjectEvents reuse (MB-13.3 pattern) ·
 * realtime toast cuando auditor crea nueva (auditor_clarification_new event ·
 * tanstack invalidate query refetch automático).
 *
 * Project-scoped (R23 admin) · breadcrumb /admin/projects/{id}/audit/clarifications.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ClipboardCheck, Loader2, MessageCircle } from "lucide-react";
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
import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";
import {
  type AdminClarificationPatchRequest,
  type ClarificationListResponse,
  type ClarificationOut,
  type ClarificationPriority,
  type ClarificationStatus,
  PRIORITY_LABEL,
  PRIORITY_VARIANT,
  STATUS_LABEL,
  STATUS_VARIANT,
  TARGET_TYPE_LABEL,
  listClarificationsAdmin,
  patchClarificationAdmin,
} from "@/lib/api/auditor-clarifications";

interface Props {
  projectId: string;
}

const STATUS_OPTIONS: { value: ClarificationStatus | "all"; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "open", label: "Abiertas" },
  { value: "in_progress", label: "En revisión" },
  { value: "responded", label: "Respondidas" },
  { value: "closed", label: "Cerradas" },
];

const PRIORITY_OPTIONS: {
  value: ClarificationPriority | "all";
  label: string;
}[] = [
  { value: "all", label: "Todas" },
  { value: "urgent", label: "Urgente" },
  { value: "high", label: "Alta" },
  { value: "normal", label: "Normal" },
  { value: "low", label: "Baja" },
];

export function AdminClarificationsInbox({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = React.useState<
    ClarificationStatus | "all"
  >("all");
  const [priorityFilter, setPriorityFilter] = React.useState<
    ClarificationPriority | "all"
  >("all");
  const [newSinceMount, setNewSinceMount] = React.useState(0);

  const query = useQuery<ClarificationListResponse>({
    queryKey: [
      "admin",
      "audit",
      "clarifications",
      projectId,
      statusFilter,
      priorityFilter,
    ],
    queryFn: () =>
      listClarificationsAdmin(projectId, {
        status: statusFilter !== "all" ? statusFilter : undefined,
        priority: priorityFilter !== "all" ? priorityFilter : undefined,
      }),
    staleTime: 15_000,
  });

  // SSE subscription · §2.7 audit-2026-06-15: una SOLA conexión SSE (antes este
  // componente abría un 2º EventSource al mismo canal). auditor_clarification_new
  // lo sirve el propio hook vía onClarificationNew.
  useProjectEvents({
    projectId,
    onClarificationNew: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "audit", "clarifications", projectId],
      });
      setNewSinceMount((n) => n + 1);
    },
  });

  return (
    <div className="space-y-4" data-testid="admin-clarifications-inbox">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <MessageCircle
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Aclaraciones del auditor
            {newSinceMount > 0 ? (
              <Badge
                variant="info"
                className="ml-2"
                data-testid="admin-clarifications-new-counter"
              >
                {newSinceMount} nueva{newSinceMount > 1 ? "s" : ""} desde inicio sesión
              </Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor="admin-clarif-status-filter">Estado</Label>
            <Select
              value={statusFilter}
              onValueChange={(v) =>
                setStatusFilter(v as ClarificationStatus | "all")
              }
            >
              <SelectTrigger
                id="admin-clarif-status-filter"
                className="w-44"
                aria-label="Filtrar por estado"
                data-testid="admin-clarif-status-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Label htmlFor="admin-clarif-priority-filter">Prioridad</Label>
            <Select
              value={priorityFilter}
              onValueChange={(v) =>
                setPriorityFilter(v as ClarificationPriority | "all")
              }
            >
              <SelectTrigger
                id="admin-clarif-priority-filter"
                className="w-32"
                aria-label="Filtrar por prioridad"
                data-testid="admin-clarif-priority-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {query.data ? (
              <span
                className="text-fulkro-ink-500"
                data-testid="admin-clarifications-total"
              >
                {query.data.total} aclaraciones
              </span>
            ) : null}
          </div>
          <Alert>
            <AlertTitle>Notificación en tiempo real</AlertTitle>
            <AlertDescription>
              Esta página se actualiza automáticamente cuando el auditor envía
              nuevas aclaraciones (Server-Sent Events). También recibirás un
              correo electrónico de respaldo por cada solicitud.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <div
          className="flex items-center gap-2 text-sm text-fulkro-ink-500"
          data-testid="admin-clarifications-loading"
        >
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Cargando aclaraciones…
        </div>
      ) : null}

      {query.isError ? (
        <Alert variant="danger" data-testid="admin-clarifications-error">
          <AlertCircle size={14} aria-hidden="true" />
          <AlertTitle>No se pudieron cargar las aclaraciones</AlertTitle>
          <AlertDescription>Reintenta más tarde.</AlertDescription>
        </Alert>
      ) : null}

      {query.data && query.data.items.length === 0 ? (
        <Alert>
          <AlertTitle>Sin aclaraciones</AlertTitle>
          <AlertDescription>
            No hay aclaraciones para los filtros aplicados.
          </AlertDescription>
        </Alert>
      ) : null}

      {query.data?.items.map((c) => (
        <AdminClarificationCard
          key={c.id}
          projectId={projectId}
          clarification={c}
        />
      ))}
    </div>
  );
}

function AdminClarificationCard({
  projectId,
  clarification,
}: {
  projectId: string;
  clarification: ClarificationOut;
}) {
  const queryClient = useQueryClient();
  const [response, setResponse] = React.useState(
    clarification.admin_response ?? "",
  );
  const [status, setStatus] = React.useState<ClarificationStatus>(
    clarification.status,
  );

  const patchMut = useMutation({
    mutationFn: async () => {
      const body: AdminClarificationPatchRequest = {};
      if (response.trim() !== (clarification.admin_response ?? "")) {
        body.admin_response = response.trim();
      }
      if (status !== clarification.status) {
        body.status = status;
      }
      if (!body.admin_response && !body.status) {
        throw new Error("No hay cambios por guardar");
      }
      return patchClarificationAdmin(projectId, clarification.id, body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "audit", "clarifications", projectId],
      });
    },
  });

  return (
    <Card data-testid={`admin-clarification-card-${clarification.id}`}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <Badge variant={PRIORITY_VARIANT[clarification.priority]}>
            {PRIORITY_LABEL[clarification.priority]}
          </Badge>
          <span className="text-sm text-fulkro-ink-900">
            {TARGET_TYPE_LABEL[clarification.linked_target_type]}
          </span>
          <Badge variant={STATUS_VARIANT[clarification.status]}>
            {STATUS_LABEL[clarification.status]}
          </Badge>
          <span className="text-[11px] text-fulkro-ink-500">
            {new Date(clarification.created_at).toLocaleString()}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-50 p-3">
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Pregunta del auditor
          </p>
          <p className="whitespace-pre-wrap text-fulkro-ink-900">
            {clarification.question_text}
          </p>
          {clarification.linked_target_id ? (
            <p className="mt-1 font-mono text-[10px] text-fulkro-ink-500">
              target_id: {clarification.linked_target_id}
            </p>
          ) : null}
        </div>

        <div>
          <Label htmlFor={`admin-clarif-response-${clarification.id}`}>
            Respuesta del consultor
          </Label>
          <Textarea
            id={`admin-clarif-response-${clarification.id}`}
            rows={4}
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="Documenta la respuesta para el auditor (queda en audit log inmutable)…"
            data-testid={`admin-clarification-response-${clarification.id}`}
            aria-label="Respuesta del consultor"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Label htmlFor={`admin-clarif-status-${clarification.id}`}>
            Nuevo estado
          </Label>
          <Select
            value={status}
            onValueChange={(v) => setStatus(v as ClarificationStatus)}
          >
            <SelectTrigger
              id={`admin-clarif-status-${clarification.id}`}
              className="w-44"
              aria-label="Nuevo estado"
              data-testid={`admin-clarification-status-${clarification.id}`}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">Abierta</SelectItem>
              <SelectItem value="in_progress">En revisión</SelectItem>
              <SelectItem value="responded">Respondida</SelectItem>
              <SelectItem value="closed">Cerrada</SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => patchMut.mutate()}
            disabled={patchMut.isPending}
            data-testid={`admin-clarification-submit-${clarification.id}`}
          >
            <ClipboardCheck
              size={14}
              className="mr-1"
              aria-hidden="true"
            />
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

        {clarification.admin_responded_at ? (
          <p className="text-[11px] text-fulkro-ink-500">
            Última respuesta: {clarification.admin_responded_by ?? "—"} ·{" "}
            {new Date(clarification.admin_responded_at).toLocaleString()}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
