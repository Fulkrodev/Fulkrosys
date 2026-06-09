"use client";

/**
 * MageritSignValidationButton · sticky bottom · firma magerit_validation.
 *
 * SAN-E v3.MB-5.4.C · drop-in SigningFlow pattern atom 5.3.C.
 * Cambia signableType="magerit_validation" · reusa OTP email + chain.
 */
import { useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { ClientApiError } from "@/lib/client-portal-api";
import { getMageritClientDocumentHash } from "@/lib/api/magerit";


interface Props {
  projectId: string;
  totalAssets: number;
  totalRisks: number;
  ready: boolean;
  onSigningComplete: () => void;
}


export function MageritSignValidationButton({
  projectId,
  totalAssets,
  totalRisks,
  ready,
  onSigningComplete,
}: Props) {
  const [signingOpen, setSigningOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleStartSigning = async () => {
    setLoading(true);
    try {
      const hashResult = await getMageritClientDocumentHash(projectId);
      if (!hashResult.ready_for_signing) {
        toast.error(
          "MAGERIT aun no esta listo · revisa todos los activos y riesgos",
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
              Inventario y análisis riesgos listos para validar
            </p>
            <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
              Has revisado {totalAssets} activos y {totalRisks} riesgos. La
              validación requiere un código enviado a tu email.
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
            {loading ? "Preparando…" : "Validar inventario MAGERIT"}
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
          signableType="magerit_validation"
          signableLabel="Validacion inventario MAGERIT"
          documentHash={documentHash}
          intentPayload={{
            assets_total: totalAssets,
            risks_total: totalRisks,
            sign_context: "client_in_portal_magerit_validation",
          }}
          onSuccess={(signature) => {
            toast.success(
              `MAGERIT validado · ${new Date(
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
