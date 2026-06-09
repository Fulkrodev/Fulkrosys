"use client";

/**
 * WhatsAppOTPVerifyCard · MB-8 atom 8.3 Q3.D step 2.
 *
 * Cliente introduces OTP recibido via WA · valida.
 */
import { CheckCircle2, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { verifyOtp } from "@/lib/api/whatsapp";


interface Props {
  phoneE164: string;
  onVerified: () => void;
}


export function WhatsAppOTPVerifyCard({ phoneE164, onVerified }: Props) {
  const [otp, setOtp] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const r = await verifyOtp(otp);
      if (r.verified) onVerified();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "OTP inválido o expirado",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-700" />
          Introduce el código
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-[color:var(--fulkro-body)]">
          Hemos enviado un código de 6 dígitos a{" "}
          <strong>{phoneE164}</strong>. Tienes 10 minutos para introducirlo.
        </p>
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Código</span>
            <input
              type="text"
              required
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 8))}
              placeholder="123456"
              className="rounded-md border px-3 py-2 text-center text-lg font-mono tracking-widest"
              data-testid="whatsapp-otp-input"
            />
          </label>
          {error && (
            <p className="rounded-md border border-rose-300/40 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-700">
              {error}
            </p>
          )}
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={submitting || otp.length < 4}
            data-testid="whatsapp-verify-otp"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Verificar
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
