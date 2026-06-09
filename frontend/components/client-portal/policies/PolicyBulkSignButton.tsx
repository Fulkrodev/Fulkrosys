"use client";

/**
 * Policy bulk sign button · sticky bottom · firma bulk única CCN-STIC 805.
 *
 * Flow:
 *  1. Click "Firmar todas las políticas"
 *  2. Fetch bulk-document-hash (verify ready_for_signing)
 *  3. Open SigningFlow modal · signableType="policy_approval"
 *  4. On success: call finalize-signoff (link signing_intent to all docs)
 *  5. Toast + refetch summary
 *
 * Pattern atom 5.3.C consolidated (DdaSignFinalButton replica).
 */
import { useState } from "react";
import { FileSignature, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  finalizePoliciesSignoff,
  getPoliciesBulkHash,
} from "@/lib/api/policies";
import type { SignedDocumentResponse } from "@/lib/api/signing";

interface Props {
  projectId: string;
  tier: string;
  expectedCount: number;
  ready: boolean;
  alreadySigned: boolean;
  onSigningComplete: () => void;
}

export function PolicyBulkSignButton({
  projectId,
  tier,
  expectedCount,
  ready,
  alreadySigned,
  onSigningComplete,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    try {
      const hash = await getPoliciesBulkHash(projectId);
      if (!hash.ready_for_signing) {
        toast.error("Todavía hay políticas pendientes de revisar");
        return;
      }
      setDocumentHash(hash.document_hash_sha256);
      setOpen(true);
    } catch (err) {
      if (err instanceof ClientApiError) {
        toast.error(err.message);
      } else {
        toast.error("Error preparando firma bulk");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (signature: SignedDocumentResponse) => {
    try {
      const result = await finalizePoliciesSignoff(
        projectId,
        signature.intent_id,
      );
      toast.success(
        `Firma completada · ${result.documents_linked} políticas linkadas`,
      );
      setOpen(false);
      onSigningComplete();
    } catch (err) {
      if (err instanceof ClientApiError) {
        toast.error(err.message);
      } else {
        toast.error("Error finalizando signoff");
      }
    }
  };

  if (alreadySigned) {
    return (
      <div className="sticky bottom-4 z-10 mt-6">
        <div className="rounded-lg border border-fulkro-success/40 bg-fulkro-success/10 p-4 flex items-center gap-3">
          <FileSignature
            className="h-5 w-5 text-fulkro-success flex-shrink-0"
            aria-hidden
          />
          <div>
            <div className="font-semibold text-sm text-fulkro-success">
              Políticas firmadas
            </div>
            <div className="text-xs text-fulkro-ink-600 mt-0.5">
              Las {expectedCount} políticas tier {tier} ya están vinculadas a
              tu firma bulk · chain integrity asegurada.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="sticky bottom-4 z-10 mt-6">
        <div className="rounded-lg border border-fulkro-ink-200 bg-white shadow-md p-4 flex items-center justify-between gap-3">
          <div>
            <div className="font-semibold text-sm text-fulkro-ink-800">
              Firma bulk · todas las políticas
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {ready
                ? `Listo para firmar ${expectedCount} políticas tier ${tier}`
                : "Termina de revisar todas las políticas para habilitar la firma"}
            </div>
          </div>
          <Button
            onClick={handleClick}
            disabled={!ready || loading}
            data-testid="policies-bulk-sign-button"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSignature className="h-4 w-4" />
            )}
            <span className="ml-1.5">Firmar políticas</span>
          </Button>
        </div>
      </div>

      {open && documentHash && (
        <SigningFlow
          open={open}
          onClose={() => setOpen(false)}
          projectId={projectId}
          signableType="policy_approval"
          signableLabel={`Aprobación políticas (${expectedCount} tier ${tier})`}
          documentHash={documentHash}
          onSuccess={handleSuccess}
        />
      )}
    </>
  );
}
