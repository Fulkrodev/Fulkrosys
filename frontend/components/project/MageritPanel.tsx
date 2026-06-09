"use client";

import {
  AlertCircle,
  Calculator,
  Cloud,
  CloudOff,
  Database,
  FileSpreadsheet,
  Layers,
  Loader2,
  Lock,
  PlayCircle,
  ShieldAlert,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { InfoTag } from "@/components/ui/info-tag";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useCalculateEffectiveRisk,
  useCalculateIntrinsicRisk,
  useCalculateResidualRisk,
  useCreateAnalysis,
  useFreezeAnalysis,
  useGenerateTreatmentPlan,
  useMageritReport,
  useMageritSignatureStatus,
} from "@/hooks/useMagerit";
import {
  type AnalysisOut,
  type AssetOut,
  type RiskCalculationOut,
  type TreatmentActionOut,
  downloadAssetInventoryUrl,
  downloadDependencyMapUrl,
  downloadExecutiveSummaryUrl,
  downloadRiskCalculationsUrl,
  downloadSafeguardDeploymentUrl,
  downloadThreatAssessmentUrl,
  downloadTreatmentPlanUrl,
  exportAnalysisXmlUrl,
  exportAnalysisMgrUrl,
  getReportDocxUrl,
  getReportPdfUrl,
} from "@/lib/api/magerit";
import { useEnrichedMageritInventory } from "@/hooks/useCloudConnectorsAdmin";
import { cn } from "@/lib/utils";

// ===================================================================
// Helpers
// ===================================================================

const RISK_TONE: Record<string, string> = {
  MA: "bg-fulkro-danger/10 text-fulkro-danger border-fulkro-danger/30",
  A: "bg-fulkro-warning/10 text-fulkro-warning border-fulkro-warning/30",
  M: "bg-fulkro-primary-700/10 text-fulkro-primary-700 border-fulkro-primary-700/30",
  B: "bg-fulkro-success/10 text-fulkro-success border-fulkro-success/30",
  MB: "bg-fulkro-success/10 text-fulkro-success border-fulkro-success/30",
};

const RISK_LABEL: Record<string, string> = {
  MA: "Muy alto",
  A: "Alto",
  M: "Medio",
  B: "Bajo",
  MB: "Muy bajo",
};

const TREATMENT_LABEL: Record<string, string> = {
  mitigar: "Mitigar",
  transferir: "Transferir",
  aceptar: "Aceptar",
  eliminar: "Eliminar",
};

function RiskPill({ level }: { level: string | null | undefined }) {
  if (!level) {
    return (
      <span className="inline-flex items-center rounded-full border border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] px-2.5 py-0.5 text-xs font-semibold text-[color:var(--fulkro-body)]">
        n/d
      </span>
    );
  }
  const tone = RISK_TONE[level] ?? RISK_TONE.M;
  const label = RISK_LABEL[level] ?? level;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        tone,
      )}
    >
      {label}
    </span>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-5">
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
          style={{
            backgroundColor: "var(--fulkro-surface-glass-strong)",
            color: "var(--fulkro-title)",
          }}
        >
          <Icon size={22} strokeWidth={2.2} />
        </div>
        <div className="flex flex-col">
          <span className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            {label}
          </span>
          <span className="text-2xl font-bold text-[color:var(--fulkro-title)]">
            {value}
          </span>
          {hint && (
            <span className="text-xs text-[color:var(--fulkro-body)]">
              {hint}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ===================================================================
// Tabs - Sub-views (inline pequeñas, NO sub-componentes)
// ===================================================================

function AssetsTab({
  assets,
  projectId,
  analysisId,
}: {
  assets: AssetOut[];
  projectId: string;
  analysisId: string | null;
}) {
  const [onlyCloudVerified, setOnlyCloudVerified] = React.useState(false);
  const { data: enrichedView } = useEnrichedMageritInventory(
    projectId,
    analysisId ?? undefined,
  );

  // Build asset_id → enriched map (cloud_verified · provider · detected_at)
  const enrichedById = React.useMemo(() => {
    const m = new Map<
      string,
      {
        cloud_verified: boolean;
        provider: string | null;
        detected_at: string | null;
      }
    >();
    for (const a of enrichedView?.assets ?? []) {
      m.set(a.asset_id, {
        cloud_verified: a.cloud_verified,
        provider: a.cloud_provider,
        detected_at: a.cloud_detected_at,
      });
    }
    return m;
  }, [enrichedView]);

  const counts = enrichedView?.counts;
  const verifiedCount = counts?.cloud_verified ?? 0;
  const totalCount = counts?.total ?? assets.length;

  const filteredAssets = React.useMemo(() => {
    if (!onlyCloudVerified) return assets;
    return assets.filter((a) => enrichedById.get(a.id)?.cloud_verified);
  }, [assets, onlyCloudVerified, enrichedById]);

  if (!assets.length) {
    return (
      <EmptyState
        icon={<Database size={32} strokeWidth={2.2} />}
        title="Sin activos cargados"
        description="Importa el inventario de activos para iniciar el análisis MAGERIT."
      />
    );
  }
  return (
    <div className="space-y-4">
      {/* Stats card · cloud verification summary */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] p-3"
        data-testid="magerit-cloud-stats"
      >
        <div className="flex items-center gap-2 text-sm">
          <Cloud size={18} className="text-fulkro-primary-600" />
          <span className="font-semibold">
            {verifiedCount}/{totalCount}
          </span>
          <span className="text-[color:var(--fulkro-subtitle)]">
            activos cloud-verified (op.exp.1)
          </span>
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={onlyCloudVerified}
            onChange={(e) => setOnlyCloudVerified(e.target.checked)}
            className="size-3.5 cursor-pointer"
            data-testid="magerit-filter-cloud-verified"
          />
          <span>Solo cloud-verified</span>
        </label>
      </div>

      <Card>
        <CardContent className="overflow-x-auto p-0">
          <table className="min-w-full text-sm" data-testid="magerit-assets-table">
            <thead>
              <tr
                className="border-b text-left"
                style={{ borderColor: "var(--fulkro-surface-glass-border)" }}
              >
                <th className="px-4 py-3 font-bold">Código</th>
                <th className="px-4 py-3 font-bold">Nombre</th>
                <th className="px-4 py-3 font-bold">Tipo</th>
                <th className="px-4 py-3 text-center font-bold">Cloud</th>
                <th className="px-4 py-3 text-center font-bold">D</th>
                <th className="px-4 py-3 text-center font-bold">I</th>
                <th className="px-4 py-3 text-center font-bold">C</th>
                <th className="px-4 py-3 text-center font-bold">A</th>
                <th className="px-4 py-3 text-center font-bold">T</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssets.map((asset) => {
                const enrich = enrichedById.get(asset.id);
                const verified = enrich?.cloud_verified ?? false;
                const tooltip = verified
                  ? `Detected in ${enrich?.provider ?? "cloud"}${
                      enrich?.detected_at
                        ? ` · ${new Date(enrich.detected_at).toLocaleDateString("es-ES")}`
                        : ""
                    }`
                  : "Sin verificación cloud · declarado manualmente";
                return (
                  <tr
                    key={asset.id}
                    className="border-b last:border-0"
                    style={{ borderColor: "var(--fulkro-surface-glass-border)" }}
                    data-testid={
                      verified ? "magerit-row-cloud-verified" : "magerit-row-manual"
                    }
                  >
                    <td className="px-4 py-3 font-mono text-xs">{asset.code}</td>
                    <td className="px-4 py-3 font-semibold">{asset.name}</td>
                    <td className="px-4 py-3 font-mono text-xs uppercase text-[color:var(--fulkro-subtitle)]">
                      {asset.asset_type_code}
                    </td>
                    <td className="px-4 py-3 text-center" title={tooltip}>
                      {verified ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-fulkro-success/30 bg-fulkro-success/10 px-2 py-0.5 text-xs text-fulkro-success">
                          <Cloud size={12} strokeWidth={2.2} />
                          {enrich?.provider ?? "cloud"}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-[color:var(--fulkro-subtitle)]">
                          <CloudOff size={12} strokeWidth={2.2} />
                          —
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {asset.value_d ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {asset.value_i ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {asset.value_c ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {asset.value_a ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {asset.value_t ?? "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

function RisksTab({
  risks,
  assets,
}: {
  risks: RiskCalculationOut[];
  assets: AssetOut[];
}) {
  const assetByID = React.useMemo(() => {
    const m = new Map<string, AssetOut>();
    assets.forEach((a) => m.set(a.id, a));
    return m;
  }, [assets]);

  if (!risks.length) {
    return (
      <EmptyState
        icon={<Calculator size={32} strokeWidth={2.2} />}
        title="Sin cálculos de riesgo"
        description="Lanza primero el cálculo intrínseco, efectivo y residual."
      />
    );
  }

  return (
    <Card>
      <CardContent className="overflow-x-auto p-0">
        <table className="min-w-full text-sm">
          <thead>
            <tr
              className="border-b text-left"
              style={{ borderColor: "var(--fulkro-surface-glass-border)" }}
            >
              <th className="px-4 py-3 font-bold">Activo</th>
              <th className="px-4 py-3 font-bold">Amenaza</th>
              <th className="px-4 py-3 font-bold">Dim</th>
              <th className="px-4 py-3 text-right font-bold">R. intrínseco</th>
              <th className="px-4 py-3 text-right font-bold">R. efectivo</th>
              <th className="px-4 py-3 text-right font-bold">R. residual</th>
              <th className="px-4 py-3 text-center font-bold">Nivel</th>
            </tr>
          </thead>
          <tbody>
            {risks.map((risk, idx) => {
              const asset = assetByID.get(risk.asset_id);
              return (
                <tr
                  key={`${risk.asset_id}-${risk.threat_code}-${risk.dimension}-${idx}`}
                  className="border-b last:border-0"
                  style={{
                    borderColor: "var(--fulkro-surface-glass-border)",
                  }}
                >
                  <td className="px-4 py-3 font-semibold">
                    {asset ? asset.name : risk.asset_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {risk.threat_code}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs uppercase">
                    {risk.dimension}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {risk.risk_intrinsic_repercuted?.toFixed(2) ??
                      risk.risk_intrinsic_accumulated?.toFixed(2) ??
                      "-"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {risk.risk_effective?.toFixed(2) ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {risk.risk_residual?.toFixed(2) ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <RiskPill level={risk.risk_level} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function TreatmentTab({
  actions,
  assets,
}: {
  actions: TreatmentActionOut[];
  assets: AssetOut[];
}) {
  const assetByID = React.useMemo(() => {
    const m = new Map<string, AssetOut>();
    assets.forEach((a) => m.set(a.id, a));
    return m;
  }, [assets]);

  if (!actions.length) {
    return (
      <EmptyState
        icon={<Target size={32} strokeWidth={2.2} />}
        title="Sin plan de tratamiento"
        description="Genera el plan de tratamiento tras calcular los riesgos."
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {actions.map((act) => {
        const asset = assetByID.get(act.asset_id);
        return (
          <Card key={act.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <CardTitle className="text-base">
                  {asset ? asset.name : act.asset_id.slice(0, 8)} ·{" "}
                  <span className="font-mono text-sm text-[color:var(--fulkro-subtitle)]">
                    {act.threat_code}
                  </span>
                </CardTitle>
                <RiskPill level={act.current_risk_level} />
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Estrategia
                </span>
                <span className="rounded-full bg-fulkro-primary-700/10 px-2.5 py-0.5 text-xs font-semibold text-fulkro-primary-700">
                  {TREATMENT_LABEL[act.treatment] ?? act.treatment}
                </span>
              </div>
              {act.action_description && (
                <p className="text-[color:var(--fulkro-body)]">
                  {act.action_description}
                </p>
              )}
              {act.proposed_safeguards && act.proposed_safeguards.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {act.proposed_safeguards.map((sg) => (
                    <span
                      key={sg}
                      className="rounded-md bg-[color:var(--fulkro-surface-glass-strong)] px-2 py-0.5 font-mono text-xs"
                    >
                      {sg}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center justify-between text-xs text-[color:var(--fulkro-subtitle)]">
                <span>
                  Objetivo: <RiskPill level={act.target_risk_level} />
                </span>
                {act.deadline && (
                  <span className="font-mono">{act.deadline}</span>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function ReportsTab({ analysisId }: { analysisId: string }) {
  const ExportRow = ({
    href,
    label,
    icon: Icon,
  }: {
    href: string;
    label: string;
    icon: LucideIcon;
  }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors hover:bg-[color:var(--fulkro-surface-glass-strong)]"
      style={{
        borderColor: "var(--fulkro-surface-glass-border)",
        color: "var(--fulkro-title)",
      }}
    >
      <Icon size={18} strokeWidth={2.2} />
      <span className="text-sm font-semibold">{label}</span>
    </a>
  );

  return (
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
      <ExportRow
        href={getReportPdfUrl(analysisId)}
        label="Informe consolidado (PDF)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={getReportDocxUrl(analysisId)}
        label="Informe consolidado (DOCX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={exportAnalysisXmlUrl(analysisId)}
        label="Export XML estructurado"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={exportAnalysisMgrUrl(analysisId)}
        label="Export PILAR/MGR"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadAssetInventoryUrl(analysisId)}
        label="Inventario activos (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadDependencyMapUrl(analysisId)}
        label="Dependencias (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadThreatAssessmentUrl(analysisId)}
        label="Amenazas (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadSafeguardDeploymentUrl(analysisId)}
        label="Salvaguardas (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadRiskCalculationsUrl(analysisId)}
        label="Cálculos de riesgo (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadTreatmentPlanUrl(analysisId)}
        label="Plan de tratamiento (XLSX)"
        icon={FileSpreadsheet}
      />
      <ExportRow
        href={downloadExecutiveSummaryUrl(analysisId)}
        label="Resumen ejecutivo (XLSX)"
        icon={FileSpreadsheet}
      />
    </div>
  );
}

// ===================================================================
// Main panel
// ===================================================================

export function MageritPanel({ projectId }: { projectId: string }) {
  const [analysisId, setAnalysisId] = React.useState<string | null>(null);

  const createMut = useCreateAnalysis(projectId);
  const reportQ = useMageritReport(analysisId ?? undefined);
  const sigStatusQ = useMageritSignatureStatus(analysisId ?? undefined);

  const calcIntrinsicMut = useCalculateIntrinsicRisk(analysisId ?? "");
  const calcEffectiveMut = useCalculateEffectiveRisk(analysisId ?? "");
  const calcResidualMut = useCalculateResidualRisk(analysisId ?? "");
  const treatmentPlanMut = useGenerateTreatmentPlan(analysisId ?? "");
  const freezeMut = useFreezeAnalysis(analysisId ?? "");

  const handleCreateAnalysis = async () => {
    try {
      const analysis = (await createMut.mutateAsync({
        name: `MAGERIT v3 - ${new Date().toLocaleDateString("es-ES")}`,
        calculation_mode: "qualitative",
      })) as AnalysisOut;
      setAnalysisId(analysis.id);
      toast.success("Análisis MAGERIT creado");
    } catch {
      toast.error("No se pudo crear el análisis");
    }
  };

  // ===== Loading: cuando no hay analysisId todavía
  if (!analysisId) {
    return (
      <div className="flex flex-col gap-6">
        <header className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)]">
              Análisis de riesgos MAGERIT v3
            </h1>
            <p className="mt-1 text-sm text-[color:var(--fulkro-body)]">
              Activos · dependencias · amenazas · salvaguardas · riesgos ·
              tratamiento.
            </p>
          </div>
        </header>

        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
            <ShieldAlert
              size={32}
              strokeWidth={2.2}
              className="text-[color:var(--fulkro-subtitle)]"
            />
            <div>
              <h2 className="text-lg font-bold text-[color:var(--fulkro-title)]">
                No hay análisis MAGERIT activo
              </h2>
              <p className="mt-1 text-sm text-[color:var(--fulkro-body)]">
                Inicia un nuevo análisis para cargar el inventario de activos.
              </p>
            </div>
            <Button
              onClick={handleCreateAnalysis}
              disabled={createMut.isPending}
            >
              {createMut.isPending ? (
                <>
                  <Loader2 size={16} strokeWidth={2.4} className="animate-spin" />
                  Creando...
                </>
              ) : (
                <>
                  <PlayCircle size={16} strokeWidth={2.4} />
                  Crear análisis MAGERIT
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ===== Loading: análisis creado, esperando primer reporte
  if (reportQ.isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-12 w-1/2" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  // ===== Error de fetch (404 inicial es esperable)
  if (reportQ.isError) {
    return (
      <Alert>
        <AlertCircle size={18} strokeWidth={2.4} />
        <AlertTitle>El análisis aún no tiene datos</AlertTitle>
        <AlertDescription>
          Importa el inventario de activos para generar la primera versión
          del reporte MAGERIT.
        </AlertDescription>
      </Alert>
    );
  }

  const report = reportQ.data;
  const assets = report?.assets ?? [];
  const risks = report?.risk_calculations ?? [];
  const treatments = report?.treatment_actions ?? [];

  const summary = report?.summary ?? {};
  const totalAssets = (summary.total_assets as number) ?? assets.length;
  const totalRisks = (summary.total_risks as number) ?? risks.length;
  const highRisks =
    (summary.high_risk_count as number) ??
    risks.filter((r) => r.risk_level === "A" || r.risk_level === "MA").length;

  const isFrozen = sigStatusQ.data?.is_frozen ?? false;

  return (
    <div className="flex flex-col gap-7">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)]">
            Análisis de riesgos <InfoTag term="MAGERIT" display="MAGERIT" /> v3
          </h1>
          <p className="mt-1 text-sm text-[color:var(--fulkro-body)]">
            {report?.analysis.name} · v{report?.analysis.version} ·{" "}
            <span className="font-mono uppercase">
              {report?.analysis.calculation_mode}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            onClick={() =>
              calcIntrinsicMut
                .mutateAsync()
                .then(() => toast.success("Riesgo intrínseco calculado"))
                .catch(() => toast.error("Error en cálculo intrínseco"))
            }
            disabled={calcIntrinsicMut.isPending || isFrozen}
          >
            <Calculator size={16} strokeWidth={2.4} />
            Calcular intrínseco <TooltipENS term="riesgo_intrinseco" />
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              calcEffectiveMut
                .mutateAsync()
                .then(() => toast.success("Riesgo efectivo calculado"))
                .catch(() => toast.error("Error en cálculo efectivo"))
            }
            disabled={calcEffectiveMut.isPending || isFrozen}
          >
            <Calculator size={16} strokeWidth={2.4} />
            Calcular efectivo <TooltipENS term="riesgo_efectivo" />
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              calcResidualMut
                .mutateAsync()
                .then(() => toast.success("Riesgo residual calculado"))
                .catch(() => toast.error("Error en cálculo residual"))
            }
            disabled={calcResidualMut.isPending || isFrozen}
          >
            <Calculator size={16} strokeWidth={2.4} />
            Calcular residual <TooltipENS term="riesgo_residual" />
          </Button>
          <Button
            onClick={() =>
              treatmentPlanMut
                .mutateAsync({})
                .then(() => toast.success("Plan de tratamiento generado"))
                .catch(() => toast.error("Error generando plan"))
            }
            disabled={treatmentPlanMut.isPending || isFrozen}
          >
            <Sparkles size={16} strokeWidth={2.4} />
            Generar plan
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              freezeMut
                .mutateAsync()
                .then(() => toast.success("Análisis congelado"))
                .catch(() => toast.error("Error al congelar"))
            }
            disabled={freezeMut.isPending || isFrozen}
          >
            <Lock size={16} strokeWidth={2.4} />
            {isFrozen ? "Congelado" : "Congelar"}
          </Button>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          icon={Database}
          label="Activos"
          value={totalAssets}
          hint="Inventario cargado"
        />
        <StatCard
          icon={Layers}
          label="Cálculos"
          value={totalRisks}
          hint="Activo × amenaza × dimensión"
        />
        <StatCard
          icon={ShieldAlert}
          label="Riesgos altos"
          value={highRisks}
          hint="Nivel A o MA"
        />
      </div>

      <Tabs defaultValue="assets" className="flex flex-col gap-5">
        <TabsList
          style={{
            backgroundColor: "var(--fulkro-surface-glass)",
            borderColor: "var(--fulkro-surface-glass-border)",
          }}
          className="w-full justify-start gap-1 overflow-x-auto rounded-xl border p-1.5"
        >
          <TabsTrigger value="assets" className="gap-2 px-4 py-2">
            <Database size={15} strokeWidth={2.2} />
            Activos
          </TabsTrigger>
          <TabsTrigger value="risks" className="gap-2 px-4 py-2">
            <Calculator size={15} strokeWidth={2.2} />
            Riesgos
          </TabsTrigger>
          <TabsTrigger value="treatments" className="gap-2 px-4 py-2">
            <Target size={15} strokeWidth={2.2} />
            Tratamiento
          </TabsTrigger>
          <TabsTrigger value="reports" className="gap-2 px-4 py-2">
            <FileSpreadsheet size={15} strokeWidth={2.2} />
            Informes
          </TabsTrigger>
        </TabsList>

        <TabsContent value="assets">
          <AssetsTab
            assets={assets}
            projectId={projectId}
            analysisId={analysisId}
          />
        </TabsContent>
        <TabsContent value="risks">
          <RisksTab risks={risks} assets={assets} />
        </TabsContent>
        <TabsContent value="treatments">
          <TreatmentTab actions={treatments} assets={assets} />
        </TabsContent>
        <TabsContent value="reports">
          <ReportsTab analysisId={analysisId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
