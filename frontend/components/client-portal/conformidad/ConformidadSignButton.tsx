"use client";

/**
 * ConformidadSignButton · sticky bottom · firma conformidad_ens (step-up OTP).
 *
 * SAN-E v3.MB-5.6.D · drop-in SigningFlow pattern atom 5.3.C / 5.4.C / 5.5.D.
 * signableType="conformidad_ens" (REQUIRES_STEP_UP_OTP en signable_types.py).
 *
 * Readiness gate: client_reviewed_at + readiness.ready_for_conformity_sign.
 */
import { useState } from "react";
import { Award, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SigningFlow } from "@/components/shared/signing/SigningFlow";
import { getConformidadDocumentHash } from "@/lib/api/conformidad";
import { ClientApiError } from "@/lib/client-portal-api";


interface Props {
  projectId: string;
  declarationId: string;
  tier: string;
  declarationType: string;
  reviewed: boolean;
  readyForSign: boolean;
  onSigningComplete: () => void;
}


export function ConformidadSignButton({
  projectId,
  declarationId,
  tier,
  declarationType,
  reviewed,
  readyForSign,
  onSigningComplete,
}: Props) {
  const [signingOpen, setSigningOpen] = useState(false);
  const [documentHash, setDocumentHash] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isBasica = declarationType === "initial";
  const buttonLabel = isBasica
    ? "Firmar declaración ENS"
    : "Firmar compromiso conformidad";
  const signableLabel = isBasica
    ? "Declaración Conformidad ENS final (E-041)"
    : "Compromiso conformidad pre-auditoría ENAC";

  const handleStartSigning = async () => {
    setLoading(true);
    try {
      const hashResult = await getConformidadDocumentHash(projectId);
      if (!hashResult.ready_for_signing) {
        toast.error(
          "Conformidad NO lista · revisa los bloqueos y marca como revisado primero",
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
      <div className="sticky bottom-4 mt-2 rounded-lg border-2 border-fulkro-success bg-fulkro-success/10 p-4 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-fulkro-success">
              {isBasica
                ? `Conformidad ENS ${tier} lista para firmar`
                : `Compromiso ${tier} listo para firmar`}
            </p>
            <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
              La firma requiere un código enviado a tu email (paso de
              seguridad adicional).
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleStartSigning()}
            disabled={!reviewed || !readyForSign || loading}
            className="inline-flex items-center gap-2 rounded-md bg-fulkro-success px-4 py-2 text-sm font-semibold text-white hover:bg-fulkro-success/90 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Award className="h-4 w-4" />
            )}
            {loading ? "Preparando…" : buttonLabel}
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
          signableType="conformidad_ens"
          signableLabel={signableLabel}
          documentHash={documentHash}
          signableRefId={declarationId}
          signableRefType="basic_declaration"
          intentPayload={{
            declaration_id: declarationId,
            declaration_type: declarationType,
            tier,
            sign_context: "client_in_portal_conformidad_ens",
          }}
          onSuccess={(signature) => {
            toast.success(
              `Conformidad firmada · ${new Date(
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
