"use client";

/**
 * Checkin detail · 5 secciones core + 2 bonus · SAN-E v3.MB-6 atom 4.
 */
import { useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Lightbulb,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { CheckinSignButton } from "@/components/client-portal/retainer-checkin/CheckinSignButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  type CheckinReviewAction,
  type RagStatus,
  type RetainerCheckin,
} from "@/lib/api/retainer-checkin";
import { cn } from "@/lib/utils";

interface Props {
  checkin: RetainerCheckin;
  onReview: (
    reportId: string,
    action: CheckinReviewAction,
    note?: string,
  ) => Promise<void>;
  onSigningComplete: () => void;
}

function ragBanner(rag: RagStatus | null) {
  if (rag === "red") {
    return (
      <div className="rounded-lg border-2 border-destructive/40 bg-destructive/10 p-3 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-destructive flex-shrink-0" aria-hidden />
        <div className="text-sm font-semibold text-destructive">
          RAG Rojo · acciones críticas pendientes
        </div>
      </div>
    );
  }
  if (rag === "amber") {
    return (
      <div className="rounded-lg border-2 border-fulkro-warning/40 bg-fulkro-warning/10 p-3 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-fulkro-warning flex-shrink-0" aria-hidden />
        <div className="text-sm font-semibold text-fulkro-warning">
          RAG Ámbar · vigilancia requerida
        </div>
      </div>
    );
  }
  if (rag === "green") {
    return (
      <div className="rounded-lg border-2 border-fulkro-success/40 bg-fulkro-success/10 p-3 flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-fulkro-success flex-shrink-0" aria-hidden />
        <div className="text-sm font-semibold text-fulkro-success">
          RAG Verde · estado saludable
        </div>
      </div>
    );
  }
  return null;
}

function SummaryStat({
  label, value, accent,
}: {
  label: string; value: number | string; accent?: "danger" | "warning" | "success" | "info";
}) {
  const colorMap = {
    danger: "text-destructive",
    warning: "text-fulkro-warning",
    success: "text-fulkro-success",
    info: "text-fulkro-info",
  };
  return (
    <div>
      <dt className="text-xs text-fulkro-ink-500 uppercase tracking-wide">{label}</dt>
      <dd className={cn(
        "font-bold text-lg font-mono tabular-nums mt-0.5",
        accent ? colorMap[accent] : "text-fulkro-ink-700",
      )}>
        {value}
      </dd>
    </div>
  );
}

export function CheckinDetail({
  checkin,
  onReview,
  onSigningComplete,
}: Props) {
  const [pendingAction, setPendingAction] = useState<CheckinReviewAction | null>(
    null,
  );
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reviewed = checkin.client_review_status === "revisada_ok";
  const signed = checkin.client_signing_intent_id != null;
  const summary = checkin.summary_jsonb;

  const handleAction = async (action: CheckinReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(checkin.id, action);
        toast.success("Comité retainer marcado revisado");
      } catch {
        // toast viene del hook
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(checkin.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) {
      toast.error("La nota debe tener al menos 5 caracteres");
      return;
    }
    setSubmitting(true);
    try {
      await onReview(checkin.id, pendingAction, note.trim());
      toast.success("Review actualizado");
      setPendingAction(null);
    } catch {
      // toast viene del hook
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="checkin-detail" className="space-y-4">
      <Card className="p-5">
        <div className="text-xs uppercase tracking-wide font-semibold text-fulkro-primary-700">
          Comité Retainer
        </div>
        <h2 className="text-xl font-bold text-fulkro-ink-800 mt-1">
          {checkin.period_quarter ?? "—"}
        </h2>
        <div className="text-sm text-fulkro-ink-600 mt-1">
          {new Date(checkin.period_start).toLocaleDateString("es-ES")} →{" "}
          {new Date(checkin.period_end).toLocaleDateString("es-ES")}
        </div>
      </Card>

      {ragBanner(checkin.rag_overall as RagStatus | null)}

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="h-4 w-4 text-fulkro-primary-700" aria-hidden />
          <h3 className="font-semibold text-sm text-fulkro-ink-800">
            Actividades retainer
          </h3>
        </div>
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
          <SummaryStat
            label="Completadas"
            value={checkin.activities_completed}
            accent="success"
          />
          <SummaryStat
            label="Pendientes"
            value={checkin.activities_pending}
          />
          <SummaryStat
            label="Atrasadas"
            value={checkin.activities_overdue}
            accent={checkin.activities_overdue > 0 ? "warning" : undefined}
          />
        </dl>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="h-4 w-4 text-fulkro-warning" aria-hidden />
          <h3 className="font-semibold text-sm text-fulkro-ink-800">
            Incidentes y vulnerabilidades
          </h3>
        </div>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <SummaryStat
            label="Incidents detectados"
            value={checkin.incidents_detected}
          />
          <SummaryStat
            label="Vulns críticas"
            value={checkin.vulns_critical}
            accent={checkin.vulns_critical > 0 ? "danger" : "success"}
          />
          {summary?.incidents && (
            <SummaryStat
              label="Notificados CCN-CERT"
              value={summary.incidents.ccn_cert_routed}
            />
          )}
        </dl>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-4 w-4 text-fulkro-info" aria-hidden />
          <h3 className="font-semibold text-sm text-fulkro-ink-800">
            Normativa y stakeholders
          </h3>
        </div>
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <SummaryStat
            label="Cambios normativa"
            value={checkin.normativa_changes_relevant}
          />
          {summary?.stakeholder_changes && (
            <SummaryStat
              label="Interacciones stakeholders"
              value={summary.stakeholder_changes.count}
            />
          )}
          {summary?.evidence_freshness && (
            <SummaryStat
              label="Evidencias vigentes"
              value={summary.evidence_freshness.fresh}
              accent="info"
            />
          )}
        </dl>
      </Card>

      {summary && summary.evidence_freshness && summary.evidence_freshness.stale > 0 && (
        <Card className="p-4 border-fulkro-warning/40 bg-fulkro-warning/10">
          <div className="flex items-center gap-2 text-sm text-fulkro-warning">
            <AlertCircle className="h-4 w-4" aria-hidden />
            <span>
              {summary.evidence_freshness.stale} evidencias caducadas pendientes
              de renovación
            </span>
          </div>
        </Card>
      )}

      {!signed && (
        <Card className="p-5">
          <div className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Revisión cliente
          </div>
          {reviewed && checkin.client_review_note && (
            <div className="text-xs text-fulkro-ink-600 mb-3 p-2 rounded bg-fulkro-ink-50 italic">
              &ldquo;{checkin.client_review_note}&rdquo;
            </div>
          )}
          {pendingAction === null ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant={reviewed ? "outline" : "primary"}
                onClick={() => handleAction("revisada_ok")}
                disabled={submitting}
                data-testid="checkin-review-ok"
              >
                {submitting ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3 w-3" />
                )}
                <span className="ml-1.5">
                  {reviewed ? "Revisado OK" : "Marcar revisado OK"}
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
                    ? "¿Qué duda tienes sobre el comité trimestral?"
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
        <CheckinSignButton
          checkin={checkin}
          reviewed={reviewed}
          onSigningComplete={onSigningComplete}
        />
      )}

      {signed && (
        <Card className="p-4 border-fulkro-success/40 bg-fulkro-success/10">
          <div className="flex items-center gap-2 text-sm text-fulkro-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden />
            <span className="font-semibold">
              Comité firmado · audit ENAC asegurado
            </span>
          </div>
        </Card>
      )}
    </div>
  );
}
