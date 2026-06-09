/**
 * ContractCanvasSignFlow · #43 · firma del contrato comercial con canvas Ed25519.
 *
 * Flow del dispatch /sign/[token] para purpose FIRMA_CONTRATO. El lead (SIN
 * cuenta · la firma crea al cliente #7) introduce el OTP recibido por canal
 * separado, dibuja su firma (canvas) y confirma. La firma:
 *   - se sella con Ed25519 + hash chain (m05),
 *   - promociona el proyecto + crea su cliente (#7) en una transacción atómica,
 *   - archiva el contrato firmado en IDMS.
 *
 * A diferencia de los otros flows (BaseSignFlow · botón aprobar/rechazar), éste
 * usa el canvas manuscrito (SignatureCanvas) y el endpoint público
 * /contract-signing/confirm (que hace consume + sign_canvas internamente).
 */
"use client";

import { BadgeCheck, FileText, Loader2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import {
  SignatureCanvas,
  type SignatureSubmitPayload,
} from "@/components/signatures/SignatureCanvas";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  confirmContractSignature,
  downloadContractPreview,
} from "@/lib/api/contract-signing";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

export function ContractCanvasSignFlow({
  token,
}: {
  token: string;
  status?: MagicLinkStatus;
}) {
  const [otp, setOtp] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [signed, setSigned] = React.useState(false);
  const [geo, setGeo] = React.useState<{ lat: number; lon: number } | null>(
    null,
  );
  const [previewing, setPreviewing] = React.useState(false);
  const [previewError, setPreviewError] = React.useState(false);

  // #34 (FRENTE B): descarga el contrato exacto a firmar (no se firma a ciegas).
  const handlePreview = async () => {
    if (!token) {
      toast.error("Enlace inválido: falta el token del contrato.");
      return;
    }
    setPreviewing(true);
    setPreviewError(false);
    try {
      await downloadContractPreview(token);
    } catch {
      setPreviewError(true);
    } finally {
      setPreviewing(false);
    }
  };

  React.useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => setGeo({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => setGeo(null),
      { timeout: 8000 },
    );
  }, []);

  const handleSubmit = async (payload: SignatureSubmitPayload) => {
    if (!token) {
      toast.error("Enlace inválido: falta el token del contrato.");
      return;
    }
    if (otp.trim().length < 4) {
      toast.error("Introduce el código OTP que recibiste por separado.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmContractSignature({
        token,
        otp: otp.trim(),
        signature_canvas_dataurl: payload.signature_canvas_dataurl,
        signed_name: payload.signed_name,
        signed_surname: payload.signed_surname,
        geo_lat: geo?.lat ?? null,
        geo_lon: geo?.lon ?? null,
      });
      setSigned(true);
      toast.success("Contrato firmado correctamente.");
    } catch {
      toast.error(
        "No se pudo firmar el contrato. Revisa el código OTP o vuelve a abrir el enlace.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (signed) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <BadgeCheck size={32} className="text-fulkro-success" />
          <h1 className="text-xl font-semibold text-fulkro-primary-700">
            Contrato firmado
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Tu firma quedó sellada criptográficamente (Ed25519). Recibirás el
            acceso a tu portal en breve. Gracias.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Firma de tu contrato de servicios FULKRO</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {/* #34 (FRENTE B): el cliente lee/descarga el contrato EXACTO ANTES de
            firmar (cierra el "contrato mudo" · WYSIWYS). */}
        <div className="flex flex-col gap-2 rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-3">
          <p className="text-sm text-fulkro-ink-700">
            Antes de firmar, revisa el documento exacto que vas a firmar.
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            disabled={previewing}
            onClick={handlePreview}
          >
            {previewing ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <FileText size={14} />
            )}
            <span className="ml-2">Ver / descargar el contrato</span>
          </Button>
          {previewError ? (
            <p className="text-xs text-fulkro-danger-700">
              No se pudo descargar el contrato. Vuelve a abrir el enlace o
              contacta con Fulkro.
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="otp" className="text-sm font-medium">
            Código de verificación (OTP)
          </label>
          <Input
            id="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="6 dígitos recibidos por separado"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            aria-label="Código OTP de verificación"
          />
        </div>
        {submitting ? (
          <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
            <Loader2 size={14} className="animate-spin" /> firmando…
          </div>
        ) : null}
        <SignatureCanvas
          documentLabel="Contrato comercial de servicios FULKRO"
          onSubmit={handleSubmit}
          isSubmitting={submitting}
          testIdPrefix="contract-signature"
        />
      </CardContent>
    </Card>
  );
}
