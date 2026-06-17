"use client";

/**
 * Incident detail · expanded panel · SAN-E v3.MB-6 atom 3.
 *
 * Display:
 *  - Descripción + resolución
 *  - Workflow state + severity badge
 *  - CCN-CERT routing decision (internal_only/lucia_federation/manual_notification)
 *  - Si manual_notification + lucia_submission_id NULL · download PDF E-CCN-NOTIFY
 *  - Cliente review actions (3 botones · note opcional)
 *  - Sign incident_close button (sticky)
 */
import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  HelpCircle,
  Lightbulb,
  Loader2,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

import { IncidentSignButton } from "@/components/client-portal/incidents/IncidentSignButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { documentDownloadUrl } from "@/lib/api/files-extended";
import {
  type IncidentClient,
  type IncidentReviewAction,
} from "@/lib/api/incidents";
import { cn } from "@/lib/utils";

interface Props {
  incident: IncidentClient;
  onReview: (
    incidentId: string,
    action: IncidentReviewAction,
    note?: string,
  ) => Promise<void>;
  onSigningComplete: () => void;
}

function routingBadge(routing: IncidentClient["ccn_cert_routing"]) {
  if (!routing) return null;
  if (routing.route_type === "internal_only") {
    return <Badge variant="secondary">Interno · sin notificación externa</Badge>;
  }
  if (routing.route_type === "lucia_federation") {
    return <Badge variant="info">LUCIA federation · auto-reportado</Badge>;
  }
  return <Badge variant="warning">Notificación manual CCN-CERT requerida</Badge>;
}

export function IncidentDetail({
  incident,
  onReview,
  onSigningComplete,
}: Props) {
  const [pendingAction, setPendingAction] = useState<IncidentReviewAction | null>(
    null,
  );
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reviewed = incident.client_review_status === "revisada_ok";
  const closed = incident.workflow_state === "closed";
  const isManualNotification =
    incident.ccn_cert_routing?.route_type === "manual_notification";

  const handleAction = async (action: IncidentReviewAction) => {
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await onReview(incident.id, action);
        toast.success("Incident marcado revisado");
      } catch {
        // toast viene del hook
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(incident.client_review_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction) return;
    if (note.trim().length < 5) {
      toast.error("La nota debe tener al menos 5 caracteres");
      return;
    }
    setSubmitting(true);
    try {
      await onReview(incident.id, pendingAction, note.trim());
      toast.success("Review actualizado");
      setPendingAction(null);
    } catch {
      // toast viene del hook
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="incident-detail" className="space-y-4">
      <Card className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="text-xs uppercase tracking-wide font-semibold text-fulkro-primary-700">
              Incidente seguridad
            </div>
            <div className="text-sm text-fulkro-ink-700 mt-1">
              {incident.fecha
                ? new Date(incident.fecha).toLocaleString("es-ES")
                : "Sin fecha"}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            {closed && <Badge variant="success">Cerrado</Badge>}
            {!closed && incident.workflow_state === "resolved" && (
              <Badge variant="info">Resuelto</Badge>
            )}
          </div>
        </div>

        <div className="space-y-3 text-sm">
          <div>
            <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
              Descripción
            </div>
            <p className="text-fulkro-ink-800 mt-1 whitespace-pre-wrap">
              {incident.descripcion ?? "—"}
            </p>
          </div>
          {incident.resolucion && (
            <div>
              <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
                Resolución y acciones tomadas
              </div>
              <p className="text-fulkro-ink-800 mt-1 whitespace-pre-wrap">
                {incident.resolucion}
              </p>
            </div>
          )}
        </div>
      </Card>

      <Card className="p-5">
        <div className="font-semibold text-sm text-fulkro-ink-800 mb-2">
          Notificación CCN-CERT
        </div>
        <div className="flex items-start gap-2">
          {incident.ccn_cert_routing?.route_type === "internal_only" ? (
            <ShieldCheck
              className="h-5 w-5 mt-0.5 text-fulkro-info flex-shrink-0"
              aria-hidden
            />
          ) : (
            <ShieldAlert
              className="h-5 w-5 mt-0.5 text-fulkro-warning flex-shrink-0"
              aria-hidden
            />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {routingBadge(incident.ccn_cert_routing)}
              {incident.ccn_cert_routing?.deadline_hours && (
                <span className="text-xs text-fulkro-ink-500">
                  Deadline {incident.ccn_cert_routing.deadline_hours}h
                </span>
              )}
            </div>
            {incident.ccn_cert_routing?.reasoning && (
              <p className="text-xs text-fulkro-ink-600 mt-1">
                {incident.ccn_cert_routing.reasoning}
              </p>
            )}
          </div>
        </div>

        {isManualNotification && incident.manual_notification_doc_id && (
          <div className="mt-4">
            {/* S28c (campaña 2026-06-17): descarga REAL del documento E-CCN-NOTIFY
                vía el endpoint cliente /client-portal/documents/{id}/download
                (cross-tenant check + MinIO). El botón sólo aparece si el doc ya
                existe (manual_notification_doc_id != null). */}
            <Button
              size="sm"
              variant="outline"
              data-testid="incident-manual-notification-download"
              onClick={() =>
                window.open(
                  documentDownloadUrl(incident.manual_notification_doc_id!),
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              <Download className="h-3 w-3" />
              <span className="ml-1.5">Descargar E-CCN-NOTIFY</span>
            </Button>
          </div>
        )}
      </Card>

      {!closed && (
        <Card className="p-5">
          <div className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            Revisión cliente
          </div>
          {reviewed && incident.client_review_note && (
            <div className="text-xs text-fulkro-ink-600 mb-3 p-2 rounded bg-fulkro-ink-50 italic">
              &ldquo;{incident.client_review_note}&rdquo;
            </div>
          )}
          {pendingAction === null ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant={reviewed ? "outline" : "primary"}
                onClick={() => handleAction("revisada_ok")}
                disabled={submitting}
                data-testid="incident-review-ok"
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
                    ? "¿Qué duda tienes sobre este incident?"
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

      {!closed && (
        <IncidentSignButton
          incident={incident}
          reviewed={reviewed}
          onSigningComplete={onSigningComplete}
        />
      )}
    </div>
  );
}
