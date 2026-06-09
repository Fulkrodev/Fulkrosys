"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2, Lock, Mail, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  ClientApiError,
  clientApi,
  type ClientLoginResponse,
} from "@/lib/client-portal-api";

type MfaErrorPayload = {
  detail?: { requires_mfa?: boolean; mfa_method?: string } | string;
};

/** Devuelve el método MFA ('email'|'totp') si el error es un challenge MFA, o null. */
function mfaChallengeMethod(err: ClientApiError): string | null {
  if (err.status !== 401) return null;
  const detail = (err.data as MfaErrorPayload | null)?.detail;
  if (typeof detail === "object" && detail !== null && detail.requires_mfa === true) {
    return detail.mfa_method || "email";
  }
  return null;
}

export default function ClientLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [mfaMethod, setMfaMethod] = useState<string>("email");
  const [resent, setResent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const body: Record<string, string> = { email, password };
      if (step === "mfa") body.mfa_code = mfaCode;
      const resp = await clientApi<ClientLoginResponse>("/client-auth/login", {
        json: body,
      });
      if (resp.must_change_password) {
        router.push("/client-portal/account?force_change=1");
      } else {
        router.push("/client-portal/dashboard");
      }
    } catch (err) {
      if (err instanceof ClientApiError) {
        const method = mfaChallengeMethod(err);
        if (method) {
          // 2026-06-09 · method='email' → el backend ya envió el código al email.
          setMfaMethod(method);
          setStep("mfa");
          setError(null);
        } else {
          setError(err.message);
        }
      } else {
        setError("Error de conexión");
      }
    } finally {
      setLoading(false);
    }
  }

  // Reenviar el código: re-lanza el paso 1 (email+password · sin código) → el
  // backend re-emite y reenvía el código por email. El 401 requires_mfa es lo
  // esperado (no es error).
  async function handleResend() {
    setError(null);
    setResent(false);
    setLoading(true);
    try {
      await clientApi<ClientLoginResponse>("/client-auth/login", {
        json: { email, password },
      });
    } catch (err) {
      if (err instanceof ClientApiError && mfaChallengeMethod(err)) {
        setResent(true);
      } else if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Error de conexión");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fulkro-auth-bg relative -mb-16 flex min-h-dvh flex-col md:-mb-24">
      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-10">
        <div className="grid w-full max-w-6xl items-center gap-10 md:grid-cols-2 md:gap-20">
          <div className="hidden items-center justify-center md:flex">
            <Image
              src="/brand/fulkro-logo-light.svg"
              alt="FULKRO"
              width={1200}
              height={320}
              priority
              className="w-full max-w-[620px] drop-shadow-[0_8px_28px_rgba(46,41,128,0.18)]"
            />
          </div>

          <div className="mx-auto w-full max-w-md space-y-6">
            <div className="flex flex-col items-center gap-5 md:hidden">
              <Image
                src="/brand/fulkro-logo-light.svg"
                alt="FULKRO"
                width={1200}
                height={320}
                priority
                className="w-full max-w-[340px]"
              />
            </div>
            <div className="text-center">
              <h1 className="text-4xl font-extrabold tracking-tight text-fulkro-primary-700">
                Portal Cliente
              </h1>
              <p className="mt-3 flex items-center justify-center gap-1.5 text-lg font-semibold text-fulkro-ink-700">
                Acceso seguro a tu proyecto <TooltipENS term="ENS" />.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="card space-y-4 p-6">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fulkro-ink-500"
                  />
                  <Input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    disabled={loading}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fulkro-ink-500"
                  />
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    autoComplete="current-password"
                    disabled={loading}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>

              {step === "mfa" && (
                <div className="space-y-2" data-testid="login-mfa-step">
                  <Label htmlFor="mfa_code" className="flex items-center gap-2">
                    <ShieldCheck size={14} /> Código de verificación
                  </Label>
                  <Input
                    id="mfa_code"
                    inputMode="numeric"
                    pattern="\d{6}"
                    maxLength={10}
                    autoFocus
                    autoComplete="one-time-code"
                    disabled={loading}
                    value={mfaCode}
                    onChange={(e) =>
                      setMfaCode(e.target.value.replace(/[^0-9a-zA-Z]/g, ""))
                    }
                  />
                  {mfaMethod === "email" ? (
                    <>
                      <p className="text-xs text-muted-foreground">
                        Te hemos enviado un código de 6 dígitos a tu email.
                        Escríbelo aquí para entrar.
                      </p>
                      <button
                        type="button"
                        onClick={handleResend}
                        disabled={loading}
                        className="text-xs font-medium text-fulkro-primary-600 underline disabled:opacity-50"
                        data-testid="login-mfa-resend"
                      >
                        ¿No te ha llegado? Reenviar código
                      </button>
                      {resent && (
                        <p
                          className="text-xs text-fulkro-success-700"
                          aria-live="polite"
                        >
                          Te hemos enviado un código nuevo.
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Introduce el código de 6 dígitos de tu app autenticadora ·
                      o un código de respaldo si no tienes el teléfono a mano.
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

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={loading || (step === "mfa" && mfaCode.length < 6)}
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Accediendo…
                  </>
                ) : step === "mfa" ? (
                  <>Verificar</>
                ) : (
                  <>Entrar</>
                )}
              </Button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
