/**
 * SIEM · Consola de eventos de seguridad (FRENTE N · admin top-level R23).
 *
 * Correlación determinista de pentest (M8) + incidentes (M19) + escalados (M18)
 * + alertas de cumplimiento. Read-only (ADR-014). Fondos SÓLIDOS (FRENTE G ·
 * nada translúcido). op.mon.1 (detección) + op.mon.2 (métricas).
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bug,
  ShieldAlert,
  Siren,
  RefreshCw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getSiemOverview,
  type SiemEvent,
  type SiemSeverity,
} from "@/lib/api/siem";

const SEVERITY_META: Record<
  SiemSeverity,
  { label: string; badge: "danger" | "warning" | "secondary" | "outline" }
> = {
  critical: { label: "Críticos", badge: "danger" },
  high: { label: "Altos", badge: "danger" },
  medium: { label: "Medios", badge: "warning" },
  low: { label: "Bajos", badge: "secondary" },
  info: { label: "Info", badge: "outline" },
};

const SOURCE_ICON: Record<string, typeof Bug> = {
  pentest: Bug,
  incident: Siren,
  escalation: AlertTriangle,
  compliance: ShieldAlert,
};

export default function SiemPage() {
  const query = useQuery({
    queryKey: ["siem", "overview"],
    queryFn: () => getSiemOverview(),
    refetchInterval: 60_000,
  });

  return (
    <div className="flex flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-fulkro-ink-900">
            <ShieldAlert className="text-fulkro-primary" /> SIEM · Eventos de seguridad
          </h1>
          <p className="mt-1 text-sm text-fulkro-ink-600">
            Correlación de pentest, incidentes y cumplimiento · op.mon.1/op.mon.2 ·
            solo lectura.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
          data-testid="siem-refresh"
        >
          <RefreshCw size={14} className={query.isFetching ? "animate-spin" : ""} />
          <span className="ml-2">Actualizar</span>
        </Button>
      </header>

      {query.isLoading ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <Card className="border-fulkro-danger-300 bg-white">
          <CardContent className="flex items-center gap-2 py-4 text-fulkro-danger-700">
            <AlertTriangle size={16} /> No se pudo cargar el SIEM.
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void query.refetch()}
              data-testid="siem-retry"
            >
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : query.data ? (
        <>
          {/* Tiles de severidad (fondos sólidos) */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {(Object.keys(SEVERITY_META) as SiemSeverity[]).map((sev) => (
              <Card key={sev} className="bg-white">
                <CardContent className="py-4">
                  <div className="text-3xl font-bold text-fulkro-ink-900">
                    {query.data.by_severity[sev] ?? 0}
                  </div>
                  <div className="mt-1 text-sm text-fulkro-ink-600">
                    {SEVERITY_META[sev].label}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Correlaciones activas */}
          <Card className="bg-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Siren size={18} className="text-fulkro-danger-700" />
                Correlaciones activas ({query.data.correlation_count})
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {query.data.correlations.length === 0 ? (
                <p className="text-sm text-fulkro-ink-500">
                  Sin correlaciones de riesgo activas. Todo en orden.
                </p>
              ) : (
                query.data.correlations.map((c) => (
                  <div
                    key={c.rule_id + (c.project_id ?? "")}
                    className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-fulkro-ink-900">
                        {c.title}
                      </span>
                      <Badge variant={SEVERITY_META[c.severity].badge}>
                        {c.severity}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-fulkro-ink-600">
                      {c.description}
                    </p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Timeline de eventos */}
          <Card className="bg-white">
            <CardHeader>
              <CardTitle>
                Eventos ({query.data.active_events} activos / {query.data.total_events})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-fulkro-ink-200 text-left text-fulkro-ink-500">
                      <th className="px-2 py-2">Fuente</th>
                      <th className="px-2 py-2">Sev.</th>
                      <th className="px-2 py-2">Evento</th>
                      <th className="px-2 py-2">Fecha</th>
                      <th className="px-2 py-2">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.events.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-2 py-6 text-center text-fulkro-ink-500">
                          Sin eventos de seguridad registrados.
                        </td>
                      </tr>
                    ) : (
                      query.data.events.map((e: SiemEvent) => {
                        const Icon = SOURCE_ICON[e.source] ?? ShieldAlert;
                        return (
                          <tr
                            key={`${e.source}-${e.ref_id}`}
                            className="border-b border-fulkro-ink-100 last:border-b-0 hover:bg-fulkro-ink-50"
                          >
                            <td className="px-2 py-2">
                              <span className="inline-flex items-center gap-1 capitalize">
                                <Icon size={13} className="text-fulkro-ink-500" />
                                {e.source}
                              </span>
                            </td>
                            <td className="px-2 py-2">
                              <Badge variant={SEVERITY_META[e.severity].badge}>
                                {e.severity}
                              </Badge>
                            </td>
                            <td className="px-2 py-2 text-fulkro-ink-900">{e.title}</td>
                            <td className="px-2 py-2 font-mono text-xs text-fulkro-ink-500">
                              {e.occurred_at?.slice(0, 16).replace("T", " ") ?? "—"}
                            </td>
                            <td className="px-2 py-2">
                              {e.resolved ? (
                                <Badge variant="secondary">resuelto</Badge>
                              ) : (
                                <Badge variant="outline">activo</Badge>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
