"use client";

/**
 * Acta sign button · SigningFlow drop-in · 7ª aplicación · MB-6 atom 5.
 *
 * signableType='acta_comite' · NO step-up OTP (acta_comite NOT en
 * REQUIRES_STEP_UP_OTP frozenset · audit findings 5.6.0 confirmed).
 */
import { useState } from "react";
import { FileSignature, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  type ActaClientView,
  ACTA_SUBTYPE_SHORT_LABELS,
  finalizeActaSignoff,
  getActaDocumentHash,
} from "@/lib/api/actas";
import type { SignedDocumentResponse } from "@/lib/api/signing";

interface Props {
  acta: ActaClientView;
  reviewed: boolean;
  onSigningComplete: () => void;
}

export function ActaSignButton({ acta, reviewed, onSigningComplete }: Props) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    try {
      const hash = await getActaDocumentHash(acta.id);
      if (!hash.ready_for_signing) {
        toast.error("Marca el acta como revisada antes de firmar");
        return;
      }
      setDocumentHash(hash.document_hash_sha256);
      setOpen(true);
    } catch (err) {
      if (err instanceof ClientApiError) toast.error(err.message);
      else toast.error("Error preparando firma acta");
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (signature: SignedDocumentResponse) => {
    try {
      await finalizeActaSignoff(acta.id, signature.intent_id);
      const label = acta.acta_subtype
        ? ACTA_SUBTYPE_SHORT_LABELS[acta.acta_subtype]
        : "Acta";
      toast.success(`${label} firmada · trazabilidad asegurada`);
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
              Firmar acta
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {reviewed
                ? "Firma electrónica · sin OTP adicional"
                : "Marca el acta como revisada antes de firmar"}
            </div>
          </div>
          <Button
            onClick={handleClick}
            disabled={!reviewed || loading}
            data-testid="acta-sign-button"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSignature className="h-4 w-4" />
            )}
            <span className="ml-1.5">Firmar acta</span>
          </Button>
        </div>
      </div>

      {open && documentHash && (
        <SigningFlow
          open={open}
          onClose={() => setOpen(false)}
          projectId={acta.project_id}
          signableType="acta_comite"
          signableLabel={acta.titulo ?? acta.codigo ?? "Acta"}
          documentHash={documentHash}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
