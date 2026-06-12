/**
 * ContinuidadBuzonAdminPanel · feat/fulkro-100 Ola A.
 *
 * Cierra el loop de sync de continuidad en el lado admin. Marcos VE el buzón:
 *  - el cuestionario que envió el cliente (RTO/RPO, procesos, activos, notas)
 *  - sus aprobaciones / peticiones de cambio sobre los borradores BIA/DRP
 * y NOTIFICA al cliente cuando deja un borrador listo (SSE continuidad.draft_ready
 * → el portal del cliente lo refresca y le invita a revisarlo).
 *
 * Realtime: se refresca solo cuando el cliente rellena el cuestionario o
 * aprueba/comenta un borrador (useProjectEvents.onContinuidadChanged · Pattern #14).
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  Inbox,
  Loader2,
  MessageSquareWarning,
} from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";
import {
  type ContinuidadBuzon,
  getContinuidadBuzon,
  notifyDraftReady,
} from "@/lib/admin-bia/api";

interface Props {
  projectId: string;
}

export function ContinuidadBuzonAdminPanel({ projectId }: Props) {
  const qc = useQueryClient();
  const queryKey = ["continuidad-buzon", projectId];

  const { data, isLoading } = useQuery<ContinuidadBuzon>({
    queryKey,
    queryFn: () => getContinuidadBuzon(projectId),
  });

  const onContinuidadChanged = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["continuidad-buzon", projectId] });
  }, [qc, projectId]);

  // Realtime: el cliente rellena/aprueba/comenta → refresca el buzón.
  useProjectEvents({ projectId, enabled: !!projectId, onContinuidadChanged });

  const [artifactType, setArtifactType] = useState<"bia" | "drp">("bia");

  const notify = useMutation({
    mutationFn: () =>
      notifyDraftReady(projectId, { artifact_type: artifactType }),
    onSuccess: () =>
      toast.success(
        "Cliente avisado · el borrador aparece en su portal para revisar/aprobar",
      ),
    onError: () => toast.error("No se pudo avisar al cliente"),
  });

  const q = data?.questionnaire ?? null;
  const approvals = data?.approvals ?? [];
  const pending = data?.pending_comments ?? 0;

  return (
    <div className="space-y-4" data-testid="continuidad-buzon-admin">
      {/* ── Buzón: lo que envió el cliente ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Inbox className="h-5 w-5" aria-hidden />
            Buzón de continuidad del cliente
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
            </div>
          )}

          {!isLoading && !data?.has_questionnaire && (
            <p className="text-muted-foreground">
              El cliente aún no ha enviado su cuestionario de continuidad
              (tolerancia RTO/RPO, procesos críticos, activos). Lo verás aquí en
              cuanto lo rellene desde su portal.
            </p>
          )}

          {q && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Metric label="RTO tolerado" value={fmtHoras(q.rto_horas_tolerancia)} />
                <Metric label="RPO tolerado" value={fmtHoras(q.rpo_horas_tolerancia)} />
                <Metric
                  label="Impacto diario"
                  value={q.impacto_diario_eur ? `${q.impacto_diario_eur} €` : "—"}
                />
              </div>

              {q.procesos_criticos && q.procesos_criticos.length > 0 && (
                <div>
                  <p className="font-medium">Procesos críticos</p>
                  <ul className="ml-4 list-disc text-muted-foreground">
                    {q.procesos_criticos.map((p, i) => (
                      <li key={i}>
                        {p.nombre}
                        {p.descripcion ? ` — ${p.descripcion}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {q.activos_core && q.activos_core.length > 0 && (
                <div>
                  <p className="font-medium">Activos core</p>
                  <ul className="ml-4 list-disc text-muted-foreground">
                    {q.activos_core.map((a, i) => (
                      <li key={i}>
                        {a.nombre}
                        {a.tipo ? ` (${a.tipo})` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {q.notas_cliente && (
                <div>
                  <p className="font-medium">Notas del cliente</p>
                  <p className="whitespace-pre-wrap text-muted-foreground">
                    {q.notas_cliente}
                  </p>
                </div>
              )}

              <p className="text-xs text-muted-foreground">
                {q.completed
                  ? "Cuestionario marcado como completado por el cliente."
                  : "Borrador en curso (el cliente aún no lo ha marcado como completado)."}{" "}
                Última actualización: {fmtFecha(q.updated_at)}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Decisiones del cliente sobre los borradores ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" aria-hidden />
            Aprobaciones y comentarios del cliente
            {pending > 0 && (
              <span
                className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900"
                data-testid="continuidad-pending-comments"
              >
                {pending} {pending === 1 ? "cambio pedido" : "cambios pedidos"}
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {approvals.length === 0 ? (
            <p className="text-muted-foreground">
              Sin decisiones del cliente todavía. Cuando apruebe o pida cambios
              en un borrador BIA/DRP, aparecerá aquí.
            </p>
          ) : (
            <ul className="space-y-2">
              {approvals.map((a) => (
                <li
                  key={a.id}
                  className="flex items-start gap-2 border-t py-2 first:border-t-0"
                >
                  {a.action === "comment" ? (
                    <MessageSquareWarning
                      className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
                      aria-hidden
                    />
                  ) : (
                    <CheckCircle2
                      className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                      aria-hidden
                    />
                  )}
                  <div className="min-w-0">
                    <span className="font-medium uppercase">
                      {a.artifact_type}
                    </span>{" "}
                    · {labelAction(a.action)}{" "}
                    <span className="text-muted-foreground">
                      ({fmtFecha(a.created_at)})
                    </span>
                    {a.comment_text && (
                      <p className="text-muted-foreground">“{a.comment_text}”</p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* ── Notificar al cliente: borrador listo ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" aria-hidden />
            Avisar al cliente: borrador listo
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            Cuando dejes preparado un borrador (BIA o Plan de Continuidad / DRP),
            avisa al cliente. Su portal se actualiza al instante y le invita a
            revisarlo y aprobarlo.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="contin-artifact" className="text-muted-foreground">
              Tipo de borrador:
            </label>
            <select
              id="contin-artifact"
              value={artifactType}
              onChange={(e) =>
                setArtifactType(e.target.value === "drp" ? "drp" : "bia")
              }
              className="rounded-md border border-input bg-background px-2 py-1"
              data-testid="continuidad-artifact-select"
            >
              <option value="bia">BIA (análisis de impacto)</option>
              <option value="drp">DRP (plan de continuidad)</option>
            </select>
            <Button
              onClick={() => notify.mutate()}
              disabled={notify.isPending}
              data-testid="continuidad-notify-draft-ready"
            >
              {notify.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Bell className="mr-2 h-4 w-4" />
              )}
              Avisar al cliente
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/40 p-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  );
}

function fmtHoras(h?: number | null): string {
  return h === null || h === undefined ? "—" : `${h} h`;
}

function fmtFecha(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function labelAction(action: string): string {
  if (action === "approved") return "aprobó el borrador";
  if (action === "rejected") return "rechazó el borrador";
  if (action === "comment") return "pidió cambios";
  return action;
}
