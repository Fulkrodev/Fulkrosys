"use client";

/**
 * Policy row · individual policy review · SAN-E v3.MB-6 atom 1.
 *
 * 3 review actions: revisada_ok · con_pregunta · suggest_change
 * Pattern alineado DdaMeasureRow (atom 5.3.A).
 */
import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Lightbulb,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  type PolicyClientView,
  type PolicyReviewAction,
} from "@/lib/api/policies";
import { cn } from "@/lib/utils";

interface Props {
  policy: PolicyClientView;
  onReview: (
    documentId: string,
    action: PolicyReviewAction,
    note?: string,
  ) => Promise<void>;
  disabled: boolean;
}

function statusBadge(status: PolicyClientView["client_review_status"]) {
  if (status === "revisada_ok") return <Badge variant="success">Revisada</Badge>;
  if (status === "con_pregunta") return <Badge variant="warning">Con pregunta</Badge>;
  if (status === "suggest_change") return <Badge variant="warning">Cambio sugerido</Badge>;
  return <Badge variant="secondary">Pendiente</Badge>;
}

export function PolicyRow({ policy, onReview, disabled }: Props) {
  const [pendingAction, setPendingAction] = useState<PolicyReviewAction | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reviewed = policy.client_review_status === "revisada_ok";
  const docMissing = policy.document_id === null;

  const handleAction = async (action: PolicyReviewAction) => {
    setError(null);
    if (docMissing) {
      setError("Política aún no generada por el consultor");
      return;
    }
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(policy.document_id!, action);
        toast.success(`${policy.template_codigo} marcada como revisada`);
      } catch {
        // error toast viene del hook
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(policy.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction || !policy.document_id) return;
    if (note.trim().length < 5) {
      setError("La nota debe tener al menos 5 caracteres");
      return;
    }
    setSubmitting(true);
    try {
      await onReview(policy.document_id, pendingAction, note.trim());
      toast.success(`${policy.template_codigo} actualizada`);
      setPendingAction(null);
    } catch {
      // error toast viene del hook
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-template-codigo={policy.template_codigo}
      data-review-status={policy.client_review_status ?? "pending"}
      className={cn(
        "rounded-lg border p-4",
        reviewed && "border-fulkro-success/30 bg-fulkro-success/5",
        docMissing && "border-fulkro-ink-200 bg-fulkro-ink-50/50 opacity-70",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="font-mono text-xs text-fulkro-ink-500 mt-0.5 flex-shrink-0">
            {policy.template_codigo}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-fulkro-ink-800 truncate">
              {policy.nombre ?? "Pendiente de generación por el consultor"}
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              Nivel {policy.level} · {policy.family}
              {policy.client_reviewed_at && (
                <>
                  {" · "}
                  Revisada {new Date(policy.client_reviewed_at).toLocaleDateString("es-ES")}
                </>
              )}
            </div>
            {policy.client_review_note && (
              <div className="text-xs text-fulkro-ink-600 mt-2 p-2 rounded bg-fulkro-ink-50 italic">
                &ldquo;{policy.client_review_note}&rdquo;
              </div>
            )}
          </div>
        </div>
        <div className="flex-shrink-0">{statusBadge(policy.client_review_status)}</div>
      </div>

      {!docMissing && pendingAction === null && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={reviewed ? "outline" : "primary"}
            onClick={() => handleAction("revisada_ok")}
            disabled={disabled || submitting}
          >
            {submitting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3 w-3" />
            )}
            <span className="ml-1.5">
              {reviewed ? "Aceptada" : "Marcar revisada OK"}
            </span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleAction("con_pregunta")}
            disabled={disabled || submitting}
          >
            <HelpCircle className="h-3 w-3" />
            <span className="ml-1.5">Tengo una pregunta</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleAction("suggest_change")}
            disabled={disabled || submitting}
          >
            <Lightbulb className="h-3 w-3" />
            <span className="ml-1.5">Sugerir cambio</span>
          </Button>
        </div>
      )}

      {pendingAction !== null && (
        <div className="mt-3 space-y-2">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              pendingAction === "con_pregunta"
                ? "¿Qué duda tienes sobre esta política?"
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
                setError(null);
              }}
              disabled={submitting}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-2 flex items-start gap-1.5 text-xs text-destructive">
          <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" aria-hidden />
          {error}
        </div>
      )}
    </div>
  );
}
