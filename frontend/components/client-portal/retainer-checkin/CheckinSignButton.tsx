"use client";

/**
 * Checkin sign button · SigningFlow drop-in · 6ª aplicación.
 *
 * signableType='retainer_quarterly_signoff' · step-up OTP requerido (audit ENAC).
 */
import { useState } from "react";
import { FileSignature, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  type RetainerCheckin,
  finalizeCheckinSignoff,
  getCheckinDocumentHash,
} from "@/lib/api/retainer-checkin";
import type { SignedDocumentResponse } from "@/lib/api/signing";

interface Props {
  checkin: RetainerCheckin;
  reviewed: boolean;
  onSigningComplete: () => void;
}

export function CheckinSignButton({
  checkin,
  reviewed,
  onSigningComplete,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    try {
      const hash = await getCheckinDocumentHash(checkin.id);
      if (!hash.ready_for_signing) {
        toast.error("Marca el comité como revisado antes de firmar");
        return;
      }
      setDocumentHash(hash.document_hash_sha256);
      setOpen(true);
    } catch (err) {
      if (err instanceof ClientApiError) toast.error(err.message);
      else toast.error("Error preparando firma comité");
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (signature: SignedDocumentResponse) => {
    try {
      await finalizeCheckinSignoff(checkin.id, signature.intent_id);
      toast.success(
        `Comité ${checkin.period_quarter} firmado · trazabilidad ENAC asegurada`,
      );
      setOpen(false);
      onSigningComplete();
    } catch (err) {
      if (err instanceof ClientApiError) toast.error(err.message);
      else toast.error("Error finalizando firma");
    }
  };

  return (
    <>
      <div className="sticky bottom-4 z-10 mt-6">
        <div className="rounded-lg border border-fulkro-ink-200 bg-white shadow-md p-4 flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-sm text-fulkro-ink-800">
              Firmar comité retainer
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {reviewed
                ? "OTP step-up requerido (audit ENAC trimestral)"
                : "Marca el comité como revisado antes de firmar"}
            </div>
          </div>
          <Button
            onClick={handleClick}
            disabled={!reviewed || loading}
            data-testid="checkin-sign-button"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSignature className="h-4 w-4" />
            )}
            <span className="ml-1.5">Firmar comité</span>
          </Button>
        </div>
      </div>

      {open && documentHash && (
        <SigningFlow
          open={open}
          onClose={() => setOpen(false)}
          projectId={checkin.project_id}
          signableType="retainer_quarterly_signoff"
          signableLabel={`Comité Retainer ${checkin.period_quarter ?? ""}`}
          documentHash={documentHash}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
