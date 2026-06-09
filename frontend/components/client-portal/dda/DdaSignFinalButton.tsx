"use client";

/**
 * DdaSignFinalButton · sticky bottom · readiness gate · firma DdA E2E.
 *
 * SAN-E v3.MB-5.3.C · primer wire-up cliente firma in-portal.
 *
 * Flow:
 * 1. Click "Firmar DdA final" → fetch document-hash backend
 * 2. Verify ready_for_signing flag
 * 3. Open SigningFlow modal · signableType="dda"
 * 4. SigningFlow handles intent + OTP + sign internamente
 * 5. onSuccess: toast + onSigningComplete callback (refetch summary)
 */
import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { ClientApiError } from "@/lib/client-portal-api";
import { getDdaDocumentHash } from "@/lib/api/signing";

interface Props {
  projectId: string;
  totalMeasures: number;
  ready: boolean;
  onSigningComplete: () => void;
}


export function DdaSignFinalButton({
  projectId,
  totalMeasures,
  ready,
  onSigningComplete,
}: Props) {
  const [signingOpen, setSigningOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleStartSigning = async () => {
    setLoading(true);
    try {
      const hashResult = await getDdaDocumentHash(projectId);
      if (!hashResult.ready_for_signing) {
        toast.error(
          "La DdA aun no esta lista para firmar · revisa todas las medidas",
        );
        return;
      }
      setDocumentHash(hashResult.document_hash_sha256);
      setSigningOpen(true);
    } catch (err) {
      const msg =
        err instanceof ClientApiError
          ? err.message
          : "Error preparando firma. Reintenta.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="sticky bottom-4 mt-8 rounded-lg border-2 border-fulkro-success bg-fulkro-success/10 p-4 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-fulkro-success">
              Declaracion lista para firmar
            </p>
            <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
              Has revisado las {totalMeasures} medidas. La firma requiere
              un codigo enviado a tu email.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleStartSigning()}
            disabled={!ready || loading}
            className="inline-flex items-center gap-2 rounded-md bg-fulkro-success px-4 py-2 text-sm font-semibold text-white hover:bg-fulkro-success/90 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="h-4 w-4" />
            )}
            {loading ? "Preparando…" : "Firmar Declaracion de Aplicabilidad"}
          </button>
        </div>
      </div>

      {documentHash && (
        <SigningFlow
          open={signingOpen}
          onClose={() => {
            setSigningOpen(false);
            setDocumentHash(null);
          }}
          projectId={projectId}
          signableType="dda"
          signableLabel="Declaracion de Aplicabilidad ENS"
          documentHash={documentHash}
          intentPayload={{
            measures_total: totalMeasures,
            sign_context: "client_in_portal_dda_review",
          }}
          onSuccess={(signature) => {
            toast.success(
              `DdA firmada correctamente · ${new Date(
                signature.signed_at,
              ).toLocaleString("es-ES")}`,
              { duration: 5000 },
            );
            setSigningOpen(false);
            setDocumentHash(null);
            onSigningComplete();
          }}
        />
      )}
    </>
  );
}
