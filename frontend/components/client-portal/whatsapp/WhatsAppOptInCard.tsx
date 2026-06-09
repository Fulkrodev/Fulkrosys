"use client";

/**
 * WhatsAppOptInCard · MB-8 atom 8.3 Q3.D.
 *
 * Step 1 of opt-in · cliente introduces phone E.164 + button send OTP.
 */
import { Loader2, MessageCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { verifyPhone } from "@/lib/api/whatsapp";


interface Props {
  onOtpSent: (phoneE164: string) => void;
}


export function WhatsAppOptInCard({ onOtpSent }: Props) {
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const r = await verifyPhone(phone);
      if (r.otp_sent) {
        onOtpSent(r.phone_e164);
      } else {
        setError(r.error || "No se ha podido enviar el código");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error envío");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5 text-emerald-600" />
          Verificar WhatsApp
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-[color:var(--fulkro-body)]">
          Introduce tu número de WhatsApp para recibir notificaciones críticas
          de FULKRO. Te enviaremos un código de 6 dígitos para verificar.
        </p>
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Número WhatsApp</span>
            <input
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+34 666 555 444"
              className="rounded-md border px-3 py-2 text-sm"
              data-testid="whatsapp-phone-input"
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
            disabled={submitting || !phone.trim()}
            data-testid="whatsapp-send-otp"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Enviar código
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
