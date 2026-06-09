"use client";

/**
 * Incident close sign button · SigningFlow drop-in · 5ª aplicación.
 *
 * signableType='incident_close' · NO step-up OTP (not in REQUIRES_STEP_UP_OTP).
 */
import { useState } from "react";
import { FileSignature, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  type IncidentClient,
  finalizeIncidentClose,
  getIncidentCloseHash,
} from "@/lib/api/incidents";
import type { SignedDocumentResponse } from "@/lib/api/signing";

interface Props {
  incident: IncidentClient;
  reviewed: boolean;
  onSigningComplete: () => void;
}

export function IncidentSignButton({
  incident,
  reviewed,
  onSigningComplete,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    try {
      const hash = await getIncidentCloseHash(incident.id);
      if (!hash.ready_for_signing) {
        toast.error("Marca el incident como revisado antes de firmar cierre");
        return;
      }
      setDocumentHash(hash.document_hash_sha256);
      setOpen(true);
    } catch (err) {
      if (err instanceof ClientApiError) toast.error(err.message);
      else toast.error("Error preparando firma cierre");
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (signature: SignedDocumentResponse) => {
    try {
      await finalizeIncidentClose(incident.id, signature.intent_id);
      toast.success("Cierre incident firmado · trazabilidad ENAC asegurada");
      setOpen(false);
      onSigningComplete();
    } catch (err) {
      if (err instanceof ClientApiError) toast.error(err.message);
      else toast.error("Error finalizando cierre");
    }
  };

  return (
    <>
      <div className="sticky bottom-4 z-10 mt-6">
        <div className="rounded-lg border border-fulkro-ink-200 bg-white shadow-md p-4 flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-sm text-fulkro-ink-800">
              Cerrar incident
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {reviewed
                ? "Firma para cerrar incident · queda en historial firmas"
                : "Marca el incident como revisado antes de cerrar"}
            </div>
          </div>
          <Button
            onClick={handleClick}
            disabled={!reviewed || loading}
            data-testid="incident-close-sign-button"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSignature className="h-4 w-4" />
            )}
            <span className="ml-1.5">Firmar cierre</span>
          </Button>
        </div>
      </div>

      {open && documentHash && (
        <SigningFlow
          open={open}
          onClose={() => setOpen(false)}
          projectId={incident.project_id}
          signableType="incident_close"
          signableLabel={`Cierre incidente ${incident.severidad ?? ""}`}
          documentHash={documentHash}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
