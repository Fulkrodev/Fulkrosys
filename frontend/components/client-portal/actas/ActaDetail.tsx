"use client";

/**
 * Acta detail · 28 cols pretty render + review actions MixinA · MB-6 atom 5.
 */
import { useState } from "react";
import {
  CheckCircle2,
  FileText,
  HelpCircle,
  Lightbulb,
  Loader2,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { ActaSignButton } from "@/components/client-portal/actas/ActaSignButton";
import { SubtypeBadge } from "@/components/client-portal/actas/ActaCard";
import { AgentSummaryDrawer } from "@/components/client-portal/inline-agents/AgentSummaryDrawer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  type ActaClientView,
  type ActaReviewAction,
} from "@/lib/api/actas";

interface Props {
  acta: ActaClientView;
  onReview: (
    meetingId: string,
    action: ActaReviewAction,
    note?: string,
  ) => Promise<void>;
  onSigningComplete: () => void;
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-ES");
  } catch {
    return iso;
  }
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES");
  } catch {
    return iso;
  }
}

export function ActaDetail({ acta, onReview, onSigningComplete }: Props) {
  const [pendingAction, setPendingAction] = useState<ActaReviewAction | null>(
    null,
  );
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(false);

  const reviewed = acta.client_review_status === "revisada_ok";
  const signed = acta.client_signing_intent_id != null;

  const handleAction = async (action: ActaReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(acta.id, action);
        toast.success("Acta marcada revisada");
      } catch {
        // toast viene del hook
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(acta.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) {
      toast.error("La nota debe tener al menos 5 caracteres");
      return;
    }
    setSubmitting(true);
    try {
      await onReview(acta.id, pendingAction, note.trim());
      toast.success("Review actualizado");
      setPendingAction(null);
    } catch {
      // toast viene del hook
    } finally {
      setSubmitting(false);
    }
  };

  const actaContext = [
    acta.titulo ? `Título: ${acta.titulo}` : null,
    acta.codigo ? `Código: ${acta.codigo}` : null,
    acta.fecha ? `Fecha: ${acta.fecha}` : null,
    acta.orden_del_dia?.length
      ? `Orden del día: ${acta.orden_del_dia
          .map((o) => o.titulo ?? o.punto ?? "")
          .filter(Boolean)
          .join("; ")}`
      : null,
    acta.acuerdos_jsonb?.length
      ? `Acuerdos: ${acta.acuerdos_jsonb
          .map((a) => a.descripcion ?? "")
          .filter(Boolean)
          .join("; ")}`
      : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div data-testid="acta-detail" className="space-y-4">
      <div className="flex items-center justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSummaryOpen(true)}
          data-testid="acta-ai-summary-trigger"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span className="ml-1.5">Resumen ejecutivo IA</span>
        </Button>
      </div>

      <AgentSummaryDrawer
        open={summaryOpen}
        onClose={() => setSummaryOpen(false)}
        slug="a18_reunion_summary"
        title="Resumen ejecutivo IA"
        prompt={
          "Genera un resumen ejecutivo en 3-5 viñetas del acta adjunta. "
          + "Estructura: decisiones · responsables · próximos pasos · "
          + "riesgos detectados. Tono ejecutivo claro."
        }
        extraContext={actaContext}
      />

      <Card className="p-5">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="text-xs uppercase tracking-wide font-semibold text-fulkro-primary-700">
            {acta.acta_subtype_label || "Acta"}
          </div>
          <SubtypeBadge subtype={acta.acta_subtype} />
        </div>
        <h2 className="text-xl font-bold text-fulkro-ink-800 mt-1">
          {acta.titulo ?? acta.codigo ?? "—"}
        </h2>
        <div className="text-sm text-fulkro-ink-600 mt-1">
          {acta.codigo ?? ""} · {fmtDate(acta.fecha)}
          {acta.lugar && ` · ${acta.lugar}`}
        </div>
        <div className="text-xs text-fulkro-ink-500 mt-2 grid grid-cols-2 gap-2">
          {acta.presidente && (
            <div>
              <span className="font-semibold">Presidente:</span>{" "}
              {acta.presidente}
            </div>
          )}
          {acta.secretario && (
            <div>
              <span className="font-semibold">Secretario:</span>{" "}
              {acta.secretario}
            </div>
          )}
        </div>
      </Card>

      {acta.asistentes && acta.asistentes.length > 0 && (
        <Card className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Users className="h-4 w-4 text-fulkro-primary-700" aria-hidden />
            <h3 className="font-semibold text-sm text-fulkro-ink-800">
              Asistentes ({acta.asistentes.length})
            </h3>
          </div>
          <ul className="space-y-1.5 text-sm">
            {acta.asistentes.map((a, i) => (
              <li key={i} className="text-fulkro-ink-700">
                <span className="font-medium">{a.nombre ?? "—"}</span>
                {a.cargo && (
                  <span className="text-fulkro-ink-500"> · {a.cargo}</span>
                )}
                {a.organizacion && (
                  <span className="text-fulkro-ink-500">
                    {" "}
                    · {a.organizacion}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {acta.orden_del_dia && acta.orden_del_dia.length > 0 && (
        <Card className="p-5">
          <h3 className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Orden del día
          </h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-fulkro-ink-700">
            {acta.orden_del_dia.map((o, i) => (
              <li key={i}>
                {o.titulo ?? o.punto ?? "—"}
                {o.ponente && (
                  <span className="text-fulkro-ink-500"> · {o.ponente}</span>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {acta.acuerdos_jsonb && acta.acuerdos_jsonb.length > 0 && (
        <Card className="p-5">
          <h3 className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Acuerdos ({acta.acuerdos_jsonb.length})
          </h3>
          <ol className="space-y-2 text-sm">
            {acta.acuerdos_jsonb.map((a, i) => (
              <li
                key={i}
                className="border-l-2 border-fulkro-primary-200 pl-3 py-1"
              >
                <div className="font-medium text-fulkro-ink-800">
                  {a.numero != null ? `#${a.numero} · ` : ""}
                  {a.descripcion ?? "—"}
                </div>
                {(a.owner || a.fecha_limite) && (
                  <div className="text-xs text-fulkro-ink-500 mt-0.5">
                    {a.owner && `Owner: ${a.owner}`}
                    {a.fecha_limite && ` · Fecha: ${fmtDate(a.fecha_limite)}`}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {acta.proximos_pasos && acta.proximos_pasos.length > 0 && (
        <Card className="p-5">
          <h3 className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Próximos pasos
          </h3>
          <ul className="space-y-1 text-sm list-disc list-inside text-fulkro-ink-700">
            {acta.proximos_pasos.map((p, i) => (
              <li key={i}>
                {p.descripcion ?? "—"}
                {p.owner && (
                  <span className="text-fulkro-ink-500"> · {p.owner}</span>
                )}
                {p.fecha_limite && (
                  <span className="text-fulkro-ink-500">
                    {" "}
                    · {fmtDate(p.fecha_limite)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {acta.notas_libres && (
        <Card className="p-5">
          <h3 className="font-semibold text-sm text-fulkro-ink-800 mb-2">
            Notas
          </h3>
          <p className="text-sm text-fulkro-ink-700 whitespace-pre-wrap">
            {acta.notas_libres}
          </p>
        </Card>
      )}

      {(acta.hash_sha256 || acta.firmas?.length) && (
        <Card className="p-5 bg-fulkro-ink-50">
          <div className="flex items-center gap-2 mb-3">
            <FileText
              className="h-4 w-4 text-fulkro-ink-600"
              aria-hidden
            />
            <h3 className="font-semibold text-sm text-fulkro-ink-800">
              Trazabilidad
            </h3>
          </div>
          {acta.hash_sha256 && (
            <div className="text-xs font-mono text-fulkro-ink-600 break-all mb-2">
              <span className="font-semibold uppercase tracking-wide">
                SHA-256:
              </span>{" "}
              {acta.hash_sha256}
            </div>
          )}
          {acta.firmas && acta.firmas.length > 0 && (
            <div className="text-xs text-fulkro-ink-600">
              <div className="font-semibold uppercase tracking-wide mb-1">
                Firmas ({acta.firmas.length}):
              </div>
              <ul className="space-y-1">
                {acta.firmas.map((f, i) => (
                  <li key={i} className="font-mono">
                    {f.actor ?? f.asistente_nombre ?? "—"} ·{" "}
                    {fmtDateTime(f.firmado_at)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {!signed && (
        <Card className="p-5">
          <div className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Revisión cliente
          </div>
          {reviewed && acta.client_review_note && (
            <div className="text-xs text-fulkro-ink-600 mb-3 p-2 rounded bg-fulkro-ink-50 italic">
              &ldquo;{acta.client_review_note}&rdquo;
            </div>
          )}
          {pendingAction === null ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant={reviewed ? "outline" : "primary"}
                onClick={() => handleAction("revisada_ok")}
                disabled={submitting}
                data-testid="acta-review-ok"
              >
                {submitting ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3 w-3" />
                )}
                <span className="ml-1.5">
                  {reviewed ? "Revisada OK" : "Marcar revisada OK"}
                </span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleAction("con_pregunta")}
                disabled={submitting}
              >
                <HelpCircle className="h-3 w-3" />
                <span className="ml-1.5">Tengo una pregunta</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleAction("suggest_change")}
                disabled={submitting}
              >
                <Lightbulb className="h-3 w-3" />
                <span className="ml-1.5">Sugerir cambio</span>
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={
                  pendingAction === "con_pregunta"
                    ? "¿Qué duda tienes sobre esta acta?"
                    : "¿Qué cambio sugieres?"
                }
                rows={3}
                className="text-sm"
                maxLength={4000}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={submitWithNote}
                  disabled={submitting || note.trim().length < 5}
                >
                  {submitting && <Loader2 className="h-3 w-3 animate-spin" />}
                  Guardar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setPendingAction(null);
                    setNote("");
                  }}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {!signed && (
        <ActaSignButton
          acta={acta}
          reviewed={reviewed}
          onSigningComplete={onSigningComplete}
        />
      )}

      {signed && (
        <Card className="p-4 border-fulkro-success/40 bg-fulkro-success/10">
          <div className="flex items-center gap-2 text-sm text-fulkro-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            <span className="font-semibold">
              Acta firmada · trazabilidad asegurada
            </span>
          </div>
        </Card>
      )}
    </div>
  );
}
