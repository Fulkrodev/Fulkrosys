"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clipboard,
  ClipboardCheck,
  Loader2,
  X,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  getRemediationGuide,
  markRemediationFixed,
} from "@/lib/api/public-portals";
import type {
  RemediationFindingCard,
  RemediationGuide,
  RemediationRetestResult,
} from "@/lib/public-portals-types";
import { cn } from "@/lib/utils";

interface Props {
  token: string;
  finding: RemediationFindingCard;
  onClose: () => void;
  onFixed: (result: RemediationRetestResult) => void;
}

export function RemediationGuideModal({
  token, finding, onClose, onFixed,
}: Props) {
  const [guide, setGuide] = React.useState<RemediationGuide | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [applying, setApplying] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getRemediationGuide(token, finding.finding_id)
      .then((g) => {
        if (!cancelled) {
          setGuide(g);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError((e as Error).message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, finding.finding_id]);

  async function handleFixed() {
    setApplying(true);
    try {
      const result = await markRemediationFixed(token, finding.finding_id);
      onFixed(result);
    } catch (e) {
      toast.error("No se pudo verificar la corrección", {
        description: (e as Error).message,
      });
    } finally {
      setApplying(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-title"
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-fulkro-primary-700/40 p-4"
      onClick={onClose}
    >
      <div
        className="my-8 w-full max-w-2xl rounded-lg border border-fulkro-ink-300/60 bg-white shadow-ink"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-fulkro-ink-300/40 p-4">
          <div>
            <h2 id="guide-title" className="text-base font-semibold text-fulkro-primary-700">
              Cómo solucionarlo
            </h2>
            <p className="mt-1 text-sm text-fulkro-ink-500">
              {finding.title}
            </p>
            <p className="font-mono text-[11px] text-fulkro-ink-500">
              {finding.host_port}
            </p>
          </div>
          <button
            type="button"
            aria-label="Cerrar"
            onClick={onClose}
            className="rounded p-1 text-fulkro-ink-500 hover:bg-fulkro-ink-100"
          >
            <X size={18} />
          </button>
        </div>

        {loading && (
          <div className="flex h-40 items-center justify-center gap-2 text-sm text-fulkro-ink-500">
            <Loader2 size={14} className="animate-spin" /> cargando guía…
          </div>
        )}

        {error && (
          <div className="p-4 text-sm text-fulkro-danger">
            No se pudo cargar la guía: {error}
          </div>
        )}

        {guide && !loading && (
          <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto p-4">
            <section>
              <h3 className="text-sm font-semibold text-fulkro-primary-700">
                ¿Qué supone?
              </h3>
              <p className="mt-1 text-sm text-fulkro-ink-700">
                {guide.guide.resumen_no_tecnico}
              </p>
            </section>

            <section className="rounded-md border border-fulkro-warning/40 bg-fulkro-warning/5 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle
                  size={14}
                  className="mt-0.5 shrink-0 text-fulkro-warning"
                />
                <div>
                  <h3 className="text-sm font-semibold text-fulkro-primary-700">
                    Riesgo real si no se corrige
                  </h3>
                  <p className="mt-1 text-sm text-fulkro-ink-700">
                    {guide.guide.riesgo_real}
                  </p>
                </div>
              </div>
            </section>

            <section className="flex flex-wrap gap-2 text-xs text-fulkro-ink-500">
              <span className="rounded bg-fulkro-ink-100 px-2 py-0.5">
                ⏱ {guide.guide.tiempo_estimado}
              </span>
              <span
                className={cn(
                  "rounded px-2 py-0.5",
                  guide.guide.requiere_reinicio
                    ? "bg-fulkro-warning/10 text-fulkro-warning"
                    : "bg-fulkro-success/10 text-fulkro-success",
                )}
              >
                {guide.guide.requiere_reinicio
                  ? "Requiere reinicio"
                  : "Sin reinicio"}
              </span>
              {guide.guide.requiere_ventana_mantenimiento && (
                <span className="rounded bg-fulkro-warning/10 px-2 py-0.5 text-fulkro-warning">
                  Ventana de mantenimiento recomendada
                </span>
              )}
            </section>

            <section>
              <h3 className="text-sm font-semibold text-fulkro-primary-700">
                Pasos ({guide.guide.pasos.length})
              </h3>
              <ol className="mt-2 flex flex-col gap-3">
                {guide.guide.pasos.map((p) => (
                  <li
                    key={p.paso}
                    className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/30 p-3"
                  >
                    <div className="flex items-start gap-2">
                      <span className="rounded-full bg-fulkro-primary-700 px-2 py-0.5 text-[11px] font-semibold text-white">
                        Paso {p.paso}
                      </span>
                      <p className="font-semibold text-fulkro-primary-700">
                        {p.titulo}
                      </p>
                    </div>
                    <p className="mt-1 text-sm text-fulkro-ink-700">
                      {p.explicacion}
                    </p>
                    <CopyableCommand
                      label="Comando"
                      command={p.comando}
                    />
                    <CopyableCommand
                      label="Verificación"
                      command={p.verificacion}
                    />
                  </li>
                ))}
              </ol>
            </section>
          </div>
        )}

        <div className="flex flex-col gap-2 border-t border-fulkro-ink-300/40 bg-fulkro-ink-100/40 p-4 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={onClose} disabled={applying}>
            Cerrar
          </Button>
          <Button
            onClick={handleFixed}
            disabled={loading || applying}
            className="gap-2"
          >
            {applying ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <CheckCircle2 size={14} />
            )}
            Ya lo he arreglado
          </Button>
        </div>
      </div>
    </div>
  );
}

function CopyableCommand({
  label,
  command,
}: {
  label: string;
  command: string;
}) {
  const [copied, setCopied] = React.useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("No se pudo copiar al portapapeles");
    }
  }

  return (
    <div className="mt-2">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
        {label}
      </p>
      <div className="mt-1 flex items-stretch gap-0 overflow-hidden rounded border border-fulkro-ink-300/60">
        <pre className="flex-1 overflow-x-auto bg-fulkro-primary-700 px-3 py-2 font-mono text-[12px] text-fulkro-ink-50">
          <code>{command}</code>
        </pre>
        <button
          type="button"
          onClick={copy}
          aria-label={`Copiar ${label.toLowerCase()}`}
          className="flex items-center gap-1 bg-fulkro-primary-700/90 px-3 text-[11px] font-semibold text-fulkro-ink-50 transition-colors hover:bg-fulkro-primary-500"
        >
          {copied ? <ClipboardCheck size={14} /> : <Clipboard size={14} />}
          {copied ? "Copiado" : "Copiar"}
        </button>
      </div>
    </div>
  );
}
