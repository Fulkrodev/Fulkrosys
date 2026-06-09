"use client";

/**
 * DdaMeasureRow · row de medida ENS DdA en lista cliente.
 *
 * Mobile-first: tarjeta full-width con código + familia · nombre · status
 * actual · acciones quick (Aceptar · Pregunta · Sugerir cambio).
 *
 * SAN-E v3.MB-5.3.A · review actions cliente.
 * SAN-E v3.MB-5.3.E · expand RICHER (audit ENAC compliance · cliente VE
 *   descripción + requisito_base + ccn_stic_ref + tier + dimensiones +
 *   evidencias linked + observaciones admin pre-firma · 0 deuda técnica).
 */
import { useState } from "react";

import { AgentEnrichComposer } from "@/components/client-portal/inline-agents/AgentEnrichComposer";
import { MeasureLensesPanel } from "@/components/m04_gap/MeasureLensesPanel";
import type {
  DdaClientEntryView,
  DdaClientReviewAction,
} from "@/lib/api/dda";


function InfoChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border bg-card px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-[color:var(--fulkro-muted)]">
        {label}
      </div>
      <div className="text-[11px] font-medium">{value}</div>
    </div>
  );
}

interface Props {
  entry: DdaClientEntryView;
  onReview: (
    entryId: string,
    action: DdaClientReviewAction,
    note?: string,
  ) => Promise<void>;
}

const STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  revisada_ok: {
    label: "Revisada",
    cls: "bg-fulkro-success/15 text-fulkro-success border-fulkro-success/30",
  },
  con_pregunta: {
    label: "Pregunta",
    cls: "bg-fulkro-warning/15 text-fulkro-warning border-fulkro-warning/30",
  },
  suggest_change: {
    label: "Sugerencia",
    cls: "bg-fulkro-info/15 text-fulkro-info border-fulkro-info/30",
  },
};


export function DdaMeasureRow({ entry, onReview }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [pendingAction, setPendingAction] =
    useState<DdaClientReviewAction | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const status = entry.client_review_status;
  const statusInfo = status ? STATUS_LABELS[status] : null;

  const handleAction = async (action: DdaClientReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(entry.id, action);
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(entry.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) return;
    setSubmitting(true);
    try {
      await onReview(entry.id, pendingAction, note);
      setPendingAction(null);
      setNote("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <li className="rounded-md border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-xs text-[color:var(--fulkro-muted)]">
              {entry.measure_codigo}
            </span>
            {entry.measure_familia && (
              <span className="text-xs uppercase text-[color:var(--fulkro-muted)]">
                {entry.measure_familia}
              </span>
            )}
            {statusInfo && (
              <span
                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${statusInfo.cls}`.trim()}
              >
                {statusInfo.label}
              </span>
            )}
          </div>
          <h3 className="mt-1 text-sm font-medium leading-snug">
            {entry.measure_nombre}
          </h3>
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-fulkro-primary-700 underline-offset-2 hover:underline"
        >
          {expanded ? "Ocultar detalle" : "Ver detalle"}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 space-y-5 border-t pt-4 text-sm">
          {/* Ola 4 cierre · las 3 lentes de la medida (declarado + evidencia + madurez) */}
          <MeasureLensesPanel
            variant="cliente"
            measureCode={entry.measure_codigo}
            estadoImplementacion={entry.estado_implementacion}
          />

          {/* Section 1 · Descripcion + requisito_base + ccn-stic ref */}
          <section>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Descripcion de la medida
            </h4>
            {entry.measure_descripcion && (
              <p className="leading-relaxed text-[color:var(--fulkro-title)]">
                {entry.measure_descripcion}
              </p>
            )}
            {entry.requisito_base && (
              <p className="mt-2 rounded bg-fulkro-ink-50 px-3 py-2 text-xs italic">
                <span className="font-medium not-italic">Requisito base:</span>{" "}
                {entry.requisito_base}
              </p>
            )}
            {entry.ccn_stic_reference && (
              <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
                Referencia CCN-STIC:{" "}
                <span className="font-mono">{entry.ccn_stic_reference}</span>
              </p>
            )}
          </section>

          {/* Section 2 · Aplicabilidad + justificacion admin (cliente VE · NO edit) */}
          <section>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Como aplica esta medida en tu proyecto
            </h4>
            <div className="rounded-md border bg-fulkro-ink-50/60 px-3 py-2.5">
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs">
                <span className="font-medium text-[color:var(--fulkro-title)]">
                  Aplicabilidad:
                </span>
                <span className="rounded bg-card px-2 py-0.5 font-mono text-[11px]">
                  {entry.aplicabilidad ?? "—"}
                </span>
                {entry.estado_implementacion && (
                  <>
                    <span className="font-medium text-[color:var(--fulkro-title)]">
                      Estado:
                    </span>
                    <span className="rounded bg-card px-2 py-0.5 text-[11px]">
                      {entry.estado_implementacion}
                    </span>
                  </>
                )}
                <span className="text-[10px] italic text-[color:var(--fulkro-muted)]">
                  (asignado por Marcos · cliente revisa · NO edita)
                </span>
              </div>
              {entry.justificacion_no_aplica ? (
                <p className="whitespace-pre-wrap text-xs leading-relaxed">
                  <span className="font-medium not-italic">Justificacion:</span>{" "}
                  {entry.justificacion_no_aplica}
                </p>
              ) : (
                <p className="text-xs italic text-[color:var(--fulkro-muted)]">
                  Sin justificacion adicional · medida aplica per defecto.
                </p>
              )}
              {entry.observaciones && (
                <p className="mt-1.5 text-xs italic text-[color:var(--fulkro-muted)]">
                  <span className="font-medium not-italic">
                    Observaciones admin:
                  </span>{" "}
                  {entry.observaciones}
                </p>
              )}
            </div>
          </section>

          {/* Section 3 · Evidencias adjuntas */}
          <section>
            <h4 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              <span>Evidencias adjuntas</span>
              <span className="rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-[11px] tabular-nums">
                {entry.evidence_count}
              </span>
            </h4>
            {entry.evidence_list.length > 0 ? (
              <ul className="space-y-1.5">
                {entry.evidence_list.map((ev) => (
                  <li
                    key={ev.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded border bg-card px-3 py-2 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">
                        {ev.fichero_nombre_original ?? ev.nombre_tipo ?? "Evidencia"}
                      </p>
                      <p className="text-[10px] text-[color:var(--fulkro-muted)]">
                        {ev.nombre_tipo ?? "—"}
                        {ev.fecha_evidencia && (
                          <> · {new Date(ev.fecha_evidencia).toLocaleDateString("es-ES")}</>
                        )}
                        {ev.vigente ? (
                          <span className="ml-1 rounded bg-fulkro-success/15 px-1 text-fulkro-success">
                            vigente
                          </span>
                        ) : (
                          <span className="ml-1 rounded bg-fulkro-warning/15 px-1 text-fulkro-warning">
                            sin vigencia
                          </span>
                        )}
                      </p>
                    </div>
                    <a
                      href={`/api/v1/evidence/${ev.id}/download`}
                      className="rounded border px-2 py-1 text-[11px] font-medium hover:bg-fulkro-ink-50"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Descargar
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded border bg-fulkro-warning/5 px-3 py-2 text-xs italic text-[color:var(--fulkro-muted)]">
                Sin evidencias adjuntas todavia · contacta a Marcos si la
                medida requiere documentacion soporte.
              </p>
            )}
          </section>

          {/* Section 4 · ENS context educational */}
          <section className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <InfoChip
              label="Tier requerido"
              value={
                entry.tier_required_for.length > 0
                  ? entry.tier_required_for.join(" · ")
                  : "—"
              }
            />
            <InfoChip
              label="Categoria minima"
              value={entry.categoria_minima ?? "—"}
            />
            <InfoChip label="Familia" value={entry.measure_familia ?? "—"} />
            <InfoChip
              label="Dimensiones DICAT"
              value={
                entry.dimensiones_aplicables &&
                entry.dimensiones_aplicables.length > 0
                  ? entry.dimensiones_aplicables.join(" · ")
                  : "Todas"
              }
            />
          </section>

          {/* Section 5 · Tu nota previa cliente */}
          {entry.client_review_note && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                Tu nota previa
              </h4>
              <p className="rounded bg-fulkro-info/10 px-3 py-2 text-xs">
                {entry.client_review_note}
              </p>
            </section>
          )}

          {entry.aprobado_por && (
            <p className="text-[11px] italic text-[color:var(--fulkro-muted)]">
              Aprobado por: {entry.aprobado_por}
              {entry.fecha_aprobacion && (
                <>
                  {" "}
                  ·{" "}
                  {new Date(entry.fecha_aprobacion).toLocaleDateString("es-ES")}
                </>
              )}
            </p>
          )}
        </div>
      )}

      {pendingAction ? (
        <div className="mt-3 space-y-2">
          <label
            htmlFor={`note-${entry.id}`}
            className="text-xs font-medium"
          >
            {pendingAction === "con_pregunta"
              ? "Tu pregunta para Marcos"
              : "Tu sugerencia de cambio"}
          </label>
          <textarea
            id={`note-${entry.id}`}
            rows={3}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-fulkro-primary-700 focus:outline-none focus:ring-1 focus:ring-fulkro-primary-700"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              pendingAction === "con_pregunta"
                ? "Ej: ¿Esta medida aplica si solo tenemos un cloud SaaS sin servidores propios?"
                : "Ej: Propongo añadir una salvaguarda compensatoria descrita en…"
            }
          />
          {pendingAction === "suggest_change" && (
            <AgentEnrichComposer
              slug="a31_enriquecedor_dda"
              currentValue={note}
              prompt="Reescribe esta sugerencia de cambio con contexto CCN-STIC + tono profesional, 80-150 palabras."
              onApply={(enriched) => setNote(enriched)}
              label="Enriquecer sugerencia con IA"
            />
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setPendingAction(null);
                setNote("");
              }}
              className="rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-fulkro-ink-50"
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => void submitWithNote()}
              disabled={submitting || note.trim().length < 5}
              className="rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-fulkro-primary-800 disabled:opacity-50"
            >
              {submitting ? "Guardando…" : "Enviar"}
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void handleAction("revisada_ok")}
            disabled={submitting || status === "revisada_ok"}
            className="rounded-md bg-fulkro-primary-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-fulkro-primary-800 disabled:opacity-50"
          >
            {status === "revisada_ok" ? "✓ Revisada" : "Aceptar · marcar revisada"}
          </button>
          <button
            type="button"
            onClick={() => void handleAction("con_pregunta")}
            disabled={submitting}
            className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-fulkro-warning/10"
          >
            Tengo una pregunta
          </button>
          <button
            type="button"
            onClick={() => void handleAction("suggest_change")}
            disabled={submitting}
            className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-fulkro-info/10"
          >
            Sugerir cambio
          </button>
        </div>
      )}
    </li>
  );
}
