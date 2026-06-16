"use client";

/**
 * Motor 5 - Obligations Board (zero-mock, FASE 9.A.6).
 *
 * Refactor desde version mock (useProjectData.useObligations + mockObligations)
 * a backend real (M04 + M05). Combina:
 *  - GET /api/v1/projects/{id}/obligations  (lista plana)
 *  - GET /api/v1/projects/{id}/obligations/summary (KPI counts)
 *
 * Acciones (lifecycle): start / complete / verify - via mutations reales.
 *
 * CONSISTENCY-001:
 *  - tokens FULKRO (--fulkro-*)
 *  - Badge variants (success / warning / danger / info / outline)
 *  - Button primary / outline FULKRO
 *  - Card glass
 *  - lucide strokeWidth 2.2-2.4
 *  - Skeleton para loading / Alert variant="danger" para error / EmptyState
 */
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Loader2,
  PlayCircle,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  type LucideIcon,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { InfoTag } from "@/components/ui/info-tag";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useCompleteObligation,
  useObligations,
  useObligationsSummary,
  useStartObligation,
  useVerifyObligation,
} from "@/hooks/useObligations";
import type {
  ObligationEstado,
  ObligationOut,
} from "@/lib/api/obligations";
import { cn } from "@/lib/utils";

// ===================================================================
// Mappings backend (estado / modo) -> labels y variants UI
// ===================================================================

const ESTADO_LABEL: Record<string, string> = {
  pendiente: "Pendiente",
  en_curso: "En curso",
  completada: "Completada",
  verificada: "Verificada",
  bloqueada: "Bloqueada",
};

type BadgeVariant =
  | "default"
  | "secondary"
  | "accent"
  | "outline"
  | "success"
  | "warning"
  | "info"
  | "danger";

const ESTADO_VARIANT: Record<string, BadgeVariant> = {
  verificada: "success",
  completada: "info",
  en_curso: "warning",
  pendiente: "outline",
  bloqueada: "danger",
};

const MODO_LABEL: Record<string, string> = {
  consultor_redacta: "Consultor redacta",
  cliente_aporta_evidencia: "Cliente aporta",
  validacion_existente: "Validar existente",
  configuracion_tecnica: "Configuración técnica",
};

// ===================================================================
// #24 Ola 6 · secuenciar por la estructura del Anexo II RD 311/2022.
// Las medidas ENS NO tienen fase lifecycle (todas son implantación) · su
// secuencia canónica es por MARCO (org → op → mp) · derivable del prefijo del
// measure_code (org.1 · op.acc.5 · mp.s.2 …). NO requiere backend ni migración.
// ===================================================================

const MARCO_ORDER = ["org", "op", "mp", "otros"] as const;
type MarcoKey = (typeof MARCO_ORDER)[number];

const MARCO_LABEL: Record<MarcoKey, string> = {
  org: "Marco organizativo (org)",
  op: "Marco operacional (op)",
  mp: "Medidas de protección (mp)",
  otros: "Sin medida asociada",
};

function marcoOf(measureCode: string | null): MarcoKey {
  const prefix = (measureCode ?? "").split(".")[0]?.toLowerCase();
  return prefix === "org" || prefix === "op" || prefix === "mp"
    ? prefix
    : "otros";
}

// ===================================================================
// Componente principal
// ===================================================================

export function ObligationBoard({ projectId }: { projectId: string }) {
  const obligationsQuery = useObligations(projectId);
  const summaryQuery = useObligationsSummary(projectId);

  const obligations: ObligationOut[] = React.useMemo(
    () => obligationsQuery.data ?? [],
    [obligationsQuery.data],
  );

  const [search, setSearch] = React.useState("");
  const [estado, setEstado] = React.useState<ObligationEstado | "all">("all");
  const [modo, setModo] = React.useState<string>("all");
  const [selected, setSelected] = React.useState<ObligationOut | null>(null);

  const modos = React.useMemo(
    () =>
      Array.from(
        new Set(
          obligations
            .map((o) => o.modo_ejecucion)
            .filter((m): m is string => !!m),
        ),
      ).sort(),
    [obligations],
  );

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return obligations.filter((o) => {
      if (estado !== "all" && o.estado !== estado) return false;
      if (modo !== "all" && o.modo_ejecucion !== modo) return false;
      if (!q) return true;
      return (
        (o.measure_code ?? "").toLowerCase().includes(q) ||
        o.titulo.toLowerCase().includes(q) ||
        o.descripcion.toLowerCase().includes(q)
      );
    });
  }, [obligations, search, estado, modo]);

  // #24 · agrupar las medidas filtradas por marco (org → op → mp → otros),
  // ordenadas por measure_code dentro de cada marco (familia + número natural).
  const marcoGroups = React.useMemo(() => {
    const byMarco = new Map<MarcoKey, ObligationOut[]>();
    for (const o of filtered) {
      const key = marcoOf(o.measure_code);
      const arr = byMarco.get(key);
      if (arr) arr.push(o);
      else byMarco.set(key, [o]);
    }
    return MARCO_ORDER.map((marco) => ({
      marco,
      items: (byMarco.get(marco) ?? []).sort((a, b) =>
        (a.measure_code ?? "").localeCompare(b.measure_code ?? "", undefined, {
          numeric: true,
        }),
      ),
    })).filter((g) => g.items.length > 0);
  }, [filtered]);

  // Loading
  if (obligationsQuery.isLoading) {
    return <LoadingSkeleton />;
  }

  // Error
  if (obligationsQuery.isError) {
    return (
      <Alert variant="danger">
        <AlertTriangle size={16} strokeWidth={2.4} />
        <AlertTitle>No se pudieron cargar las obligaciones</AlertTitle>
        <AlertDescription>
          {obligationsQuery.error instanceof Error
            ? obligationsQuery.error.message
            : "Error desconocido. Reintenta o consulta el log del backend."}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <SummaryStrip
        total={summaryQuery.data?.total ?? obligations.length}
        pendientes={summaryQuery.data?.pendientes ?? 0}
        enCurso={summaryQuery.data?.en_curso ?? 0}
        completadas={summaryQuery.data?.completadas ?? 0}
        verificadas={summaryQuery.data?.verificadas ?? 0}
        loading={summaryQuery.isLoading}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span>Obligaciones del proyecto</span>
              <span className="text-xs font-normal text-fulkro-ink-500">
                {filtered.length}/{obligations.length}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 md:grid-cols-4">
              <div className="relative md:col-span-2">
                <Search
                  size={14}
                  strokeWidth={2.2}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fulkro-ink-500"
                />
                <Input
                  placeholder="Buscar código, título o descripción…"
                  className="pl-8"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <FilterSelect
                ariaLabel="Filtrar obligaciones por estado"
                value={estado}
                onValueChange={(v) =>
                  setEstado(v as ObligationEstado | "all")
                }
                options={[
                  { value: "all", label: "Todos los estados" },
                  { value: "pendiente", label: "Pendientes" },
                  { value: "en_curso", label: "En curso" },
                  { value: "completada", label: "Completadas" },
                  { value: "verificada", label: "Verificadas" },
                  { value: "bloqueada", label: "Bloqueadas" },
                ]}
              />
              <FilterSelect
                ariaLabel="Filtrar obligaciones por modo de ejecución"
                value={modo}
                onValueChange={setModo}
                options={[
                  { value: "all", label: "Todos los modos" },
                  ...modos.map((m) => ({
                    value: m,
                    label: MODO_LABEL[m] ?? m,
                  })),
                ]}
              />
            </div>

            {filtered.length === 0 ? (
              <EmptyState
                icon={<ShieldCheck size={28} strokeWidth={2.2} />}
                title={
                  obligations.length === 0
                    ? "Sin obligaciones instanciadas"
                    : "Ningún registro coincide con los filtros"
                }
                description={
                  obligations.length === 0
                    ? "Ejecuta el análisis de gaps (M04) y la instanciación M05 para poblar este tablero."
                    : "Ajusta los filtros o limpia la búsqueda."
                }
              />
            ) : (
              <div className="overflow-x-auto rounded-md border border-[color:var(--fulkro-surface-glass-border)]">
                <table
                  aria-label="Obligaciones y medidas del proyecto"
                  className="min-w-full divide-y divide-fulkro-ink-300/60 text-sm"
                >
                  <thead className="bg-[color:var(--fulkro-surface-glass-strong)] text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold">
                        Medida
                      </th>
                      <th className="px-3 py-2 text-left font-semibold">
                        Título
                      </th>
                      <th className="px-3 py-2 text-left font-semibold">
                        Estado
                      </th>
                      <th className="px-3 py-2 text-left font-semibold">
                        Modo
                      </th>
                      <th className="px-3 py-2 text-left font-semibold">
                        Resp.
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-fulkro-ink-300/40 bg-white">
                    {marcoGroups.map((group) => (
                      <React.Fragment key={group.marco}>
                        <tr className="bg-[color:var(--fulkro-surface-glass)]">
                          <td
                            colSpan={5}
                            className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]"
                          >
                            {MARCO_LABEL[group.marco]} · {group.items.length}
                          </td>
                        </tr>
                        {group.items.map((o) => {
                      const active = selected?.id === o.id;
                      return (
                        <tr
                          key={o.id}
                          className={cn(
                            "cursor-pointer transition-colors",
                            active
                              ? "bg-fulkro-primary-700/5"
                              : "hover:bg-[color:var(--fulkro-surface-glass)]",
                          )}
                          onClick={() => setSelected(o)}
                        >
                          <td className="whitespace-nowrap px-3 py-2 font-mono text-xs font-bold text-[color:var(--fulkro-subtitle)]">
                            {o.measure_code ?? "—"}
                          </td>
                          <td className="px-3 py-2">
                            <span className="font-bold text-[color:var(--fulkro-title)]">
                              {o.titulo}
                            </span>
                            {o.descripcion ? (
                              <p className="mt-0.5 line-clamp-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                                {o.descripcion}
                              </p>
                            ) : null}
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              variant={
                                ESTADO_VARIANT[o.estado] ?? "outline"
                              }
                            >
                              {ESTADO_LABEL[o.estado] ?? o.estado}
                            </Badge>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-fulkro-ink-500">
                            {o.modo_ejecucion
                              ? MODO_LABEL[o.modo_ejecucion] ??
                                o.modo_ejecucion
                              : "—"}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2 text-fulkro-ink-500">
                            {o.responsable ?? "—"}
                          </td>
                        </tr>
                      );
                        })}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <ObligationDetailPanel
          projectId={projectId}
          obligation={selected}
          onClose={() => setSelected(null)}
        />
      </div>
    </div>
  );
}

// ===================================================================
// SummaryStrip (KPIs por estado)
// ===================================================================

function SummaryStrip({
  total,
  pendientes,
  enCurso,
  completadas,
  verificadas,
  loading,
}: {
  total: number;
  pendientes: number;
  enCurso: number;
  completadas: number;
  verificadas: number;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  const items: {
    label: string;
    value: number;
    icon: LucideIcon;
    accent: string;
  }[] = [
    {
      label: "Total",
      value: total,
      icon: ShieldCheck,
      accent: "text-[color:var(--fulkro-title)]",
    },
    {
      label: "Pendientes",
      value: pendientes,
      icon: CircleDashed,
      accent: "text-fulkro-warning",
    },
    {
      label: "En curso",
      value: enCurso,
      icon: PlayCircle,
      accent: "text-fulkro-info",
    },
    {
      label: "Completadas",
      value: completadas,
      icon: CheckCircle2,
      accent: "text-fulkro-success",
    },
    {
      label: "Verificadas",
      value: verificadas,
      icon: ShieldCheck,
      accent: "text-fulkro-success",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {items.map((it) => (
        <Card key={it.label}>
          <CardContent className="flex items-center gap-3 py-4">
            <span
              className={cn(
                "rounded-full bg-[color:var(--fulkro-surface-glass-strong)] p-2",
                it.accent,
              )}
            >
              <it.icon size={18} strokeWidth={2.2} />
            </span>
            <div>
              <p className="text-2xl font-bold text-[color:var(--fulkro-title)]">
                {it.value}
              </p>
              <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                {it.label}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ===================================================================
// FilterSelect (sub-component)
// ===================================================================

function FilterSelect({
  value,
  onValueChange,
  options,
  className,
  ariaLabel,
}: {
  value: string;
  onValueChange: (v: string) => void;
  options: { value: string; label: string }[];
  className?: string;
  ariaLabel: string;
}) {
  return (
    <select
      aria-label={ariaLabel}
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      className={cn(
        "h-10 w-full rounded-md border border-fulkro-ink-300 bg-white px-2 text-base font-medium text-[color:var(--fulkro-body)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700",
        className,
      )}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ===================================================================
// ObligationDetailPanel (lifecycle actions)
// ===================================================================

function ObligationDetailPanel({
  projectId,
  obligation,
  onClose,
}: {
  projectId: string;
  obligation: ObligationOut | null;
  onClose: () => void;
}) {
  const startMutation = useStartObligation(projectId);
  const completeMutation = useCompleteObligation(projectId);
  const verifyMutation = useVerifyObligation(projectId);

  const busy =
    startMutation.isPending ||
    completeMutation.isPending ||
    verifyMutation.isPending;

  async function transition(
    label: string,
    mutation:
      | typeof startMutation
      | typeof completeMutation
      | typeof verifyMutation,
  ) {
    if (!obligation) return;
    try {
      await mutation.mutateAsync(obligation.id);
      toast.success(`${label} (${obligation.titulo})`);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? `${label} falló: ${err.message}`
          : `${label} falló (error desconocido)`,
      );
    }
  }

  return (
    <Card className="xl:sticky xl:top-4 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Detalle</CardTitle>
        {obligation && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Cerrar detalle"
          >
            <X size={14} strokeWidth={2.4} />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {!obligation ? (
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
            Selecciona una obligación para ver su detalle y acciones.
          </p>
        ) : (
          <>
            <div>
              <p className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                {obligation.measure_code ?? "(sin medida asociada)"}
              </p>
              <p className="text-xl font-bold text-[color:var(--fulkro-title)]">
                {obligation.titulo}
              </p>
              <p className="mt-1 text-base font-medium text-[color:var(--fulkro-body)]">
                {obligation.descripcion}
              </p>
            </div>

            <dl className="grid grid-cols-2 gap-2 text-xs">
              <Field
                label="Estado"
                value={ESTADO_LABEL[obligation.estado] ?? obligation.estado}
              />
              <Field
                label="Modo"
                value={
                  obligation.modo_ejecucion
                    ? MODO_LABEL[obligation.modo_ejecucion] ??
                      obligation.modo_ejecucion
                    : "—"
                }
              />
              <Field
                label="Responsable"
                value={obligation.responsable ?? "—"}
              />
              <Field
                label="Esfuerzo (h)"
                value={
                  obligation.esfuerzo_estimado !== null
                    ? String(obligation.esfuerzo_estimado)
                    : "—"
                }
              />
              <Field
                label="Fecha objetivo"
                value={obligation.fecha_objetivo ?? "—"}
              />
              <Field
                label="Completado"
                value={obligation.fecha_completado ?? "—"}
              />
            </dl>

            {obligation.entregable_esperado ? (
              <div className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 text-sm">
                <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Entregable esperado
                </p>
                <p className="mt-0.5 font-medium text-[color:var(--fulkro-body)]">
                  {obligation.entregable_esperado}
                </p>
              </div>
            ) : null}

            <div className="space-y-2">
              <Button
                variant="outline"
                size="md"
                className="w-full"
                disabled={busy || obligation.estado === "en_curso"}
                onClick={() => transition("Iniciar", startMutation)}
              >
                {startMutation.isPending ? (
                  <Loader2
                    size={14}
                    strokeWidth={2.4}
                    className="animate-spin"
                  />
                ) : (
                  <PlayCircle size={14} strokeWidth={2.4} />
                )}
                Iniciar (start)
              </Button>
              <Button
                variant="outline"
                size="md"
                className="w-full"
                disabled={
                  busy ||
                  obligation.estado === "completada" ||
                  obligation.estado === "verificada"
                }
                onClick={() => transition("Completar", completeMutation)}
              >
                {completeMutation.isPending ? (
                  <Loader2
                    size={14}
                    strokeWidth={2.4}
                    className="animate-spin"
                  />
                ) : (
                  <CheckCircle2 size={14} strokeWidth={2.4} />
                )}
                Completar (complete)
              </Button>
              <Button
                variant="primary"
                size="md"
                className="w-full"
                disabled={busy || obligation.estado !== "completada"}
                onClick={() => transition("Verificar", verifyMutation)}
              >
                {verifyMutation.isPending ? (
                  <Loader2
                    size={14}
                    strokeWidth={2.4}
                    className="animate-spin"
                  />
                ) : (
                  <Sparkles size={14} strokeWidth={2.4} />
                )}
                Verificar (verify)
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-[color:var(--fulkro-surface-glass)] px-2 py-1.5">
      <dt className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
      </dt>
      <dd className="text-sm font-medium text-[color:var(--fulkro-body)]">
        {value}
      </dd>
    </div>
  );
}

// ===================================================================
// LoadingSkeleton (top-level)
// ===================================================================

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>
              Obligaciones del proyecto{" "}
              <TooltipENS text="Las medidas del Anexo II ENS aplicables a tu proyecto · 73 medidas obligatorias · cuáles te tocan depende de tu categoría (BÁSICA · MEDIA · ALTA)." />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Detalle</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
