/**
 * DocumentSigningFlow · firma REAL de un documento ENS (acta E-012 de
 * categorización, informe MAGERIT E-028, DdA E-040, conformidad…) vía magic-link
 * FIRMA_DOCUMENTO. Reemplaza al LegacyDocumentSignFlow (mock que fingía la firma
 * con setTimeout SIN registrar nada, pese a prometer "firma Ed25519 registrada").
 *
 * §3.1 audit-2026-06-15 · flujo real: el firmante (Responsable de la
 * Información/Servicio, Dirección, RSEG) revisa el documento, introduce el OTP
 * recibido por canal aparte, marca conformidad y firma → POST
 * /api/v1/document-signing/sign, que consume el magic-link (valida OTP/caducidad/
 * usos) y registra su firma Ed25519 sobre el hash congelado del snapshot (m05 ·
 * hash chain R6).
 */
"use client";

import { BadgeCheck, FileSignature, Loader2, ShieldCheck } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { signDocument } from "@/lib/api/document-signing";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

// Etiqueta legible del documento según el discriminador del scope. El backend
// resuelve el SignableType; aquí sólo elegimos el texto que ve el firmante.
const DOC_LABELS: Record<string, string> = {
  acta_e012: "Acta de categorización (E-012)",
  informe_e028_magerit: "Informe de análisis MAGERIT (E-028)",
  dda_e040_rseg: "Declaración de Aplicabilidad (DdA · E-040)",
};

export function DocumentSigningFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as Record<string, unknown>;
  const docType = (scope.document_type as string) || "";
  const titulo =
    DOC_LABELS[docType] ||
    (scope.title as string) ||
    (scope.doc_titulo as string) ||
    "Documento";
  const firmante =
    (scope.recipient_name as string) ||
    (scope.recipient_role as string) ||
    "";
  const requiresOtp =
    (status as { requires_otp?: boolean }).requires_otp ?? true;

  const [otp, setOtp] = React.useState("");
  const [accepted, setAccepted] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [signed, setSigned] = React.useState(false);

  async function submit() {
    if (requiresOtp && otp.length !== 6) {
      toast.error("Introduce el código OTP de 6 dígitos.");
      return;
    }
    if (!accepted) {
      toast.error("Marca la casilla de conformidad.");
      return;
    }
    setSubmitting(true);
    try {
      await signDocument({ token, otp: requiresOtp ? otp : null, accepted: true });
      setSigned(true);
      toast.success("Documento firmado.");
    } catch {
      toast.error(
        "No se pudo firmar el documento. Revisa el código OTP o vuelve a abrir el enlace.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (signed) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <BadgeCheck size={32} className="text-fulkro-success" />
          <h1 className="text-xl font-semibold text-fulkro-primary-700">
            Documento firmado
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Tu firma quedó registrada con hash Ed25519 y fecha en el audit log de
            FULKRO. Gracias.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileSignature size={16} /> Firma de documento
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-fulkro-primary-700">
            {titulo}
          </h2>
          {firmante ? (
            <p className="text-xs text-fulkro-ink-500">Firmante: {firmante}</p>
          ) : null}
        </div>

        {requiresOtp && (
          <div className="space-y-1.5">
            <label
              className="text-xs font-medium text-fulkro-ink-700"
              htmlFor="otp"
            >
              Código OTP recibido por canal aparte
            </label>
            <Input
              id="otp"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              value={otp}
              onChange={(e) =>
                setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              className="text-center font-mono text-lg tracking-[0.4em]"
              placeholder="000000"
              aria-label="Código OTP de firma del documento"
            />
          </div>
        )}

        <label className="flex items-start gap-2 text-xs text-fulkro-ink-700">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            He leído el documento y firmo conforme. Acepto que mi firma quede
            registrada con hash Ed25519 y fecha en el audit log de FULKRO.
          </span>
        </label>

        <Button
          type="button"
          className="w-full"
          size="lg"
          onClick={submit}
          disabled={
            submitting || (requiresOtp && otp.length !== 6) || !accepted
          }
        >
          {submitting ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ShieldCheck size={14} />
          )}
          Firmar con Ed25519
        </Button>
      </CardContent>
    </Card>
  );
}
