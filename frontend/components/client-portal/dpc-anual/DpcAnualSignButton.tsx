"use client";

/**
 * DPC anual sign button · sticky bottom · SAN-E v3.MB-6 atom 2.
 *
 * Drop-in SigningFlow pattern · 4ª aplicación post (dda + magerit + policies).
 * Step-up OTP requerido (dpc_anual en REQUIRES_STEP_UP_OTP).
 */
import { useState } from "react";
import { FileSignature, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  type DpcDeclaration,
  finalizeDpcSignoff,
  getDpcDocumentHash,
} from "@/lib/api/dpc-anual";
import type { SignedDocumentResponse } from "@/lib/api/signing";

interface Props {
  declaration: DpcDeclaration;
  reviewed: boolean;
  onSigningComplete: () => void;
}

export function DpcAnualSignButton({
  declaration,
  reviewed,
  onSigningComplete,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    try {
      const hash = await getDpcDocumentHash(declaration.id);
      if (!hash.ready_for_signing) {
        toast.error("Marca la DPC anual como revisada antes de firmar");
        return;
      }
      setDocumentHash(hash.document_hash_sha256);
      setOpen(true);
    } catch (err) {
      if (err instanceof ClientApiError) {
        toast.error(err.message);
      } else {
        toast.error("Error preparando firma DPC");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (signature: SignedDocumentResponse) => {
    try {
      await finalizeDpcSignoff(declaration.id, signature.intent_id);
      toast.success(
        `DPC anual ${declaration.anniversary_year} firmada · trazabilidad ENAC asegurada`,
      );
      setOpen(false);
      onSigningComplete();
    } catch (err) {
      if (err instanceof ClientApiError) {
        toast.error(err.message);
      } else {
        toast.error("Error finalizando signoff DPC");
      }
    }
  };

  if (declaration.status === "signed") {
    return null;
  }

  return (
    <>
      <div className="sticky bottom-4 z-10 mt-6">
        <div className="rounded-lg border border-fulkro-ink-200 bg-white shadow-md p-4 flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-sm text-fulkro-ink-800">
              Firmar DPC anual {declaration.anniversary_year}
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {reviewed
                ? "Lista para firma · OTP step-up requerido (art.25 RD 311/2022)"
                : "Marca la declaración como revisada antes de firmar"}
            </div>
          </div>
          <Button
            onClick={handleClick}
            disabled={!reviewed || loading}
            data-testid="dpc-sign-button"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSignature className="h-4 w-4" />
            )}
            <span className="ml-1.5">Firmar DPC</span>
          </Button>
        </div>
      </div>

      {open && documentHash && (
        <SigningFlow
          open={open}
          onClose={() => setOpen(false)}
          projectId={declaration.project_id}
          signableType="dpc_anual"
          signableLabel={`DPC anual ${declaration.anniversary_year}`}
          documentHash={documentHash}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
