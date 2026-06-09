"use client";

/**
 * EvidencePackView · pack de evidencia ENAC (doc §16).
 *
 * El superpoder de auditoría del pipeline NO es "encontrar todo": es producir
 * un rastro de evidencia impecable, reproducible y trazable. Esta vista
 * sintetiza lo que el auditor verifica: metodología, cobertura% honesta,
 * integridad R6 (hash chain), hallazgos mapeados a medidas del Anexo II,
 * estados de cierre y el disclaimer honesto.
 *
 * Read-only · consume GET /projects/{id}/verification/runs/{rid}/evidence-pack.
 */
import {
  BookOpenCheck,
  FileCheck2,
  Fingerprint,
  Loader2,
  ShieldCheck,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useEvidencePack } from "@/hooks/useAutopilot";

interface EvidencePackViewProps {
  projectId: string;
  runId: string | null;
}

export function EvidencePackView({ projectId, runId }: EvidencePackViewProps) {
  const { data, isLoading, isError, error } = useEvidencePack(projectId, runId);

  if (!runId) {
    return (
      <Card data-testid="evidence-pack-empty">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck2 size={20} className="text-fulkro-primary-700" />
            Pack de evidencia ENAC
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[color:var(--fulkro-muted)]">
            Lanza un autopilot para generar el pack de evidencia auditable.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-2 p-6 text-sm text-[color:var(--fulkro-muted)]">
          <Loader2 size={14} className="animate-spin" /> generando pack de
          evidencia…
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          No se pudo obtener el pack de evidencia:{" "}
          {(error as Error)?.message ?? "error"}
        </CardContent>
      </Card>
    );
  }

  const medidas = Object.entries(data.hallazgos.por_medida_ens);
  const estados = Object.entries(data.hallazgos.por_estado);
  const r6Ok = data.integridad_r6.ok;

  return (
    <Card data-testid="evidence-pack-view">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <FileCheck2 size={20} className="text-fulkro-primary-700" />
            Pack de evidencia ENAC
          </CardTitle>
          <CardDescription>
            Run #{data.run_id.slice(0, 8)}… · Categoría{" "}
            <span className="font-semibold">{data.categoria_ens ?? "—"}</span> ·
            síntesis auditable del proceso, evidencia y cierre.
          </CardDescription>
        </div>
        {r6Ok != null && (
          <Badge variant={r6Ok ? "success" : "danger"}>
            <ShieldCheck size={12} className="mr-1" />
            Integridad R6 {r6Ok ? "OK" : "FALLO"}
          </Badge>
        )}
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {/* Metodología */}
        <section>
          <h4 className="mb-1.5 flex items-center gap-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            <BookOpenCheck size={14} /> Metodología
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {data.metodologia.map((m) => (
              <Badge key={m} variant="secondary">
                {m}
              </Badge>
            ))}
          </div>
        </section>

        {/* Cobertura honesta */}
        <section className="grid gap-3 sm:grid-cols-3">
          <Metric
            label="Cobertura"
            value={`${data.cobertura.coverage_pct.toFixed(1)}%`}
            hint="Métrica de honestidad: porcentaje de activos en alcance efectivamente probados."
            emphasis={data.cobertura.coverage_pct >= 95 ? "success" : "warning"}
          />
          <Metric
            label="Activos probados"
            value={`${data.cobertura.assets_scanned ?? 0}/${
              data.cobertura.assets_in_scope ?? 0
            }`}
          />
          <Metric
            label="Hallazgos"
            value={String(data.hallazgos.total)}
            hint={`${data.hallazgos.zero_fp_verified} verificados Cero Falsos Positivos.`}
          />
        </section>

        {data.cobertura.partial_run && (
          <Alert variant="warning">
            <AlertTitle>Run parcial</AlertTitle>
            <AlertDescription>
              No se completó el escaneo de todos los activos. La cobertura
              reportada es exacta a lo probado · honestidad del alcance.
            </AlertDescription>
          </Alert>
        )}

        {/* Determinismo */}
        {data.determinismo.run_manifest_hash && (
          <section className="flex items-center gap-2 text-xs">
            <Fingerprint size={14} className="text-fulkro-primary-700" />
            <span className="font-semibold text-[color:var(--fulkro-subtitle)]">
              Determinismo (run_manifest_hash):
            </span>
            <code
              className="rounded bg-fulkro-ink-50 px-1.5 py-0.5 font-mono text-[11px] text-fulkro-ink-700"
              title={data.determinismo.run_manifest_hash}
            >
              {data.determinismo.run_manifest_hash.slice(0, 24)}…
            </code>
          </section>
        )}

        {/* Severidad */}
        <section>
          <h4 className="mb-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
            Hallazgos por severidad
          </h4>
          <div className="flex flex-wrap gap-2 text-sm">
            <span>
              <strong className="text-fulkro-danger">
                {data.hallazgos.severidad.critical}
              </strong>{" "}
              críticos
            </span>
            <span>
              <strong className="text-fulkro-danger/80">
                {data.hallazgos.severidad.high}
              </strong>{" "}
              altos
            </span>
            <span>
              <strong className="text-fulkro-warning">
                {data.hallazgos.severidad.medium}
              </strong>{" "}
              medios
            </span>
            <span>
              <strong className="text-fulkro-info">
                {data.hallazgos.severidad.low}
              </strong>{" "}
              bajos
            </span>
            <span>
              <strong>{data.hallazgos.severidad.info}</strong> info
            </span>
          </div>
        </section>

        {/* Hallazgos por medida ENS Anexo II */}
        {medidas.length > 0 && (
          <section>
            <h4 className="mb-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Trazabilidad a medidas{" "}
              <TooltipENS term="ENS" text="Esquema Nacional de Seguridad · RD 311/2022" icon="info" iconSize={12} />{" "}
              <TooltipENS term="Anexo_II" text="Anexo II · catálogo de medidas de seguridad" icon="info" iconSize={12} />
            </h4>
            <ul className="flex flex-col gap-1 text-sm">
              {medidas.map(([measure, items]) => (
                <li
                  key={measure}
                  className="flex items-center justify-between gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] px-2.5 py-1.5"
                >
                  <code className="font-mono text-xs text-fulkro-primary-700">
                    {measure}
                  </code>
                  <span className="text-xs text-[color:var(--fulkro-muted)]">
                    {items.length} hallazgo(s)
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Estados de cierre */}
        <section className="grid gap-3 sm:grid-cols-2">
          <div>
            <h4 className="mb-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Estados de cierre
            </h4>
            <ul className="flex flex-col gap-0.5 text-sm">
              {estados.length === 0 ? (
                <li className="text-[color:var(--fulkro-muted)]">
                  Sin hallazgos registrados.
                </li>
              ) : (
                estados.map(([state, count]) => (
                  <li key={state} className="flex items-center justify-between">
                    <span className="font-mono text-xs">{state}</span>
                    <span className="font-semibold">{count}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
          <div>
            <h4 className="mb-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Delta de cierre
            </h4>
            <ul className="flex flex-col gap-0.5 text-sm">
              <li className="flex justify-between">
                <span>Cerrados</span>
                <strong className="text-fulkro-success">
                  {data.cierre.closed}
                </strong>
              </li>
              <li className="flex justify-between">
                <span>Riesgo aceptado</span>
                <strong className="text-fulkro-warning">
                  {data.cierre.risk_accepted}
                </strong>
              </li>
              <li className="flex justify-between">
                <span>Nuevos / resueltos</span>
                <span>
                  +{data.cierre.delta_new} / -{data.cierre.delta_resolved}
                </span>
              </li>
            </ul>
          </div>
        </section>

        {/* Gate 2 atestación */}
        {data.gate2_atestacion.required && (
          <Alert variant={data.gate2_atestacion.done ? "success" : "warning"}>
            <ShieldCheck size={16} />
            <AlertTitle>Gate 2 · atestación cualificada</AlertTitle>
            <AlertDescription>
              {data.gate2_atestacion.done ? (
                <>
                  Atestado por{" "}
                  <strong>
                    {data.gate2_atestacion.external_pentester ?? "—"}
                  </strong>
                  {data.gate2_atestacion.cert
                    ? ` (${data.gate2_atestacion.cert})`
                    : ""}
                  .
                </>
              ) : (
                <>
                  Pendiente de validación y firma del pentester acreditado
                  (estado: {data.gate2_atestacion.status ?? "—"}).
                </>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Rastro de evidencia */}
        {data.evidence_trail.length > 0 && (
          <section>
            <h4 className="mb-1.5 text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Rastro de evidencia ({data.evidence_trail.length})
            </h4>
            <div className="max-h-48 overflow-y-auto rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-fulkro-ink-50 p-2 text-[11px]">
              <ul className="space-y-0.5 font-mono">
                {data.evidence_trail.map((e, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-fulkro-ink-500">
                      {e.ts
                        ? new Date(e.ts).toLocaleString("es-ES", {
                            hour12: false,
                          })
                        : "—"}
                    </span>
                    <span className="font-semibold text-fulkro-title">
                      {e.action}
                    </span>
                    <span className="truncate text-fulkro-ink-500">
                      {e.actor} · {e.component}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}

        {/* Disclaimer honesto */}
        <Alert variant="info" data-testid="evidence-pack-disclaimer">
          <AlertTitle>Alcance honesto</AlertTitle>
          <AlertDescription>{data.disclaimer}</AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

function Metric({
  label,
  value,
  hint,
  emphasis,
}: {
  label: string;
  value: string;
  hint?: string;
  emphasis?: "success" | "warning";
}) {
  return (
    <div className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] p-3">
      <p className="text-[12px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
        {hint && (
          <>
            {" "}
            <TooltipENS text={hint} icon="info" iconSize={11} />
          </>
        )}
      </p>
      <p
        className={
          emphasis === "success"
            ? "text-2xl font-semibold text-fulkro-success-700"
            : emphasis === "warning"
              ? "text-2xl font-semibold text-fulkro-warning-700"
              : "text-2xl font-semibold text-fulkro-primary-700"
        }
      >
        {value}
      </p>
    </div>
  );
}
