"use client";

/**
 * MeetingLivePanel — display SSE feed A18 insight progresivo
 * (sub-bloque 7.B.6 FASE 7).
 *
 * Consume hook useMeetingSSE + render:
 *   - Status banner (idle / connecting / streaming / done / error)
 *   - Progress markers (thinking / validating)
 *   - Insight final (cards: categoría / madurez / horas / riesgos /
 *     quick_wins / preguntas_pendientes)
 *   - Done métricas (latency_ms + tokens)
 *
 * Props onAttachOutputs callback opcional: cuando llega event done
 * con insight válido, parent puede persistir en
 * meeting.outputs_agente_18 vía complete_meeting o patch.
 */
import { Activity, AlertCircle, Sparkles } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMeetingSSE,
  type SSEStatus,
} from "@/hooks/useMeetingSSE";
import type { SSEEvent } from "@/lib/admin-meetings/schemas";

interface MeetingLivePanelProps {
  meetingId: string;
  notesMarkdown: string;
  disabled?: boolean;
  onInsight?: (insight: Record<string, unknown>) => void;
}

const STATUS_LABELS: Record<SSEStatus, string> = {
  idle: "Inactivo",
  connecting: "Conectando…",
  streaming: "Recibiendo insight…",
  done: "Completado",
  error: "Error",
};

const STATUS_VARIANTS: Record<
  SSEStatus,
  "default" | "secondary" | "danger"
> = {
  idle: "secondary",
  connecting: "secondary",
  streaming: "default",
  done: "default",
  error: "danger",
};

/**
 * Heurística split notas markdown → 6 bloques A-F.
 *
 * Backend A18 espera dict {A_contexto, B_informacion, ..., F_equipo}.
 * Si Marcos usa headings markdown # A · ## A · etc, splitear por
 * heading. Sino, fallback: notes completas en A_contexto.
 */
function splitNotesIntoBlocks(notes: string): Record<string, string> {
  const blocks: Record<string, string> = {
    A_contexto: "",
    B_informacion: "",
    C_madurez: "",
    D_plazos: "",
    E_presupuesto: "",
    F_equipo: "",
  };
  if (!notes.trim()) return blocks;

  // Pattern simple: "## A " o "# A " comienza un bloque
  const lines = notes.split("\n");
  let current: keyof typeof blocks = "A_contexto";
  for (const line of lines) {
    const headingMatch = line.match(/^#+\s*([A-F])\b/i);
    if (headingMatch) {
      const letter = headingMatch[1].toUpperCase();
      const map: Record<string, keyof typeof blocks> = {
        A: "A_contexto",
        B: "B_informacion",
        C: "C_madurez",
        D: "D_plazos",
        E: "E_presupuesto",
        F: "F_equipo",
      };
      current = map[letter] ?? current;
      continue;
    }
    blocks[current] += line + "\n";
  }
  // Si solo A_contexto tiene content, replicar todas notas allí (heuristic
  // fallback para notas sin headings A-F)
  const otherBlocksEmpty = Object.entries(blocks)
    .filter(([k]) => k !== "A_contexto")
    .every(([, v]) => v.trim() === "");
  if (otherBlocksEmpty && blocks.A_contexto.trim() === "" && notes.trim()) {
    blocks.A_contexto = notes;
  }
  return blocks;
}

function findInsight(events: SSEEvent[]): Record<string, unknown> | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type === "insight") return e.data;
  }
  return null;
}

function findDone(events: SSEEvent[]): Extract<SSEEvent, { type: "done" }> | null {
  for (const e of events) {
    if (e.type === "done") return e;
  }
  return null;
}

function findProgress(events: SSEEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.type === "progress") return e.phase;
  }
  return null;
}

export function MeetingLivePanel({
  meetingId,
  notesMarkdown,
  disabled = false,
  onInsight,
}: MeetingLivePanelProps) {
  const { events, status, errorMsg, start, stop } = useMeetingSSE();

  const insight = findInsight(events);
  const done = findDone(events);
  const progress = findProgress(events);

  const insightSerialized = insight ? JSON.stringify(insight) : null;
  React.useEffect(() => {
    if (status === "done" && insight && onInsight) {
      onInsight(insight);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, insightSerialized]);

  async function handleAnalyze() {
    const blocks = splitNotesIntoBlocks(notesMarkdown);
    const filled = Object.entries(blocks)
      .filter(([, v]) => v.trim().length > 0)
      .map(([k]) => k.split("_")[0].toUpperCase());
    await start({
      blocks,
      blocks_filled: filled,
      meeting_id: meetingId,
    });
  }

  return (
    <div className="flex h-full min-h-64 flex-col rounded-md border border-fulkro-ink-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-fulkro-primary-600" />
          <h2 className="text-sm font-semibold text-fulkro-primary-700">
            Panel A18 — Insight live
          </h2>
        </div>
        <Badge variant={STATUS_VARIANTS[status]}>
          {STATUS_LABELS[status]}
        </Badge>
      </div>

      <div className="flex gap-2">
        <Button
          type="button"
          size="sm"
          onClick={handleAnalyze}
          disabled={
            disabled ||
            status === "connecting" ||
            status === "streaming" ||
            !notesMarkdown.trim()
          }
        >
          <Activity size={14} className="mr-1" />
          {status === "streaming" ? "Analizando…" : "Analizar notas (A18)"}
        </Button>
        {(status === "streaming" || status === "connecting") && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={stop}
          >
            Cancelar
          </Button>
        )}
      </div>

      {errorMsg && (
        <div
          className="mt-3 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700"
          role="alert"
        >
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {progress && (status === "streaming" || status === "connecting") && (
        <p className="mt-3 text-xs italic text-fulkro-ink-500">
          {progress === "thinking" && "A18 procesando bloques A-F…"}
          {progress === "validating_schema" && "Validando schema JSON…"}
        </p>
      )}

      <div className="mt-3 flex-1 overflow-y-auto">
        {status === "idle" && (
          <p className="text-sm text-fulkro-ink-500">
            Pulsa <strong>Analizar notas</strong> para invocar A18 con
            las notas actuales. SSE stream emite progreso + insight final.
          </p>
        )}
        {status === "connecting" && (
          <Skeleton className="h-32 w-full" />
        )}
        {insight && (
          <article className="space-y-3 text-sm">
            {typeof insight.categoria_ens === "string" && (
              <div className="rounded bg-fulkro-primary-50 p-2">
                <p className="text-xs font-semibold text-fulkro-primary-700">
                  Categoría ENS
                </p>
                <p className="text-fulkro-ink-700">
                  {String(insight.categoria_ens)}
                  {typeof insight.confianza_categoria === "number" && (
                    <span className="ml-2 text-xs text-fulkro-ink-500">
                      ({insight.confianza_categoria}% confianza)
                    </span>
                  )}
                </p>
              </div>
            )}
            {typeof insight.madurez_actual === "string" && (
              <div className="rounded bg-fulkro-ink-50 p-2">
                <p className="text-xs font-semibold text-fulkro-ink-700">
                  Madurez actual
                </p>
                <p>
                  {String(insight.madurez_actual)}
                  {typeof insight.horas_marcos_estimadas === "number" && (
                    <span className="ml-2 text-xs text-fulkro-ink-500">
                      · {insight.horas_marcos_estimadas} h estimadas
                    </span>
                  )}
                </p>
              </div>
            )}
            {Array.isArray(insight.riesgos_detectados) &&
              insight.riesgos_detectados.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-fulkro-ink-700">
                    Riesgos detectados ({insight.riesgos_detectados.length})
                  </p>
                  <ul className="ml-4 list-disc text-xs">
                    {insight.riesgos_detectados.slice(0, 5).map((r, i) => (
                      <li key={i} className="text-fulkro-ink-600">
                        {(r as Record<string, unknown>).title as string ?? JSON.stringify(r)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            {Array.isArray(insight.quick_wins_sugeridas) &&
              insight.quick_wins_sugeridas.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-fulkro-ink-700">
                    Quick wins sugeridas ({insight.quick_wins_sugeridas.length})
                  </p>
                  <ul className="ml-4 list-disc text-xs">
                    {insight.quick_wins_sugeridas.slice(0, 5).map((q, i) => (
                      <li key={i} className="text-fulkro-ink-600">
                        {(q as Record<string, unknown>).title as string ?? JSON.stringify(q)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            {Array.isArray(insight.preguntas_pendientes) &&
              insight.preguntas_pendientes.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-fulkro-ink-700">
                    Preguntas pendientes ({insight.preguntas_pendientes.length})
                  </p>
                  <ul className="ml-4 list-disc text-xs">
                    {insight.preguntas_pendientes.slice(0, 5).map((p, i) => (
                      <li key={i} className="text-fulkro-ink-600">
                        {(p as Record<string, unknown>).question as string ??
                          JSON.stringify(p)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
          </article>
        )}
      </div>

      {done && (
        <div className="mt-3 border-t border-fulkro-ink-100 pt-2 text-xs text-fulkro-ink-500">
          {done.latency_ms}ms ·{" "}
          {done.tokens_input ?? "?"} in / {done.tokens_output ?? "?"} out tokens
          {done.fallback_used && (
            <span className="ml-2 text-amber-600">· fallback aplicado</span>
          )}
        </div>
      )}
    </div>
  );
}
