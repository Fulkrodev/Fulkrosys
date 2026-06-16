"use client";

/**
 * CloudConnectorsAdminPanel · sub-atom 1.D.X.J v3.12.
 *
 * Admin project-scoped UI · 4 Tabs (Conectores · Recursos · Gaps · Monitoring).
 *
 * Reuse 100% backend endpoints existing (B + H sub-fases).
 * R23 sostener firmísimo · project-scoped exclusive.
 */
import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Cloud,
  Database,
  HelpCircle,
  Loader2,
  Play,
  RefreshCw,
  Trash2,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  GAP_TYPE_LABEL,
  SEVERITY_LABEL,
  SEVERITY_VARIANT,
  STATUS_LABEL,
  type CloudConnectorAdmin,
  type CloudGap,
} from "@/lib/api/cloud-connectors-admin";
import {
  useAdminLatestDigest,
  useCloudConnectors,
  useCloudGaps,
  useCloudResources,
  useCloudSyncJobs,
  useProvidersCatalog,
  useResolveGap,
  useRevokeConnector,
  useRunDiagnosis,
  useTriggerDigest,
  useTriggerSync,
} from "@/hooks/useCloudConnectorsAdmin";

interface Props {
  projectId: string;
}

export function CloudConnectorsAdminPanel({ projectId }: Props) {
  const [selectedConnectorId, setSelectedConnectorId] = React.useState<
    string | null
  >(null);
  const [tab, setTab] = React.useState<
    "connectors" | "resources" | "gaps" | "monitoring"
  >("connectors");

  const connectorsQ = useCloudConnectors(projectId);
  const gapsQ = useCloudGaps(projectId);

  // Compute summary KPIs para hero
  const totalConnectors = connectorsQ.data?.total ?? 0;
  const totalResources = (connectorsQ.data?.items ?? []).reduce(
    (acc, c) => acc + c.last_sync_resources_count, 0,
  );
  const openGaps = gapsQ.data?.items.filter((g) => !g.resolved_at) ?? [];
  const criticalCount = openGaps.filter((g) => g.severity === "critical").length;
  const highCount = openGaps.filter((g) => g.severity === "high").length;

  return (
    <div className="space-y-4 p-4" data-testid="cloud-connectors-admin-panel">
      {/* Hero KPIs */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <KpiCard
          icon={<Cloud className="size-4" />}
          label="Conectores activos"
          value={String(totalConnectors)}
        />
        <KpiCard
          icon={<Database className="size-4" />}
          label="Recursos detectados"
          value={String(totalResources)}
        />
        <KpiCard
          icon={<AlertTriangle className="size-4 text-red-600" />}
          label="Gaps críticos"
          value={String(criticalCount)}
          highlight={criticalCount > 0 ? "danger" : "ok"}
        />
        <KpiCard
          icon={<AlertTriangle className="size-4 text-amber-600" />}
          label="Gaps altos"
          value={String(highCount)}
          highlight={highCount > 0 ? "warning" : "ok"}
        />
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="connectors" data-testid="tab-connectors">
            Conectores
          </TabsTrigger>
          <TabsTrigger value="resources" data-testid="tab-resources">
            Recursos detectados
          </TabsTrigger>
          <TabsTrigger value="gaps" data-testid="tab-gaps">
            Gaps detectados
          </TabsTrigger>
          <TabsTrigger value="monitoring" data-testid="tab-monitoring">
            Monitoring continuo
          </TabsTrigger>
        </TabsList>

        <TabsContent value="connectors" className="mt-4">
          <ConnectorsTab
            projectId={projectId}
            onSelectConnector={(id) => {
              setSelectedConnectorId(id);
              setTab("resources");
            }}
          />
        </TabsContent>
        <TabsContent value="resources" className="mt-4">
          <ResourcesTab
            projectId={projectId}
            connectors={connectorsQ.data?.items ?? []}
            selectedConnectorId={selectedConnectorId}
            onSelectConnector={setSelectedConnectorId}
          />
        </TabsContent>
        <TabsContent value="gaps" className="mt-4">
          <GapsTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="monitoring" className="mt-4">
          <MonitoringTab projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ============================================================
// Sub-componentes
// ============================================================

function KpiCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: "ok" | "warning" | "danger";
}) {
  const bg =
    highlight === "danger"
      ? "border-red-200 bg-red-50/40"
      : highlight === "warning"
      ? "border-amber-200 bg-amber-50/40"
      : "border-fulkro-ink-200";
  return (
    <Card className={bg}>
      <CardContent className="flex items-center gap-3 p-4">
        <span>{icon}</span>
        <div className="flex-1">
          <p className="text-xs text-fulkro-ink-500">{label}</p>
          <p className="text-lg font-semibold text-fulkro-ink-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ConnectorsTab({
  projectId,
  onSelectConnector,
}: {
  projectId: string;
  onSelectConnector: (id: string) => void;
}) {
  const connectorsQ = useCloudConnectors(projectId, true);
  const catalogQ = useProvidersCatalog();
  const triggerSync = useTriggerSync(projectId);
  const revoke = useRevokeConnector(projectId);

  const items = connectorsQ.data?.items ?? [];
  if (connectorsQ.isLoading) {
    return <LoadingState />;
  }
  if (connectorsQ.isError) {
    return <ErrorState />;
  }
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sin conectores configurados</CardTitle>
          <CardDescription>
            El cliente puede conectar sus sistemas desde el portal (sección
            Onboarding · primer paso). También puedes ayudar al cliente con
            setup desde aquí en MB siguientes.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const catalog = catalogQ.data ?? [];
  const labelFor = (provider: string) =>
    catalog.find((c) => c.provider === provider)?.display_name ?? provider;

  return (
    <div className="space-y-3" data-testid="connectors-list">
      {items.map((c: CloudConnectorAdmin) => (
        <Card key={c.id} data-testid={`connector-row-${c.provider}`}>
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold">{labelFor(c.provider)}</span>
                <Badge variant={c.status === "connected" ? "success" : "outline"}>
                  {STATUS_LABEL[c.status] ?? c.status}
                </Badge>
                {c.revoked_at && (
                  <Badge variant="outline">Revocado</Badge>
                )}
              </div>
              <p className="text-xs text-fulkro-ink-500">
                {c.last_sync_at
                  ? `Última sync · ${new Date(c.last_sync_at).toLocaleString()} · ${c.last_sync_resources_count} recursos`
                  : "Sin sync todavía"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onSelectConnector(c.id)}
                data-testid={`btn-view-resources-${c.provider}`}
              >
                Ver recursos
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={
                  triggerSync.isPending
                  || c.status === "revoked"
                  || c.status === "syncing"
                }
                onClick={() => triggerSync.mutate(c.id)}
                data-testid={`btn-sync-${c.provider}`}
              >
                {triggerSync.isPending ? (
                  <Loader2 className="mr-1 size-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="mr-1 size-3.5" />
                )}
                Forzar sync
              </Button>
              {c.status !== "revoked" && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => revoke.mutate(c.id)}
                  disabled={revoke.isPending}
                  data-testid={`btn-revoke-${c.provider}`}
                >
                  <Trash2 className="mr-1 size-3.5" />
                  Revocar
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ResourcesTab({
  projectId,
  connectors,
  selectedConnectorId,
  onSelectConnector,
}: {
  projectId: string;
  connectors: CloudConnectorAdmin[];
  selectedConnectorId: string | null;
  onSelectConnector: (id: string | null) => void;
}) {
  const resourcesQ = useCloudResources(projectId, selectedConnectorId);

  return (
    <div className="space-y-3" data-testid="resources-tab">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-fulkro-ink-500">Conector:</label>
        <select
          className="rounded-md border border-fulkro-ink-200 bg-white px-2 py-1 text-sm"
          value={selectedConnectorId ?? ""}
          onChange={(e) => onSelectConnector(e.target.value || null)}
          data-testid="resources-connector-select"
        >
          <option value="">— Selecciona —</option>
          {connectors.map((c) => (
            <option key={c.id} value={c.id}>
              {c.provider} ({c.last_sync_resources_count})
            </option>
          ))}
        </select>
      </div>

      {!selectedConnectorId ? (
        <Card>
          <CardContent className="p-4 text-sm text-fulkro-ink-500">
            Selecciona un conector para ver los recursos detectados.
          </CardContent>
        </Card>
      ) : resourcesQ.isLoading ? (
        <LoadingState />
      ) : resourcesQ.isError ? (
        <ErrorState />
      ) : (resourcesQ.data?.items.length ?? 0) === 0 ? (
        <Card>
          <CardContent className="p-4 text-sm text-fulkro-ink-500">
            Este conector no ha detectado recursos todavía. Lanza una sync.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table
              aria-label="Recursos cloud descubiertos"
              className="w-full text-sm"
              data-testid="resources-table"
            >
              <thead className="bg-fulkro-ink-50">
                <tr>
                  <th className="px-3 py-2 text-left">Tipo</th>
                  <th className="px-3 py-2 text-left">Nombre</th>
                  <th className="px-3 py-2 text-left">External ID</th>
                  <th className="px-3 py-2 text-left">Detectado</th>
                </tr>
              </thead>
              <tbody>
                {resourcesQ.data!.items.map((r) => (
                  <tr key={r.id} className="border-t border-fulkro-ink-100">
                    <td className="px-3 py-2">
                      <Badge variant="outline">{r.resource_type}</Badge>
                    </td>
                    <td className="px-3 py-2">{r.resource_name ?? "—"}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {r.resource_external_id}
                    </td>
                    <td className="px-3 py-2 text-xs text-fulkro-ink-500">
                      {new Date(r.detected_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function GapsTab({ projectId }: { projectId: string }) {
  const [severityFilter, setSeverityFilter] = React.useState<string[]>([]);
  const [includeResolved, setIncludeResolved] = React.useState(false);
  const gapsQ = useCloudGaps(projectId, {
    severities: severityFilter.length ? severityFilter : undefined,
    includeResolved,
  });
  const runDiag = useRunDiagnosis(projectId);
  const resolveGap = useResolveGap(projectId);

  const toggleSeverity = (s: string) =>
    setSeverityFilter((prev) =>
      prev.includes(s) ? prev.filter((p) => p !== s) : [...prev, s],
    );

  return (
    <div className="space-y-3" data-testid="gaps-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          {["critical", "high", "medium", "low"].map((sev) => (
            <Button
              key={sev}
              size="sm"
              variant={severityFilter.includes(sev) ? "primary" : "outline"}
              onClick={() => toggleSeverity(sev)}
              data-testid={`filter-severity-${sev}`}
            >
              {SEVERITY_LABEL[sev]}
            </Button>
          ))}
          <label className="ml-3 flex items-center gap-1 text-sm">
            <input
              type="checkbox"
              checked={includeResolved}
              onChange={(e) => setIncludeResolved(e.target.checked)}
              data-testid="toggle-include-resolved"
            />
            Incluir resueltos
          </label>
        </div>
        <Button
          size="sm"
          variant="primary"
          disabled={runDiag.isPending}
          onClick={() => runDiag.mutate()}
          data-testid="btn-run-diagnosis"
        >
          {runDiag.isPending ? (
            <Loader2 className="mr-1 size-3.5 animate-spin" />
          ) : (
            <Play className="mr-1 size-3.5" />
          )}
          Ejecutar diagnóstico
        </Button>
      </div>

      {runDiag.data && (
        <Card className="border-fulkro-primary-200 bg-fulkro-primary-50/40">
          <CardContent className="p-4 text-sm">
            <strong>Resultado diagnóstico:</strong>{" "}
            {runDiag.data.rules_evaluated} reglas evaluadas ·{" "}
            {runDiag.data.findings_emitted} hallazgos emitidos ·{" "}
            {runDiag.data.gaps_created} nuevos ·{" "}
            {runDiag.data.gaps_updated} actualizados ·{" "}
            {runDiag.data.gaps_resolved} auto-resueltos
            {runDiag.data.no_cloud_data && (
              <p className="mt-1 text-xs italic">
                Sin cloud data conectada · solo gaps documentales emitidos.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {gapsQ.isLoading ? (
        <LoadingState />
      ) : gapsQ.isError ? (
        <ErrorState />
      ) : (gapsQ.data?.items.length ?? 0) === 0 ? (
        <Card>
          <CardContent className="p-4 text-sm text-fulkro-ink-500">
            Sin gaps abiertos con los filtros actuales.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {gapsQ.data!.items.map((g) => (
            <GapCard
              key={g.id}
              gap={g}
              onResolve={() => resolveGap.mutate({ gapId: g.id })}
              resolving={resolveGap.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function GapCard({
  gap,
  onResolve,
  resolving,
}: {
  gap: CloudGap;
  onResolve: () => void;
  resolving: boolean;
}) {
  const isResolved = !!gap.resolved_at;
  return (
    <Card data-testid={`gap-card-${gap.ens_measure_code}`}>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge variant={SEVERITY_VARIANT[gap.severity] ?? "default"}>
                {SEVERITY_LABEL[gap.severity] ?? gap.severity}
              </Badge>
              <Badge variant="outline">{gap.ens_measure_code}</Badge>
              <Badge variant="outline">
                {GAP_TYPE_LABEL[gap.gap_type] ?? gap.gap_type}
              </Badge>
              {isResolved && (
                <Badge variant="success">
                  <CheckCircle2 className="mr-1 size-3" />
                  Resuelto
                </Badge>
              )}
            </div>
            <p className="text-sm font-semibold">{gap.title}</p>
            {gap.explanation_es && (
              <p className="text-xs text-fulkro-ink-700">{gap.explanation_es}</p>
            )}
            {gap.suggested_action && (
              <p className="text-xs italic text-fulkro-ink-500">
                Acción sugerida: {gap.suggested_action}
              </p>
            )}
          </div>
          {!isResolved && (
            <Button
              size="sm"
              variant="outline"
              onClick={onResolve}
              disabled={resolving}
              data-testid={`btn-resolve-${gap.ens_measure_code}`}
            >
              Marcar resuelto
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function MonitoringTab({ projectId }: { projectId: string }) {
  const latestQ = useAdminLatestDigest(projectId);
  const triggerDigest = useTriggerDigest(projectId);
  const [toast, setToast] = React.useState<{
    kind: "success" | "error"; msg: string;
  } | null>(null);

  async function handleTrigger() {
    setToast(null);
    try {
      const res = await triggerDigest.mutateAsync();
      setToast({
        kind: "success",
        msg: res.message || "Digest generado.",
      });
    } catch (err) {
      setToast({
        kind: "error",
        msg: err instanceof Error ? err.message : String(err),
      });
    }
  }

  if (latestQ.isLoading) {
    return <LoadingState />;
  }

  const snapshot = latestQ.data;

  return (
    <div className="space-y-3" data-testid="monitoring-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-fulkro-ink-900">
            Resumen mensual cliente
          </h3>
          <p className="text-xs text-fulkro-ink-500">
            Celery beat lo genera el día 1 de cada mes · puedes generar uno
            ahora para revisar antes con el cliente.
          </p>
        </div>
        <Button
          size="sm"
          variant="primary"
          disabled={triggerDigest.isPending}
          onClick={handleTrigger}
          data-testid="btn-generate-digest-now"
        >
          {triggerDigest.isPending ? (
            <Loader2 className="mr-1 size-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1 size-3.5" />
          )}
          Generar ahora
        </Button>
      </div>

      {toast && (
        <div
          className={`rounded-md border p-3 text-sm ${
            toast.kind === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
          role="status"
          data-testid={`digest-toast-${toast.kind}`}
        >
          {toast.msg}
        </div>
      )}

      {snapshot ? (
        <DigestSummaryCard snapshot={snapshot} />
      ) : (
        <Card data-testid="digest-empty-state">
          <CardContent className="p-6 text-center text-sm text-fulkro-ink-500">
            <p className="font-medium text-fulkro-ink-700">
              Sin digest aún
            </p>
            <p className="mt-1 text-xs">
              Genera el primero para arrancar el seguimiento mensual.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DigestSummaryCard({
  snapshot,
}: {
  snapshot: import("@/lib/api/cloud-connectors-admin").DigestSnapshot;
}) {
  const triggeredLabel =
    snapshot.triggered_by === "admin_manual"
      ? "Manual (admin)"
      : "Automático (mensual)";
  const generatedAt = new Date(snapshot.generated_at).toLocaleString();
  const scoreVariant: "success" | "warning" | "danger" =
    snapshot.compliance_score >= 85
      ? "success"
      : snapshot.compliance_score >= 60
      ? "warning"
      : "danger";

  return (
    <Card data-testid="digest-summary-card">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">Último resumen</CardTitle>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline">{triggeredLabel}</Badge>
            <span className="text-fulkro-ink-500">{generatedAt}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
            <p className="text-xs text-fulkro-ink-500">Compliance score</p>
            <p className="mt-1 text-2xl font-semibold">
              <Badge variant={scoreVariant}>{snapshot.compliance_score}</Badge>
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
            <p className="text-xs text-fulkro-ink-500">Gaps abiertos</p>
            <p className="mt-1 text-2xl font-semibold text-fulkro-ink-900">
              {snapshot.open_gaps_total}
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
            <p className="text-xs text-fulkro-ink-500">Por severidad</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(["critical", "high", "medium", "low"] as const).map((sev) => {
                const count = snapshot.open_gaps_by_severity[sev] ?? 0;
                if (count === 0) return null;
                return (
                  <Badge key={sev} variant={SEVERITY_VARIANT[sev] ?? "default"}>
                    {SEVERITY_LABEL[sev]}: {count}
                  </Badge>
                );
              })}
              {snapshot.open_gaps_total === 0 && (
                <span className="text-xs italic text-fulkro-ink-500">
                  Sin gaps abiertos
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div
      className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500"
      data-testid="loading-state"
    >
      <Loader2 className="size-4 animate-spin" />
      Cargando…
    </div>
  );
}

function ErrorState() {
  return (
    <div
      className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
      role="alert"
      data-testid="error-state"
    >
      Error al cargar datos. Reintenta en unos segundos.
    </div>
  );
}
