"use client";

/**
 * SubcontractsPanel · FASE C Phase C v3.12.
 *
 * Panel admin project-scoped que enumera adendas (sub-contratos E-604)
 * auto-generadas por workflow hito completion · cascade materialidad M28 ·
 * trigger manual admin · y manual legacy pre-FASE C.
 *
 * Surfacing per addendum:
 *   - Codigo + provider_id + normativas (ENS/RGPD/NIS2/DORA)
 *   - Estado firmas cliente/proveedor + fechas
 *   - Audit trail: last_trigger badge + triggers_history expandable
 *
 * CTAs:
 *   - "Recheck adendas" admin manual trigger -> POST /providers/adenda/check
 *   - Per addendum link a detail (TBD frontend) o download via providers/{id}
 *
 * Reuse patron: SubTabLink + Card + Badge + Skeleton + EmptyState
 * (ContractsList 1.D.D.A precedente).
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  History,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ADENDA_TRIGGER_LABELS,
  ADENDA_TRIGGER_VARIANTS,
  type AdendaSummary,
  type AdendaTrigger,
  providersAdendasApi,
} from "@/lib/api/providers-adendas";

interface SubcontractsPanelProps {
  projectId: string;
}

const NORMATIVA_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  ENS: "default",
  RGPD: "secondary",
  NIS2: "secondary",
  DORA: "outline",
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

function AdendaRow({ adenda }: { adenda: AdendaSummary }) {
  const [expanded, setExpanded] = useState(false);
  const trigger = adenda.audit_trail.last_trigger as AdendaTrigger;
  const triggerVariant = ADENDA_TRIGGER_VARIANTS[trigger] ?? "outline";
  const history = adenda.audit_trail.triggers_history ?? [];

  return (
    <div
      className="rounded-lg border border-border bg-card"
      data-testid="adenda-row"
      data-adenda-code={adenda.addendum_code}
    >
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <code className="font-mono text-sm font-medium">
              {adenda.addendum_code}
            </code>
            <Badge variant={triggerVariant} data-testid="trigger-badge">
              {ADENDA_TRIGGER_LABELS[trigger]}
            </Badge>
            {adenda.firmado_cliente && (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="h-3 w-3" /> Firmado cliente
              </Badge>
            )}
            {adenda.firmado_proveedor && (
              <Badge variant="secondary" className="gap-1">
                <CheckCircle2 className="h-3 w-3" /> Firmado proveedor
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {adenda.normativas_cubiertas.map((n) => (
              <Badge
                key={n}
                variant={NORMATIVA_VARIANT[n] ?? "outline"}
                className="text-xs"
              >
                {n}
              </Badge>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground pt-1">
            <div>
              <span className="font-medium">Generado:</span>{" "}
              {formatDate(adenda.created_at)}
            </div>
            <div>
              <span className="font-medium">Vigor:</span>{" "}
              {formatDate(adenda.fecha_vigor)}
            </div>
            <div>
              <span className="font-medium">Vencimiento:</span>{" "}
              {formatDate(adenda.vencimiento)}
            </div>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded((v) => !v)}
          aria-label="Mostrar trazabilidad"
          data-testid="audit-trail-toggle"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <History className="h-4 w-4 ml-1" />
        </Button>
      </div>

      {expanded && (
        <div
          className="border-t border-border bg-muted/40 p-4"
          data-testid="audit-trail-history"
        >
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Trazabilidad ENAC ({history.length}{" "}
            {history.length === 1 ? "evento" : "eventos"})
          </h4>
          {history.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">
              Sin trazabilidad event-driven · adenda legacy pre-FASE C o
              generada por endpoint manual antiguo.
            </p>
          ) : (
            <ol className="space-y-2 text-xs">
              {history.map((entry, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2"
                  data-testid="audit-trail-entry"
                >
                  <span className="font-mono text-muted-foreground">
                    {idx + 1}.
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant={
                          ADENDA_TRIGGER_VARIANTS[
                            entry.trigger as AdendaTrigger
                          ] ?? "outline"
                        }
                        className="text-[10px]"
                      >
                        {ADENDA_TRIGGER_LABELS[
                          entry.trigger as AdendaTrigger
                        ] ?? entry.trigger}
                      </Badge>
                      <span className="text-muted-foreground">
                        {formatDate(entry.auto_generated_at)}
                      </span>
                    </div>
                    {entry.completed_template_id && (
                      <div className="text-muted-foreground mt-0.5">
                        Hito: <code>{entry.completed_template_id}</code>
                      </div>
                    )}
                    {entry.materiality_level && (
                      <div className="text-muted-foreground mt-0.5">
                        Materialidad: <strong>{entry.materiality_level}</strong>
                        {entry.materiality_flags_triggered && (
                          <span>
                            {" · "}
                            {entry.materiality_flags_triggered.join(" + ")}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

export function SubcontractsPanel({ projectId }: SubcontractsPanelProps) {
  const queryClient = useQueryClient();

  const adendasQuery = useQuery({
    queryKey: ["m14", "providers", projectId, "adendas"],
    queryFn: () => providersAdendasApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const checkMutation = useMutation({
    mutationFn: () => providersAdendasApi.triggerCheck(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["m14", "providers", projectId, "adendas"],
      });
    },
  });

  const adendas = useMemo(
    () => adendasQuery.data?.adendas ?? [],
    [adendasQuery.data],
  );

  const counts = useMemo(() => {
    const map = new Map<AdendaTrigger | "total", number>();
    map.set("total", adendas.length);
    for (const a of adendas) {
      const t = a.audit_trail.last_trigger;
      map.set(t, (map.get(t) ?? 0) + 1);
    }
    return map;
  }, [adendas]);

  return (
    <Card data-testid="subcontracts-panel">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <ClipboardCheck className="h-5 w-5" />
            Sub-contratos · Adendas E-604
          </CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Adendas generadas automáticamente cuando workflow steps de
            proveedores completan · o cuando cambios M28 alcanzan materialidad
            MATERIAL con flags overlay/renewal. Marcos puede re-evaluar
            manualmente cuando detecta drift.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => checkMutation.mutate()}
          disabled={checkMutation.isPending}
          data-testid="trigger-recheck"
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${
              checkMutation.isPending ? "animate-spin" : ""
            }`}
          />
          Re-evaluar adendas
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Counts summary */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <Badge variant="outline">
            Total: <strong className="ml-1">{counts.get("total") ?? 0}</strong>
          </Badge>
          {(
            [
              "workflow_step_completed",
              "materiality_material_cascade",
              "admin_manual",
              "manual",
            ] as AdendaTrigger[]
          ).map((t) =>
            (counts.get(t) ?? 0) > 0 ? (
              <Badge
                key={t}
                variant={ADENDA_TRIGGER_VARIANTS[t]}
                className="gap-1"
              >
                {ADENDA_TRIGGER_LABELS[t]}: {counts.get(t) ?? 0}
              </Badge>
            ) : null,
          )}
        </div>

        {checkMutation.isError && (
          <Alert variant="danger">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Error re-evaluación</AlertTitle>
            <AlertDescription>
              {(checkMutation.error as Error)?.message ??
                "Error desconocido durante check."}
            </AlertDescription>
          </Alert>
        )}

        {checkMutation.isSuccess && checkMutation.data && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>Re-evaluación completada</AlertTitle>
            <AlertDescription>
              {checkMutation.data.adendas_processed} adenda(s) procesadas con
              marker <code>{checkMutation.data.trigger_template_id}</code>.
            </AlertDescription>
          </Alert>
        )}

        {/* List */}
        {adendasQuery.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : adendasQuery.isError ? (
          <Alert variant="danger">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Error cargando adendas</AlertTitle>
            <AlertDescription>
              {(adendasQuery.error as Error)?.message ?? "Error desconocido."}
            </AlertDescription>
          </Alert>
        ) : adendas.length === 0 ? (
          <EmptyState
            icon={<ClipboardCheck className="h-12 w-12" />}
            title="Sin adendas todavía"
            description="Aparecerán aquí cuando se autogeneren por workflow steps de proveedores o cambios M28 MATERIAL · o cuando uses 'Re-evaluar adendas'."
          />
        ) : (
          <div className="space-y-3" data-testid="adendas-list">
            {adendas.map((a) => (
              <AdendaRow key={a.addendum_id} adenda={a} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
