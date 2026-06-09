"use client";

/**
 * MageritSummaryCard · resumen análisis MAGERIT cliente.
 *
 * Muestra:
 * - Total activos + estado análisis
 * - Distribución por tipo activo (HW · SW · DATA · etc)
 * - Distribución client_review_status
 * - Progress bar completion%
 * - Banner readiness para validar inventario
 *
 * SAN-E v3.MB-5.4 · pattern alineado DdaSummaryCard.
 */
import type { MageritClientSummary } from "@/lib/api/magerit";


interface Props {
  summary: MageritClientSummary;
  className?: string;
}


const ASSET_TYPE_LABELS: Record<string, string> = {
  S: "Servicios",
  D: "Datos / Información",
  SW: "Software / Aplicaciones",
  HW: "Hardware / Equipamiento",
  COM: "Comunicaciones",
  SI: "Soportes",
  AUX: "Equipamiento auxiliar",
  L: "Instalaciones",
  P: "Personal",
};


export function MageritSummaryCard({ summary, className = "" }: Props) {
  const {
    total_assets,
    completion_percentage,
    reviewed_count,
    pending_review_count,
    questions_count,
    suggestions_count,
    ready_for_validation_sign,
    last_signed_at,
    analysis_name,
    analysis_status,
    assets_by_type,
  } = summary;

  return (
    <div
      className={`rounded-lg border bg-card p-6 shadow-sm ${className}`.trim()}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--fulkro-title)]">
            Tu inventario MAGERIT
          </h2>
          <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
            Revisa los {total_assets} activos identificados y su valoración
            DICAT (Disponibilidad · Integridad · Confidencialidad ·
            Autenticidad · Trazabilidad).
          </p>
        </div>
        {analysis_name && (
          <div className="text-right">
            <p className="text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Análisis
            </p>
            <p className="text-sm font-semibold">{analysis_name}</p>
            {analysis_status && (
              <p className="text-xs text-[color:var(--fulkro-muted)]">
                {analysis_status}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm font-medium">Progreso revisión</span>
          <span className="text-sm tabular-nums text-[color:var(--fulkro-muted)]">
            {reviewed_count} de {total_assets} · {completion_percentage}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-fulkro-ink-100">
          <div
            className="h-full bg-fulkro-primary-700 transition-all"
            style={{ width: `${completion_percentage}%` }}
          />
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBox label="Revisadas" value={reviewed_count} variant="success" />
        <StatBox
          label="Pendientes"
          value={pending_review_count}
          variant="muted"
        />
        <StatBox label="Preguntas" value={questions_count} variant="warning" />
        <StatBox
          label="Sugerencias"
          value={suggestions_count}
          variant="info"
        />
      </dl>

      {Object.keys(assets_by_type).length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
            Activos por tipo MAGERIT
          </h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(assets_by_type).map(([code, count]) => (
              <span
                key={code}
                className="inline-flex items-center gap-1 rounded-full border bg-fulkro-ink-50 px-3 py-1 text-xs"
              >
                <span className="font-mono">{code}</span>
                <span className="text-[color:var(--fulkro-muted)]">
                  {ASSET_TYPE_LABELS[code] ?? code}
                </span>
                <span className="rounded-full bg-card px-2 py-0.5 font-semibold tabular-nums">
                  {count}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {total_assets === 0 ? (
        <div className="mt-5 rounded-md border bg-fulkro-ink-50 px-4 py-3 text-sm text-[color:var(--fulkro-muted)]">
          Marcos aun no ha cargado el inventario MAGERIT. Te
          notificaremos cuando puedas revisarlo.
        </div>
      ) : ready_for_validation_sign && !last_signed_at ? (
        <div className="mt-5 rounded-md border border-fulkro-success/30 bg-fulkro-success/10 px-4 py-3 text-sm text-fulkro-success">
          ✓ Has revisado todos los activos · puedes validar el inventario
          MAGERIT.
        </div>
      ) : (
        <div className="mt-5 rounded-md border bg-fulkro-ink-50 px-4 py-3 text-sm text-[color:var(--fulkro-muted)]">
          Completa la revisión de los {pending_review_count} activos
          pendientes antes de validar.
        </div>
      )}

      {last_signed_at && (
        <p className="mt-3 text-xs text-[color:var(--fulkro-muted)]">
          Última versión validada:{" "}
          {new Date(last_signed_at).toLocaleString("es-ES")}
        </p>
      )}
    </div>
  );
}


interface StatBoxProps {
  label: string;
  value: number;
  variant: "success" | "muted" | "warning" | "info";
}


function StatBox({ label, value, variant }: StatBoxProps) {
  const colorClass = {
    success: "text-fulkro-success",
    muted: "text-[color:var(--fulkro-muted)]",
    warning: "text-fulkro-warning",
    info: "text-fulkro-info",
  }[variant];
  return (
    <div className="rounded-md border bg-fulkro-ink-50/50 px-3 py-2">
      <dt className="text-xs text-[color:var(--fulkro-muted)]">{label}</dt>
      <dd className={`text-2xl font-semibold tabular-nums ${colorClass}`.trim()}>
        {value}
      </dd>
    </div>
  );
}
