"use client";

/**
 * AssetRow · row activo MAGERIT en lista cliente review.
 *
 * Inline expand RICHER (pattern atom 5.3.E):
 * 1. Info básica · code · tipo + nombre
 * 2. Valoración DICAT · 5 chips (D · I · C · A · T) · escala 0-10
 * 3. Valores acumulados (post-propagación dependencias) · admin computed
 * 4. Owner + descripción
 * 5. Tu nota previa cliente (si existe)
 * 6. Review actions cliente (revisada_ok · con_pregunta · suggest_change)
 *
 * SAN-E v3.MB-5.4 · Q5.3 cliente NO edita valoración (admin owns).
 */
import { useState } from "react";

import type {
  AssetReviewAction,
  MageritAssetClientView,
} from "@/lib/api/magerit";


const ASSET_TYPE_LABELS: Record<string, string> = {
  S: "Servicio",
  D: "Datos / Información",
  SW: "Software / Aplicaciones",
  HW: "Hardware / Equipamiento",
  COM: "Comunicaciones",
  SI: "Soportes",
  AUX: "Equipamiento auxiliar",
  L: "Instalaciones",
  P: "Personal",
};


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


interface Props {
  asset: MageritAssetClientView;
  onReview: (
    assetId: string,
    action: AssetReviewAction,
    note?: string,
  ) => Promise<void>;
}


function DicatChip({
  letter,
  label,
  value,
  accumulated,
}: {
  letter: string;
  label: string;
  value: number | null;
  accumulated: number | null;
}) {
  const hasValue = value !== null;
  return (
    <div className="rounded border bg-card px-2 py-1.5">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-sm font-bold">{letter}</span>
        <span
          className={`text-xs tabular-nums ${
            hasValue ? "font-semibold" : "text-[color:var(--fulkro-muted)]"
          }`.trim()}
        >
          {hasValue ? value : "—"}
        </span>
      </div>
      <div className="text-[9px] uppercase tracking-wide text-[color:var(--fulkro-muted)]">
        {label}
      </div>
      {accumulated !== null && (
        <div className="text-[10px] text-[color:var(--fulkro-muted)]">
          acum. {accumulated.toFixed(2)}
        </div>
      )}
    </div>
  );
}


export function AssetRow({ asset, onReview }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [pendingAction, setPendingAction] =
    useState<AssetReviewAction | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const status = asset.client_review_status;
  const statusInfo = status ? STATUS_LABELS[status] : null;

  const handleAction = async (action: AssetReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(asset.id, action);
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(asset.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) return;
    setSubmitting(true);
    try {
      await onReview(asset.id, pendingAction, note);
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
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-xs text-[color:var(--fulkro-muted)]">
              {asset.code}
            </span>
            <span className="text-xs uppercase text-[color:var(--fulkro-muted)]">
              {ASSET_TYPE_LABELS[asset.asset_type_code] ?? asset.asset_type_code}
            </span>
            {statusInfo && (
              <span
                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${statusInfo.cls}`.trim()}
              >
                {statusInfo.label}
              </span>
            )}
          </div>
          <h3 className="mt-1 text-sm font-medium leading-snug">
            {asset.name}
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
          {/* Section 1 · Info básica */}
          {(asset.description || asset.owner) && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                Activo
              </h4>
              {asset.description && (
                <p className="leading-relaxed text-[color:var(--fulkro-title)]">
                  {asset.description}
                </p>
              )}
              {asset.owner && (
                <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
                  Responsable: <span className="font-medium">{asset.owner}</span>
                </p>
              )}
            </section>
          )}

          {/* Section 2 · Valoración DICAT 5 chips */}
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
              Valoración DICAT (escala 0-10 · admin asigna · cliente VE)
            </h4>
            <div className="grid grid-cols-5 gap-2">
              <DicatChip
                letter="D"
                label="Disponibilidad"
                value={asset.value_d}
                accumulated={asset.accumulated_d}
              />
              <DicatChip
                letter="I"
                label="Integridad"
                value={asset.value_i}
                accumulated={asset.accumulated_i}
              />
              <DicatChip
                letter="C"
                label="Confidencialidad"
                value={asset.value_c}
                accumulated={asset.accumulated_c}
              />
              <DicatChip
                letter="A"
                label="Autenticidad"
                value={asset.value_a}
                accumulated={asset.accumulated_a}
              />
              <DicatChip
                letter="T"
                label="Trazabilidad"
                value={asset.value_t}
                accumulated={asset.accumulated_t}
              />
            </div>
            <p className="mt-2 text-[10px] italic text-[color:var(--fulkro-muted)]">
              Valor base = nivel inherente · Valor acumulado = post-propagación
              de dependencias entre activos (computado por Marcos vía MAGERIT v3).
            </p>
          </section>

          {/* Section 3 · Tu nota previa cliente */}
          {asset.client_review_note && (
            <section>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                Tu nota previa
              </h4>
              <p className="rounded bg-fulkro-info/10 px-3 py-2 text-xs">
                {asset.client_review_note}
              </p>
            </section>
          )}
        </div>
      )}

      {pendingAction ? (
        <div className="mt-3 space-y-2">
          <label
            htmlFor={`mag-note-${asset.id}`}
            className="text-xs font-medium"
          >
            {pendingAction === "con_pregunta"
              ? "Tu pregunta para Marcos"
              : "Tu sugerencia de cambio"}
          </label>
          <textarea
            id={`mag-note-${asset.id}`}
            rows={3}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-fulkro-primary-700 focus:outline-none focus:ring-1 focus:ring-fulkro-primary-700"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              pendingAction === "con_pregunta"
                ? "Ej: ¿Por qué este servidor tiene Confidencialidad=10?"
                : "Ej: Propongo bajar Disponibilidad a 5 porque…"
            }
          />
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
