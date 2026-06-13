"use client";

/**
 * DdaEvidenceGapsView · CLUSTER 3 Phase C3.3 auditor portal heatmap.
 *
 * Display:
 * - Header con coverage % + counts totals
 * - Severity summary cards (critical · high · medium · recoverable)
 * - Heatmap grid · 73 medidas grouped by family (org · op · mp)
 * - Per medida cell con color + tooltip + click → drawer
 * - Drawer drill-down · DdA + evidence list + gap_reason + actions
 * - Filters: status + family + search
 */
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Loader2,
  Search,
  X,
} from "lucide-react";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ClarificationButton } from "@/components/auditor-portal/clarifications/ClarificationButton";
import {
  type DdaEvidenceGapMatrix,
  type GapStatus,
  type MedidaGapRow,
  FAMILY_LABEL,
  SEVERITY_LABEL,
  SEVERITY_VARIANT,
  STATUS_COLOR_CLASS,
  STATUS_LABEL,
  getDdaEvidenceGapsAuditor,
} from "@/lib/api/dda-evidence-gaps";

interface Props {
  token: string;
}

const STATUS_FILTER_VALUES: { value: GapStatus | "all"; label: string }[] = [
  { value: "all", label: "Todos los estados" },
  { value: "missing", label: "Sin evidencia" },
  { value: "partial", label: "Parciales" },
  { value: "covered", label: "Cubiertas" },
  { value: "not_applicable", label: "No aplican" },
];

const FAMILY_FILTER_VALUES = [
  { value: "all", label: "Todas las familias" },
  { value: "org", label: "Organizativo (org)" },
  { value: "op", label: "Operacional (op)" },
  { value: "mp", label: "Protección (mp)" },
];

function MedidaCell({
  medida,
  onClick,
}: {
  medida: MedidaGapRow;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "rounded-md border-2 px-2 py-1 text-left text-[11px] transition-all " +
        "hover:scale-105 focus:scale-105 focus:outline-none " +
        "focus:ring-2 focus:ring-fulkro-primary-700 " +
        STATUS_COLOR_CLASS[medida.status]
      }
      data-testid={`gap-medida-cell-${medida.medida_code}`}
      aria-label={`Medida ${medida.medida_code}, estado ${STATUS_LABEL[medida.status]}, ${medida.evidence_count} de ${medida.min_required} evidencias`}
      title={
        medida.gap_reason
          ? `${medida.gap_reason}`
          : `${STATUS_LABEL[medida.status]} · ${medida.evidence_count}/${medida.min_required}`
      }
    >
      <span className="block font-mono font-semibold">
        {medida.medida_code}
      </span>
      <span className="block text-[9px] opacity-80">
        {medida.evidence_count}/{medida.min_required}
      </span>
    </button>
  );
}

function SeverityCard({
  label,
  count,
  icon: Icon,
  variant,
}: {
  label: string;
  count: number;
  icon: typeof AlertCircle;
  variant: "danger" | "warning" | "info" | "success";
}) {
  const cn: Record<typeof variant, string> = {
    danger: "border-fulkro-danger-700/40 bg-fulkro-danger-700/5 text-fulkro-danger-700",
    warning: "border-fulkro-warning-700/40 bg-fulkro-warning-700/5 text-fulkro-warning-700",
    info: "border-fulkro-info-700/40 bg-fulkro-info-700/5 text-fulkro-info-700",
    success: "border-fulkro-success-700/40 bg-fulkro-success-700/5 text-fulkro-success-700",
  };
  return (
    <div
      className={`rounded-md border-2 p-3 ${cn[variant]}`}
      data-testid={`gap-severity-card-${variant}`}
    >
      <div className="flex items-center gap-2">
        <Icon size={14} aria-hidden="true" />
        <p className="text-[11px] uppercase tracking-wider">{label}</p>
      </div>
      <p className="mt-1 text-2xl font-bold">{count}</p>
    </div>
  );
}

function MedidaDrawer({
  medida,
  onClose,
  token,
}: {
  medida: MedidaGapRow;
  onClose: () => void;
  token: string;
}) {
  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md overflow-y-auto border-l border-fulkro-ink-300 bg-white shadow-xl"
      role="dialog"
      aria-label={`Detalle medida ${medida.medida_code}`}
      data-testid="gap-medida-drawer"
    >
      <div className="sticky top-0 flex items-center justify-between border-b border-fulkro-ink-300 bg-white px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Medida ENS
          </p>
          <p className="font-mono text-sm font-semibold text-fulkro-ink-900">
            {medida.medida_code}
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={onClose}
          aria-label="Cerrar detalle"
          data-testid="gap-drawer-close"
        >
          <X size={14} aria-hidden="true" />
        </Button>
      </div>

      <div className="space-y-4 px-4 py-3 text-sm">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Nombre
          </p>
          <p className="text-fulkro-ink-900">{medida.medida_nombre ?? "—"}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={SEVERITY_VARIANT[medida.severity]}>
            {SEVERITY_LABEL[medida.severity]}
          </Badge>
          <span
            className={
              "rounded-md border px-2 py-0.5 text-[11px] " +
              STATUS_COLOR_CLASS[medida.status]
            }
          >
            {STATUS_LABEL[medida.status]}
          </span>
          {medida.family ? (
            <Badge variant="outline">
              {FAMILY_LABEL[medida.family] ?? medida.family}
            </Badge>
          ) : null}
        </div>

        {medida.gap_reason ? (
          <Alert variant="warning">
            <AlertTriangle size={14} aria-hidden="true" />
            <AlertTitle>Motivo del gap</AlertTitle>
            <AlertDescription>{medida.gap_reason}</AlertDescription>
          </Alert>
        ) : null}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-[12px]">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
              Evidencias aportadas
            </p>
            <p className="text-sm font-semibold text-fulkro-ink-900">
              {medida.evidence_count} / {medida.min_required}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
              Última actualización
            </p>
            <p className="text-sm text-fulkro-ink-900">
              {medida.last_uploaded_at
                ? new Date(medida.last_uploaded_at).toLocaleDateString()
                : "—"}
            </p>
            {medida.stale ? (
              <Badge variant="warning" className="mt-1">
                Antigua (revisión pendiente)
              </Badge>
            ) : null}
          </div>
        </div>

        {medida.aplicabilidad_dda ? (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-fulkro-ink-500">
              DdA · Aplicabilidad
            </p>
            <p className="text-[13px] text-fulkro-ink-900">
              {medida.aplicabilidad_dda}
            </p>
          </div>
        ) : null}

        {medida.evidences_summary.length > 0 ? (
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Evidencias (top 5 recientes)
            </p>
            <ul className="mt-1 space-y-1">
              {medida.evidences_summary.map((e) => (
                <li
                  key={e.id}
                  className="rounded border border-fulkro-ink-300 bg-fulkro-ink-50 px-2 py-1 text-[12px]"
                >
                  <p className="font-medium text-fulkro-ink-900">
                    {e.fichero_nombre_original ?? e.nombre_tipo ?? "Evidencia"}
                  </p>
                  <p className="text-[10px] text-fulkro-ink-500">
                    {e.fecha_evidencia
                      ? new Date(e.fecha_evidencia).toLocaleDateString()
                      : "Sin fecha"}{" "}
                    · {e.vigente ? "vigente" : "no vigente"}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="border-t border-fulkro-ink-300 pt-3">
          <ClarificationButton
            token={token}
            targetType="medida"
            targetId={medida.medida_code}
            targetLabel={`Medida ${medida.medida_code}`}
            buttonLabel="Solicitar aclaración sobre esta medida"
            buttonVariant="outline"
            compact
          />
        </div>
      </div>
    </div>
  );
}

function MedidaFamilySection({
  family,
  medidas,
  onSelect,
}: {
  family: string;
  medidas: MedidaGapRow[];
  onSelect: (m: MedidaGapRow) => void;
}) {
  if (medidas.length === 0) return null;
  return (
    <Card data-testid={`gap-family-section-${family}`}>
      <CardHeader>
        <CardTitle className="text-base">
          {FAMILY_LABEL[family] ?? family}{" "}
          <span className="text-[12px] font-normal text-fulkro-ink-500">
            ({medidas.length})
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {medidas.map((m) => (
            <MedidaCell
              key={m.medida_code}
              medida={m}
              onClick={() => onSelect(m)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function DdaEvidenceGapsView({ token }: Props) {
  const [statusFilter, setStatusFilter] = React.useState<GapStatus | "all">(
    "all",
  );
  const [familyFilter, setFamilyFilter] = React.useState<string>("all");
  const [search, setSearch] = React.useState("");
  const [drawerMedida, setDrawerMedida] = React.useState<MedidaGapRow | null>(
    null,
  );

  const matrixQ = useQuery<DdaEvidenceGapMatrix>({
    queryKey: ["auditor-portal", "dda-gaps", token],
    queryFn: () => getDdaEvidenceGapsAuditor(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const filtered = React.useMemo(() => {
    if (!matrixQ.data) return [];
    return matrixQ.data.medidas.filter((m) => {
      if (statusFilter !== "all" && m.status !== statusFilter) return false;
      if (familyFilter !== "all" && m.family !== familyFilter) return false;
      if (search.trim()) {
        const lower = search.trim().toLowerCase();
        if (
          !m.medida_code.toLowerCase().includes(lower) &&
          !(m.medida_nombre ?? "").toLowerCase().includes(lower)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [matrixQ.data, statusFilter, familyFilter, search]);

  const byFamily = React.useMemo(() => {
    const groups: Record<string, MedidaGapRow[]> = {
      org: [],
      op: [],
      mp: [],
    };
    for (const m of filtered) {
      const f = m.family ?? "other";
      if (!groups[f]) groups[f] = [];
      groups[f].push(m);
    }
    return groups;
  }, [filtered]);

  if (matrixQ.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="gap-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Calculando análisis de cobertura DdA-Evidencia…
      </div>
    );
  }

  if (matrixQ.isError || !matrixQ.data) {
    return (
      <Alert variant="danger" data-testid="gap-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo calcular el análisis</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  const matrix = matrixQ.data;

  return (
    <div className="space-y-4" data-testid="gap-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <HelpCircle
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Cobertura DdA · Evidencias
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Cobertura global
            </p>
            <p
              className="text-2xl font-bold text-fulkro-ink-900"
              data-testid="gap-coverage-pct"
            >
              {matrix.coverage_pct.toFixed(1)}%
            </p>
            <p className="text-[11px] text-fulkro-ink-500">
              {matrix.total_covered}/{matrix.total_applicable} cubiertas
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Parciales
            </p>
            <p
              className="text-2xl font-bold text-fulkro-warning-700"
              data-testid="gap-total-partial"
            >
              {matrix.total_partial}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Sin evidencia
            </p>
            <p
              className="text-2xl font-bold text-fulkro-danger-700"
              data-testid="gap-total-missing"
            >
              {matrix.total_missing}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              No aplican
            </p>
            <p className="text-2xl font-bold text-fulkro-ink-500">
              {matrix.total_not_applicable}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-4">
        <SeverityCard
          label="Críticas sin evidencia"
          count={matrix.severity_summary.critical_missing}
          icon={AlertCircle}
          variant="danger"
        />
        <SeverityCard
          label="Altas parciales"
          count={matrix.severity_summary.high_partial}
          icon={AlertTriangle}
          variant="warning"
        />
        <SeverityCard
          label="Recuperables"
          count={matrix.severity_summary.recoverable}
          icon={CheckCircle}
          variant="info"
        />
        <SeverityCard
          label="Medias / Bajas"
          count={
            matrix.severity_summary.medium_total +
            matrix.severity_summary.low_total
          }
          icon={HelpCircle}
          variant="success"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="gap-status-filter" className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Estado
            </label>
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as GapStatus | "all")}
            >
              <SelectTrigger
                id="gap-status-filter"
                className="w-48"
                aria-label="Filtrar por estado"
                data-testid="gap-status-filter"
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
            <label htmlFor="gap-family-filter" className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Familia
            </label>
            <Select
              value={familyFilter}
              onValueChange={setFamilyFilter}
            >
              <SelectTrigger
                id="gap-family-filter"
                className="w-52"
                aria-label="Filtrar por familia"
                data-testid="gap-family-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FAMILY_FILTER_VALUES.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Search size={14} className="text-fulkro-ink-500" aria-hidden="true" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código o nombre"
              aria-label="Buscar medida"
              data-testid="gap-search"
              className="h-9"
            />
          </div>
          <p className="text-[11px] text-fulkro-ink-500" data-testid="gap-filtered-count">
            {filtered.length} medidas con los filtros aplicados
          </p>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <MedidaFamilySection
          family="org"
          medidas={byFamily.org ?? []}
          onSelect={setDrawerMedida}
        />
        <MedidaFamilySection
          family="op"
          medidas={byFamily.op ?? []}
          onSelect={setDrawerMedida}
        />
        <MedidaFamilySection
          family="mp"
          medidas={byFamily.mp ?? []}
          onSelect={setDrawerMedida}
        />
      </div>

      {drawerMedida ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-fulkro-ink-900/50"
            onClick={() => setDrawerMedida(null)}
            aria-label="Cerrar detalle"
          />
          <MedidaDrawer
            medida={drawerMedida}
            onClose={() => setDrawerMedida(null)}
            token={token}
          />
        </>
      ) : null}
    </div>
  );
}
