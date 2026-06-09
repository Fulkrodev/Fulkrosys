"use client";

/**
 * Verificación en 2 pasos del cliente · POR CÓDIGO AL EMAIL (2026-06-09).
 *
 * Sustituye el TOTP ("más rollo" · app autenticadora + QR) por un código de 6
 * dígitos que enviamos al email del cliente y que teclea. Cliente-mínimo · R29
 * friendly · NO admin lingo · sin presión · WCAG 2.1 AA.
 *
 * Flujo: idle → (Activar) emailStart envía código → (code) emailConfirm activa.
 * Desactivar: directo (sesión autenticada · no pide código).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, ShieldCheck, Mail } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clientMfaApi } from "@/lib/api/client-mfa";

type Step = "idle" | "code";

export default function ClientMfaSettingsPage() {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>("idle");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["client-mfa-status"],
    queryFn: () => clientMfaApi.status(),
  });

  const start = useMutation({
    mutationFn: () => clientMfaApi.emailStart(),
    onSuccess: () => {
      setStep("code");
      setError(null);
      setResent(false);
    },
    onError: (err: Error) => setError(err.message),
  });

  const resend = useMutation({
    mutationFn: () => clientMfaApi.emailStart(),
    onSuccess: () => {
      setResent(true);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const confirm = useMutation({
    mutationFn: (c: string) => clientMfaApi.emailConfirm(c),
    onSuccess: () => {
      setStep("idle");
      setCode("");
      setError(null);
      void qc.invalidateQueries({ queryKey: ["client-mfa-status"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const disable = useMutation({
    mutationFn: () => clientMfaApi.disable(),
    onSuccess: () => {
      setStep("idle");
      setCode("");
      setError(null);
      void qc.invalidateQueries({ queryKey: ["client-mfa-status"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const verified = statusQuery.data?.mfa_enabled ?? false;
  const email = statusQuery.data?.email ?? "tu email";

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="mb-2 text-2xl font-bold">Verificación en 2 pasos</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Una capa extra de seguridad para entrar al portal: al iniciar sesión te
        enviamos un código a tu email y lo escribes. Sin apps ni complicaciones ·
        puedes activarla o desactivarla cuando quieras, sin prisa por tu parte.
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-fulkro-primary-600" />
            Estado actual
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {statusQuery.isLoading && (
            <p className="text-sm text-muted-foreground" aria-live="polite">
              Cargando…
            </p>
          )}
          {statusQuery.data && (
            <div data-testid="mfa-status">
              {verified ? (
                <div className="flex items-start gap-3 rounded-md border border-fulkro-success/30 bg-fulkro-success/10 p-3">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-fulkro-success-700" />
                  <div>
                    <p className="font-medium text-fulkro-success-700">
                      Activada
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Al entrar te enviaremos un código a <strong>{email}</strong>.
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No tienes activada la verificación en 2 pasos.
                </p>
              )}
            </div>
          )}

          {error && (
            <p
              role="alert"
              className="rounded-md border border-fulkro-danger/30 bg-fulkro-danger/10 px-3 py-2 text-sm text-fulkro-danger"
            >
              {error}
            </p>
          )}

          {step === "idle" && !verified && (
            <Button
              onClick={() => start.mutate()}
              disabled={start.isPending}
              data-testid="mfa-enable-btn"
            >
              {start.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Enviando código…
                </>
              ) : (
                <>Activar verificación en 2 pasos</>
              )}
            </Button>
          )}

          {step === "idle" && verified && (
            <Button
              variant="outline"
              onClick={() => disable.mutate()}
              disabled={disable.isPending}
              data-testid="mfa-disable-cta"
            >
              {disable.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Desactivando…
                </>
              ) : (
                <>Desactivar</>
              )}
            </Button>
          )}

          {step === "code" && (
            <div className="space-y-4" data-testid="mfa-code-step">
              <div className="flex items-start gap-3 rounded-md border border-fulkro-primary-200 bg-fulkro-primary-50 p-3">
                <Mail className="mt-0.5 h-5 w-5 text-fulkro-primary-600" />
                <p className="text-sm">
                  Te hemos enviado un código de 6 dígitos a{" "}
                  <strong>{email}</strong>. Escríbelo aquí para activar la
                  verificación.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="mfa-code-input">Código del email</Label>
                <Input
                  id="mfa-code-input"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="\d{6}"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  data-testid="mfa-code-input"
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => confirm.mutate(code)}
                    disabled={code.length !== 6 || confirm.isPending}
                    data-testid="mfa-confirm-btn"
                  >
                    {confirm.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />{" "}
                        Verificando…
                      </>
                    ) : (
                      <>Confirmar</>
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => resend.mutate()}
                    disabled={resend.isPending}
                    data-testid="mfa-resend-btn"
                  >
                    {resend.isPending ? "Reenviando…" : "Reenviar código"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setStep("idle");
                      setCode("");
                      setError(null);
                    }}
                  >
                    Cancelar
                  </Button>
                </div>
                {resent && (
                  <p className="text-sm text-fulkro-success-700" aria-live="polite">
                    Te hemos enviado un código nuevo.
                  </p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
