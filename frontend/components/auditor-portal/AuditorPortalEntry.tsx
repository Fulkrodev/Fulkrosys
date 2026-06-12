"use client";

/**
 * AuditorPortalEntry · token validation gate + OTP step-up + session start.
 *
 * Flow:
 * 1. GET metadata (peek · NO consume use).
 * 2. Si token_meta.otp_required → gate de OTP: el auditor introduce el código
 *    recibido por email; POST /session con el OTP (backend lo valida · mirror
 *    m08). Sin código válido NO entra al portal.
 * 3. Si no requiere OTP → auto POST /session en mount (comportamiento previo).
 * 4. Con la sesión arrancada → render AuditorPortalChrome.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, KeyRound, Loader2 } from "lucide-react";
import * as React from "react";

import { AuditorPortalChrome } from "@/components/auditor-portal/AuditorPortalChrome";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getAuditorPortalMetadata,
  startAuditorPortalSession,
  type AuditorPortalMetadata,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
  children: React.ReactNode;
}

export function AuditorPortalEntry({ token, children }: Props) {
  const meta = useQuery<AuditorPortalMetadata>({
    queryKey: ["auditor-portal", "metadata", token],
    queryFn: () => getAuditorPortalMetadata(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const [otp, setOtp] = React.useState("");
  const sessionMut = useMutation({
    mutationFn: (code?: string) => startAuditorPortalSession(token, code),
  });
  const sessionStartedRef = React.useRef(false);

  const otpRequired = Boolean(meta.data?.token_meta?.otp_required);

  React.useEffect(() => {
    // Auto-arranque SOLO si NO requiere OTP (si requiere, esperamos al gate).
    if (
      meta.data &&
      !otpRequired &&
      !sessionStartedRef.current &&
      !sessionMut.isPending &&
      !sessionMut.isSuccess
    ) {
      sessionStartedRef.current = true;
      sessionMut.mutate(undefined);
    }
  }, [meta.data, otpRequired, sessionMut]);

  if (meta.isLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50">
        <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Validando acceso al portal del auditor…
        </div>
      </div>
    );
  }

  if (meta.isError || !meta.data) {
    const errMsg =
      meta.error instanceof Error ? meta.error.message : "Error desconocido";
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50 px-4">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle size={16} className="text-fulkro-danger-700" />
              Acceso no disponible
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Alert variant="danger">
              <AlertTitle>Enlace inválido, revocado o expirado</AlertTitle>
              <AlertDescription>
                Si has llegado aquí desde un enlace recibido por correo, puede
                haber expirado o haberse revocado. Solicita un enlace nuevo al
                consultor responsable.
              </AlertDescription>
            </Alert>
            <p className="text-[11px] text-fulkro-ink-500">
              Detalle técnico: {errMsg}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Gate de OTP (step-up · feat/fulkro-100) ──
  if (otpRequired && !sessionMut.isSuccess) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50 px-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound size={16} /> Código de acceso
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p className="text-fulkro-ink-600">
              Introduzca el código de acceso de un solo uso que ha recibido
              junto al enlace en su correo.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (otp.trim().length >= 4) sessionMut.mutate(otp.trim());
              }}
              className="space-y-3"
            >
              <div className="space-y-1.5">
                <Label htmlFor="auditor-otp">Código de acceso</Label>
                <Input
                  id="auditor-otp"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  placeholder="Ej. 482913"
                  data-testid="auditor-otp-input"
                />
              </div>
              {sessionMut.isError && (
                <Alert variant="danger">
                  <AlertDescription>
                    Código incorrecto o caducado. Revíselo e inténtelo de nuevo.
                  </AlertDescription>
                </Alert>
              )}
              <Button
                type="submit"
                disabled={sessionMut.isPending || otp.trim().length < 4}
                className="w-full"
                data-testid="auditor-otp-submit"
              >
                {sessionMut.isPending ? "Comprobando…" : "Entrar al portal"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <AuditorPortalChrome token={token} metadata={meta.data}>
      {children}
    </AuditorPortalChrome>
  );
}
