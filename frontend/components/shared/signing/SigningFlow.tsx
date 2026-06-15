"use client";

/**
 * SigningFlow · component reusable in-portal cliente firma · SAN-E v3.MB-5.3.C.
 *
 * 6 estados FSM:
 *   confirm → otp_pending → otp_input → signing → success
 *   confirm → signing → success (si !requires_step_up_otp)
 *   any → error
 *
 * Backend wire-up M05 signing service:
 * - createSigningIntent (atom 5.2)
 * - requestStepUpOtp + verifyStepUpOtp (atom 5.2.bis · email out-of-band)
 * - signIntent (Ed25519 + hash chain · atom 5.2)
 *
 * Reusable across signable_types: dda · magerit · pentest · conformidad ·
 * acta · retainer · policy · incident · dpc · renewal · document_generic.
 *
 * Pattern: useState (NO TanStack Query · alineado client-portal existing).
 */
import { useState } from "react";
import { AlertCircle, Loader2, Mail, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  createSigningIntent,
  requestStepUpOtp,
  signIntent,
  verifyStepUpOtp,
  type SignableType,
  type SignedDocumentResponse,
} from "@/lib/api/signing";

type FlowStep =
  | "confirm"
  | "otp_pending"
  | "otp_input"
  | "signing"
  | "success"
  | "error";

interface Props {
  open: boolean;
  onClose: () => void;
  projectId: string;
  signableType: SignableType;
  signableLabel: string;
  documentHash: string;
  documentId?: string;
  signableRefId?: string;
  signableRefType?: string;
  intentPayload?: Record<string, unknown>;
  onSuccess: (signature: SignedDocumentResponse) => void;
}


function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ClientApiError) return err.message;
  if (err instanceof Error) return err.message;
  return fallback;
}


export function SigningFlow(props: Props) {
  const [step, setStep] = useState<FlowStep>("confirm");
  const [intentId, setIntentId] = useState<string | null>(null);
  const [requiresOtp, setRequiresOtp] = useState(false);
  const [maskedEmail, setMaskedEmail] = useState<string>("");
  const [otpCode, setOtpCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  // §2.7 audit-2026-06-15 · guard de operación en vuelo: sin esto un doble-click en
  // "Continuar firma"/"Verificar y firmar" durante el await creaba 2 intents.
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setStep("confirm");
    setIntentId(null);
    setRequiresOtp(false);
    setMaskedEmail("");
    setOtpCode("");
    setError(null);
    setBusy(false);
  };

  const handleClose = () => {
    reset();
    props.onClose();
  };

  const handleStartFlow = async () => {
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      const intent = await createSigningIntent({
        project_id: props.projectId,
        signable_type: props.signableType,
        document_hash_sha256: props.documentHash,
        document_id: props.documentId,
        signable_ref_id: props.signableRefId,
        signable_ref_type: props.signableRefType,
        intent_payload: props.intentPayload,
      });
      setIntentId(intent.id);
      setRequiresOtp(intent.requires_step_up_otp);

      if (intent.requires_step_up_otp) {
        setStep("otp_pending");
        const otpResult = await requestStepUpOtp(intent.id);
        setMaskedEmail(otpResult.sent_to_email_masked);
        setStep("otp_input");
      } else {
        setStep("signing");
        const signResult = await signIntent(intent.id);
        setStep("success");
        props.onSuccess(signResult);
      }
    } catch (err) {
      setError(errorMessage(err, "Error iniciando firma"));
      setStep("error");
    } finally {
      setBusy(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (!intentId || busy) return;
    if (otpCode.length !== 6) {
      setError("Introduce los 6 digitos del codigo");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await verifyStepUpOtp(intentId, otpCode);
      if (!result.otp_verified) {
        setError("Codigo incorrecto. Reintenta.");
        return;
      }
      setStep("signing");
      const signResult = await signIntent(intentId);
      setStep("success");
      props.onSuccess(signResult);
    } catch (err) {
      const msg = errorMessage(err, "Error verificando codigo");
      // §2.7 · límite de intentos → detectar por STATUS 429 (robusto), con el
      // string-match como respaldo (antes sólo string-match · frágil a traducción).
      const status = (err as { status?: number } | null)?.status;
      if (status === 429 || msg.toLowerCase().includes("max otp attempts")) {
        toast.error(
          "Demasiados intentos · solicita un nuevo codigo en unos minutos",
        );
        handleClose();
        return;
      }
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const renderConfirm = () => (
    <div className="space-y-4">
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Vas a firmar este documento con firma electronica simple
          (eIDAS Art 25.1). La accion es irreversible · tu firma Ed25519
          queda registrada en el audit log (cadena de integridad SHA-256).
          {requiresOtp && (
            <span className="mt-2 block">
              Por seguridad, te enviaremos un codigo a tu email para
              confirmar.
            </span>
          )}
        </AlertDescription>
      </Alert>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={handleClose} disabled={busy}>
          Cancelar
        </Button>
        <Button onClick={() => void handleStartFlow()} disabled={busy}>
          {busy ? "Procesando…" : "Continuar firma"}
        </Button>
      </div>
    </div>
  );

  const renderOtpPending = () => (
    <div className="py-8 text-center">
      <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin" />
      <p className="text-sm text-[color:var(--fulkro-muted)]">
        Enviando codigo a tu email…
      </p>
    </div>
  );

  const renderOtpInput = () => (
    <div className="space-y-4">
      <Alert>
        <Mail className="h-4 w-4" />
        <AlertDescription>
          Hemos enviado un codigo de 6 digitos a{" "}
          <strong>{maskedEmail}</strong>. Caduca en 5 minutos.
        </AlertDescription>
      </Alert>
      <div>
        <Label htmlFor="otp-input">Codigo de seguridad</Label>
        <Input
          id="otp-input"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="\d{6}"
          maxLength={6}
          placeholder="123456"
          value={otpCode}
          onChange={(e) =>
            setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
          }
          className="mt-2 text-center font-mono text-2xl tracking-widest"
          autoFocus
        />
      </div>
      {error && (
        <Alert variant="danger">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={handleClose}>
          Cancelar
        </Button>
        <Button
          onClick={() => void handleVerifyOtp()}
          disabled={busy || otpCode.length !== 6}
        >
          {busy ? "Firmando…" : "Verificar y firmar"}
        </Button>
      </div>
    </div>
  );

  const renderSigning = () => (
    <div className="py-8 text-center">
      <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin" />
      <p className="text-sm text-[color:var(--fulkro-muted)]">
        Generando firma criptografica…
      </p>
    </div>
  );

  const renderSuccess = () => (
    <div className="space-y-4 py-4 text-center">
      <div className="mx-auto w-fit rounded-full bg-fulkro-success/15 p-3">
        <ShieldCheck className="h-6 w-6 text-fulkro-success" />
      </div>
      <div>
        <h3 className="font-semibold">Documento firmado correctamente</h3>
        <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
          La firma ha quedado registrada en el audit log con sello
          Ed25519 · cadena criptografica intacta.
        </p>
      </div>
      <Button onClick={handleClose} className="w-full">
        Cerrar
      </Button>
    </div>
  );

  const renderError = () => (
    <div className="space-y-4">
      <Alert variant="danger">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error ?? "Error desconocido"}</AlertDescription>
      </Alert>
      <Button onClick={handleClose} className="w-full">
        Cerrar
      </Button>
    </div>
  );

  return (
    <Dialog
      open={props.open}
      onOpenChange={(o) => {
        if (!o) handleClose();
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Firmar {props.signableLabel}
          </DialogTitle>
          <DialogDescription>
            Tu firma queda registrada en el audit log con sello criptografico
            Ed25519 · trazabilidad RD 311/2022 art. 21.
          </DialogDescription>
        </DialogHeader>

        {step === "confirm" && renderConfirm()}
        {step === "otp_pending" && renderOtpPending()}
        {step === "otp_input" && renderOtpInput()}
        {step === "signing" && renderSigning()}
        {step === "success" && renderSuccess()}
        {step === "error" && renderError()}
      </DialogContent>
    </Dialog>
  );
}
