"use client";

/**
 * MeasureLensesPanel · Ola 4 cierre · LAS TRES LENTES de una medida ENS en la
 * fila SoA, desde la fuente correcta (la SoA + las evidencias · nada inventado):
 *
 *   1. estado_implementacion (declarado · lo que la SoA declara · ENAC mira)
 *   2. semáforo de evidencia (#20 · que la prueba que respalda está en regla)
 *   3. madurez CMM derivada (#21 · L0-L4 · CCN-STIC 804)
 *
 * Fetch-on-mount (se renderiza al expandir la fila / abrir el modal · NO N+1 en
 * la lista). Reusable admin (variant="admin"+projectId) y cliente (variant="cliente").
 */
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  getAdminMeasureCmm,
  getAdminMeasureStatus,
  getClienteMeasureCmm,
  getClienteMeasureStatus,
  type ControlStatusResult,
  type MeasureCmm,
  type Semaforo,
} from "@/lib/api/control-status";
import { DDA_ESTADO_LABELS } from "@/lib/api/dda";

const SEMAFORO_UI: Record<Semaforo, { label: string; cls: string }> = {
  verde: {
    label: "Evidencia en regla",
    cls: "border-green-500/40 bg-green-500/10 text-green-700",
  },
  amarillo: {
    label: "Evidencia pendiente",
    cls: "border-amber-500/40 bg-amber-500/10 text-amber-700",
  },
  rojo: {
    label: "Evidencia con incidencia",
    cls: "border-red-500/40 bg-red-500/10 text-red-700",
  },
  no_aplica: {
    label: "No aplica",
    cls: "border-border bg-muted text-muted-foreground",
  },
};

interface Props {
  variant: "admin" | "cliente";
  measureCode: string;
  /** Lente 1 · estado_implementacion ya disponible en la fila (declarado). */
  estadoImplementacion: string | null;
  /** Requerido para variant="admin". */
  projectId?: string;
}

export function MeasureLensesPanel({
  variant,
  measureCode,
  estadoImplementacion,
  projectId,
}: Props) {
  const [status, setStatus] = useState<ControlStatusResult | null>(null);
  const [cmm, setCmm] = useState<MeasureCmm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);

    const statusP =
      variant === "admin" && projectId
        ? getAdminMeasureStatus(projectId, measureCode)
        : getClienteMeasureStatus(measureCode);
    const cmmP =
      variant === "admin" && projectId
        ? getAdminMeasureCmm(projectId, measureCode)
        : getClienteMeasureCmm(measureCode);

    Promise.all([statusP, cmmP])
      .then(([s, c]) => {
        if (!active) return;
        setStatus(s);
        setCmm(c);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [variant, measureCode, projectId]);

  const estadoLabel = estadoImplementacion
    ? DDA_ESTADO_LABELS[estadoImplementacion] ?? estadoImplementacion
    : "—";

  const sem = status ? SEMAFORO_UI[status.semaforo] : null;

  return (
    <section
      className="rounded-md border bg-card p-3 space-y-2.5"
      data-testid={`measure-lenses-${measureCode}`}
    >
      <h4 className="text-xs font-semibold uppercase tracking-wide text-foreground/55">
        Estado de la medida · 3 lentes
      </h4>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
        {/* Lente 1 · conformidad declarada (SoA) */}
        <div className="rounded border bg-background px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-foreground/45">
            Declarado (SoA)
          </div>
          <div className="text-[12px] font-medium" data-testid="lens-estado">
            {estadoLabel}
          </div>
        </div>

        {/* Lente 2 · semáforo de evidencia (#20) */}
        <div className="rounded border bg-background px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-foreground/45">
            Evidencia (#20)
          </div>
          {loading ? (
            <div className="flex items-center gap-1 text-[11px] text-foreground/45">
              <Loader2 className="size-3 animate-spin" /> …
            </div>
          ) : error ? (
            <div className="text-[11px] text-foreground/45">No disponible</div>
          ) : sem ? (
            <span
              className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium ${sem.cls}`}
              data-testid="lens-semaforo"
              data-semaforo={status?.semaforo}
            >
              {sem.label}
            </span>
          ) : (
            <div className="text-[11px] text-foreground/45">—</div>
          )}
        </div>

        {/* Lente 3 · madurez CMM derivada (#21) */}
        <div className="rounded border bg-background px-2 py-1.5">
          <div className="text-[9px] uppercase tracking-wide text-foreground/45">
            Madurez (CMM)
          </div>
          {loading ? (
            <div className="flex items-center gap-1 text-[11px] text-foreground/45">
              <Loader2 className="size-3 animate-spin" /> …
            </div>
          ) : error ? (
            <div className="text-[11px] text-foreground/45">No disponible</div>
          ) : cmm && cmm.cmm_level ? (
            <div className="text-[12px] font-medium" data-testid="lens-cmm">
              {cmm.cmm_level} · {cmm.cmm_label}
              {cmm.target_level && (
                <span className="ml-1 text-[10px] font-normal text-foreground/45">
                  (objetivo {cmm.target_level})
                </span>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-foreground/45">No aplica</div>
          )}
        </div>
      </div>

      {/* Por qué no está verde (R29 friendly · cliente · admin technical) */}
      {!loading && !error && status && status.missing_reasons.length > 0 && (
        <ul
          className="list-disc space-y-0.5 pl-4 text-[11px] text-foreground/65"
          data-testid="lens-missing-reasons"
        >
          {status.missing_reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
