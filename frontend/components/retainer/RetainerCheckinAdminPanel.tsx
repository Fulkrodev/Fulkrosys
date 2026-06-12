"use client";

/**
 * RetainerCheckinAdminPanel · curación admin de los check-ins trimestrales.
 * feat/fulkro-100 · Ola 3 (retainer P0).
 *
 * Marcos GENERA el borrador, lo CURA (aprueba) y lo ENVÍA al cliente. Antes
 * esto solo lo hacían los tests / el beat Celery → Marcos no tenía cómo actuar.
 * Workflow: draft → curated_by_admin → sent_to_client (→ el cliente lo revisa).
 * R30 admin · require_owner backend.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileText, Send, CheckCircle2, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  retainerCheckinAdminApi,
  type AdminCheckinReport,
} from "@/lib/api/retainer-checkin-admin";

interface Props {
  projectId: string;
}

const STATUS_META: Record<
  string,
  { label: string; variant: "secondary" | "default" | "outline" }
> = {
  draft: { label: "Borrador", variant: "outline" },
  curated_by_admin: { label: "Curado", variant: "secondary" },
  sent_to_client: { label: "Enviado al cliente", variant: "default" },
};

export function RetainerCheckinAdminPanel({ projectId }: Props) {
  const queryClient = useQueryClient();
  const KEY = ["admin-retainer-checkins", projectId];

  const { data: reports, isLoading } = useQuery({
    queryKey: KEY,
    queryFn: () => retainerCheckinAdminApi.list(projectId),
    staleTime: 30_000,
  });

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: KEY });

  const generate = useMutation({
    mutationFn: () => retainerCheckinAdminApi.generate(projectId),
    onSuccess: () => {
      invalidate();
      toast.success("Borrador del check-in generado.");
    },
    onError: (e: unknown) =>
      toast.error(
        e instanceof Error && e.message
          ? e.message
          : "No se pudo generar (¿retainer activo?).",
      ),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" /> Check-ins trimestrales
          </CardTitle>
          <CardDescription>
            Genera, revisa y envía al cliente el informe trimestral del retainer.
          </CardDescription>
        </div>
        <Button
          size="sm"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          data-testid="retainer-checkin-generate"
        >
          <Plus className="mr-1 h-4 w-4" /> Generar trimestre actual
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !reports || reports.length === 0 ? (
          <p
            className="text-sm text-muted-foreground"
            data-testid="retainer-checkin-empty"
          >
            Aún no hay check-ins. Genera el del trimestre actual para empezar.
          </p>
        ) : (
          reports.map((r) => (
            <CheckinRow
              key={r.id}
              report={r}
              onChanged={invalidate}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function CheckinRow({
  report,
  onChanged,
}: {
  report: AdminCheckinReport;
  onChanged: () => void;
}) {
  const meta = STATUS_META[report.admin_curation_status] ?? {
    label: report.admin_curation_status,
    variant: "outline" as const,
  };

  const curate = useMutation({
    mutationFn: () => retainerCheckinAdminApi.curate(report.id),
    onSuccess: () => {
      onChanged();
      toast.success("Check-in curado. Ya puedes enviarlo al cliente.");
    },
    onError: () => toast.error("No se pudo curar el check-in."),
  });

  const send = useMutation({
    mutationFn: () => retainerCheckinAdminApi.send(report.id),
    onSuccess: () => {
      onChanged();
      toast.success("Check-in enviado al cliente.");
    },
    onError: () => toast.error("No se pudo enviar el check-in."),
  });

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white p-3"
      data-testid={`retainer-checkin-row-${report.id}`}
    >
      <div className="min-w-0">
        <p className="font-medium">{report.period_quarter}</p>
        {report.sent_at && (
          <p className="text-xs text-muted-foreground">
            Enviado {new Date(report.sent_at).toLocaleDateString("es-ES")}
            {report.client_review_status
              ? ` · cliente: ${report.client_review_status}`
              : ""}
          </p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge variant={meta.variant}>{meta.label}</Badge>
        {report.admin_curation_status === "draft" && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => curate.mutate()}
            disabled={curate.isPending}
            data-testid={`retainer-checkin-curate-${report.id}`}
          >
            <CheckCircle2 className="mr-1 h-4 w-4" /> Curar
          </Button>
        )}
        {report.admin_curation_status === "curated_by_admin" && (
          <Button
            size="sm"
            onClick={() => send.mutate()}
            disabled={send.isPending}
            data-testid={`retainer-checkin-send-${report.id}`}
          >
            <Send className="mr-1 h-4 w-4" /> Enviar al cliente
          </Button>
        )}
      </div>
    </div>
  );
}
