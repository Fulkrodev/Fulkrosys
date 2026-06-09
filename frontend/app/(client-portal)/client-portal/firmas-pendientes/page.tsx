"use client";

/**
 * /client-portal/firmas-pendientes · Ejecutable 7.7 TIER 1 canvas signing.
 *
 * Cliente VE documentos pendientes de firma + SignatureCanvas inline cuando
 * selecciona uno. R29 friendly · NO admin lingo · SSE auto-update Pattern #14.
 *
 * Backend wire-up:
 *  - GET  /api/v1/portal/signing/projects/{id}/pending
 *  - POST /api/v1/portal/signing/intents/{intent_id}/sign-canvas
 *
 * SSE realtime via useClientProjectEvents Pattern #14 → events:
 *  - signing.requested · admin trigger nueva firma · refresh list
 *  - signing.signed · cliente firmó · refresh list (excluido)
 */
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, FileSignature, Inbox } from "lucide-react";

import { SignatureCanvas } from "@/components/signatures/SignatureCanvas";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import {
  type PendingSignatureCard,
  listPendingSignatures,
  signIntentCanvas,
} from "@/lib/api/signing";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface ProjectInfo {
  id: string;
  nombre?: string;
}

export default function FirmasPendientesPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingSignatureCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeIntentId, setActiveIntentId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchPending = useCallback(async (pid: string) => {
    try {
      const result = await listPendingSignatures(pid);
      setPending(result.pending);
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Error cargando documentos pendientes de firma");
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      setLoading(true);
      try {
        const proj = await clientApi<ProjectInfo>("/client-portal/project");
        if (cancelled) return;
        setProjectId(proj.id);
        await fetchPending(proj.id);
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ClientApiError) {
            setError(err.message);
          } else {
            setError("No se pudo resolver tu proyecto");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [fetchPending]);

  // SSE auto-update Pattern #14 · refresh on signing.* events
  useClientProjectEvents(projectId, {
    onSigningRequested: () => {
      if (projectId) void fetchPending(projectId);
    },
    onSigningSigned: () => {
      if (projectId) void fetchPending(projectId);
    },
    onSigningDeclined: () => {
      if (projectId) void fetchPending(projectId);
    },
  });

  const handleSubmitSign = async (
    intentId: string,
    payload: {
      signature_canvas_dataurl: string;
      signed_name: string;
      signed_surname: string;
    },
  ) => {
    setSubmitting(true);
    try {
      await signIntentCanvas(intentId, payload);
      toast.success("Documento firmado correctamente");
      setActiveIntentId(null);
      if (projectId) await fetchPending(projectId);
    } catch (err) {
      const msg =
        err instanceof ClientApiError
          ? err.message
          : "No se pudo enviar la firma. Inténtalo de nuevo.";
      toast.error(msg);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  const activeCard = pending.find((c) => c.intent_id === activeIntentId);

  return (
    <div
      className="space-y-6 px-4 py-6 sm:px-6 md:px-8 max-w-4xl mx-auto"
      data-testid="firmas-pendientes-page"
    >
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <FileSignature className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente
          </span>
        </div>
        <h1 className="text-2xl font-bold text-fulkro-ink-800">
          Documentos pendientes de firma
        </h1>
        <p className="max-w-3xl text-sm text-fulkro-ink-600">
          Aquí aparecen los documentos que necesitan tu firma para continuar
          con el proyecto <TooltipENS term="ENS" />. Cuando firmas, queda
          registrado con sello criptográfico <TooltipENS term="Ed25519" /> y
          trazabilidad <TooltipENS term="ENAC" />. Sin prisa por tu parte.
        </p>
      </header>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : error ? (
        <Card
          className="border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          data-testid="firmas-pendientes-error"
          role="alert"
        >
          {error}
        </Card>
      ) : pending.length === 0 ? (
        <Card
          className="flex flex-col items-center gap-3 p-8 text-center"
          data-testid="firmas-pendientes-empty"
        >
          <Inbox className="h-12 w-12 text-emerald-500" aria-hidden />
          <h2 className="text-lg font-semibold text-fulkro-ink-800">
            No tienes documentos pendientes de firma
          </h2>
          <p className="max-w-md text-sm text-fulkro-ink-600">
            Te avisaremos por aquí cuando llegue alguno. Mientras tanto,
            seguimos avanzando con tu implantación.
          </p>
        </Card>
      ) : activeCard ? (
        <div className="space-y-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => setActiveIntentId(null)}
            data-testid="firmas-pendientes-back"
          >
            ← Volver a la lista
          </Button>
          <Card className="p-4">
            <h2 className="mb-2 text-lg font-semibold text-fulkro-ink-800">
              {activeCard.signable_label}
            </h2>
            <p className="mb-4 text-xs text-fulkro-ink-500">
              Hash del documento: <code>{activeCard.document_hash_sha256.slice(0, 16)}…</code>
            </p>
            <SignatureCanvas
              documentLabel={activeCard.signable_label}
              isSubmitting={submitting}
              testIdPrefix={`firmas-pendientes-canvas-${activeCard.intent_id}`}
              onSubmit={(payload) =>
                handleSubmitSign(activeCard.intent_id, payload)
              }
            />
          </Card>
        </div>
      ) : (
        <ul
          className="space-y-3"
          data-testid="firmas-pendientes-list"
        >
          {pending.map((card) => (
            <li key={card.intent_id}>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <h2 className="text-base font-semibold text-fulkro-ink-800">
                    {card.signable_label}
                  </h2>
                  <p className="mt-1 text-xs text-fulkro-ink-500">
                    Pendiente desde {new Date(card.created_at).toLocaleDateString("es-ES")}
                  </p>
                </div>
                <Button
                  type="button"
                  onClick={() => setActiveIntentId(card.intent_id)}
                  data-testid={`firmas-pendientes-open-${card.intent_id}`}
                >
                  Firmar
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {pending.length > 0 && (
        <p
          className="flex items-center gap-2 text-xs text-fulkro-ink-500"
          data-testid="firmas-pendientes-count"
        >
          <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden />
          Tienes {pending.length}{" "}
          {pending.length === 1 ? "documento" : "documentos"} pendiente
          {pending.length === 1 ? "" : "s"} de firma.
        </p>
      )}
    </div>
  );
}
