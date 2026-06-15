/**
 * ApproveActaFlow · aprobación/firma REAL del acta (E-005) vía magic-link
 * APROBACION_ACTA. Reemplaza al LegacyDocumentSignFlow (mock que fingía la
 * firma con setTimeout sin registrar nada).
 *
 * Flujo real: el asistente revisa el acta (código + su rol), introduce el OTP
 * recibido por canal separado, marca conformidad y aprueba → POST
 * /api/v1/minutes-signing/approve, que consume el magic-link (valida OTP/
 * caducidad/usos) y registra su firma en committee_meetings.firmas (m18).
 */
"use client";

import { BadgeCheck, FileSignature, Loader2, ShieldCheck } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { approveActa } from "@/lib/api/minutes-signing";
import type { MagicLinkStatus } from "@/lib/magic-link-types";

export function ApproveActaFlow({
  token,
  status,
}: {
  token: string;
  status: MagicLinkStatus;
}) {
  const scope = (status.scope ?? {}) as Record<string, unknown>;
  const codigo = (scope.codigo as string) || "Acta de reunión";
  const asistente = (scope.asistente_nombre as string) || "";
  const requiresOtp = (status as { requires_otp?: boolean }).requires_otp ?? true;

  const [otp, setOtp] = React.useState("");
  const [accepted, setAccepted] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [approved, setApproved] = React.useState(false);

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
      await approveActa({ token, otp: requiresOtp ? otp : null, accepted: true });
      setApproved(true);
      toast.success("Acta aprobada y firmada.");
    } catch {
      toast.error(
        "No se pudo aprobar el acta. Revisa el código OTP o vuelve a abrir el enlace.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (approved) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <BadgeCheck size={32} className="text-fulkro-success" />
          <h1 className="text-xl font-semibold text-fulkro-primary-700">
            Acta aprobada
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Tu aprobación quedó registrada en el acta. Gracias.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileSignature size={16} /> Aprobación del acta
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs font-mono text-fulkro-ink-500">{codigo}</p>
            {asistente ? (
              <p className="text-xs text-fulkro-ink-500">Asistente: {asistente}</p>
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
                aria-label="Código OTP de aprobación del acta"
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
              He revisado el acta y la apruebo. Acepto que mi aprobación quede
              registrada con fecha en el acta y en el audit log de FULKRO.
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
            Aprobar acta
          </Button>
        </CardContent>
    </Card>
  );
}
