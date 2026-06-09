"use client";

import { useRouter } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { startAuthentication } from "@simplewebauthn/browser";
import { Loader2, Mail, Lock, KeyRound, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { resolvePostLoginRedirect } from "@/lib/auth/redirect";
import { ROUTES } from "@/lib/constants";
import type {
  LoginResponse,
  MeResponse,
  MfaVerifyResponse,
} from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth-store";

const loginSchema = z.object({
  email: z.string().email({ message: "Email no válido" }),
  password: z.string().min(1, "Introduce tu contraseña"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

type Stage =
  | { kind: "password" }
  | { kind: "webauthn"; mfaTicket: string; options: LoginResponse["webauthn"] }
  | { kind: "totp"; mfaTicket: string }
  | { kind: "bootstrap"; mfaTicket: string };

export function LoginForm() {
  const router = useRouter();
  const setUser = useAuthStore((s) => s.setUser);
  const setCsrf = useAuthStore((s) => s.setCsrf);
  const [stage, setStage] = React.useState<Stage>({ kind: "password" });
  const [totpCode, setTotpCode] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onPasswordSubmit(values: LoginFormValues) {
    setBusy(true);
    try {
      const res = await api<LoginResponse>("/api/v1/auth/login", {
        json: values,
      });
      if (res.webauthn_available && res.webauthn) {
        setStage({
          kind: "webauthn",
          mfaTicket: res.mfa_ticket,
          options: res.webauthn,
        });
      } else if (res.totp_available) {
        setStage({ kind: "totp", mfaTicket: res.mfa_ticket });
      } else {
        setStage({ kind: "bootstrap", mfaTicket: res.mfa_ticket });
      }
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 429
          ? "Demasiados intentos. Espera 15 minutos."
          : err instanceof ApiError && err.status === 423
            ? "Cuenta bloqueada temporalmente (30 min)."
            : "Credenciales inválidas";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  async function onWebAuthn(mfaTicket: string, options: LoginResponse["webauthn"]) {
    setBusy(true);
    try {
      if (!options?.publicKey) {
        throw new Error("Opciones WebAuthn ausentes");
      }
      const credential = await startAuthentication(
        options.publicKey as Parameters<typeof startAuthentication>[0],
      );
      const resp = await api<MfaVerifyResponse>(
        "/api/v1/auth/webauthn/verify",
        {
          json: {
            mfa_ticket: mfaTicket,
            credential_id: credential.id,
            client_data_json: credential.response.clientDataJSON,
            authenticator_data: credential.response.authenticatorData,
            signature: credential.response.signature,
          },
        },
      );
      await completeLogin(resp.csrf_token);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? "Verificación WebAuthn fallida"
          : err instanceof Error
            ? err.message
            : "WebAuthn cancelado";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  async function onTotpSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (stage.kind !== "totp") return;
    setBusy(true);
    try {
      const resp = await api<MfaVerifyResponse>("/api/v1/auth/totp/verify", {
        json: { mfa_ticket: stage.mfaTicket, code: totpCode },
      });
      await completeLogin(resp.csrf_token);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Código TOTP inválido";
      toast.error(message);
    } finally {
      setBusy(false);
    }
  }

  async function completeLogin(csrf: string) {
    setCsrf(csrf);
    let me: MeResponse | null = null;
    try {
      me = await api<MeResponse>("/api/v1/auth/me");
      setUser(me);
    } catch {
      /* /me fetch is best-effort; AuthGuard will re-check */
    }
    toast.success("Sesión iniciada");

    // Redirect role-based con sanitización del next param.
    // Si /me falló, mandar a login default (caso degenerado: el JWT
    // se setearía bien pero no podemos consultar role; AuthGuard
    // re-check al cargar el portal recogerá el user). Como fallback
    // razonable, mandar a /admin/dashboard (la página más común
    // en el LoginForm admin) y dejar que middleware/AuthGuard
    // redirijan si el role no es owner.
    const params = new URLSearchParams(window.location.search);
    const nextParam = params.get("next");
    const target = me
      ? resolvePostLoginRedirect(me.role, nextParam)
      : ROUTES.dashboard;
    router.replace(target);
  }

  return (
    <div className="space-y-6">
      {stage.kind === "password" && (
        <form
          onSubmit={form.handleSubmit(onPasswordSubmit)}
          className="space-y-4"
        >
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
                autoComplete="email"
                disabled={busy}
                className="pl-9"
                placeholder="marcosmata@fulkro.es"
                {...form.register("email")}
              />
            </div>
            {form.formState.errors.email && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.email.message}
              </p>
            )}
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
                autoComplete="current-password"
                disabled={busy}
                className="pl-9"
                placeholder="••••••••••••••••"
                {...form.register("password")}
              />
            </div>
            {form.formState.errors.password && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.password.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" size="lg" disabled={busy}>
            {busy ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Comprobando…
              </>
            ) : (
              <>Acceder</>
            )}
          </Button>
        </form>
      )}

      {stage.kind === "webauthn" && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/40 p-4">
            <ShieldCheck size={22} className="text-fulkro-primary-700" />
            <div>
              <p className="font-medium text-fulkro-ink-700">
                Acerca tu Yubikey
              </p>
              <p className="text-sm text-fulkro-ink-500">
                Pulsa el botón del dispositivo cuando parpadee.
              </p>
            </div>
          </div>
          <Button
            className="w-full"
            size="lg"
            disabled={busy}
            onClick={() => onWebAuthn(stage.mfaTicket, stage.options)}
          >
            {busy ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Verificando…
              </>
            ) : (
              <>Acceder con Yubikey</>
            )}
          </Button>
          <button
            type="button"
            className="block w-full text-center text-sm text-fulkro-info hover:underline"
            onClick={() =>
              setStage({ kind: "totp", mfaTicket: stage.mfaTicket })
            }
            disabled={busy}
          >
            Usar código TOTP en su lugar
          </button>
        </div>
      )}

      {stage.kind === "totp" && (
        <form onSubmit={onTotpSubmit} className="space-y-4">
          <div className="flex items-start gap-3 rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/40 p-4">
            <KeyRound size={22} className="text-fulkro-primary-700" />
            <div>
              <p className="font-medium text-fulkro-ink-700">Código TOTP</p>
              <p className="text-sm text-fulkro-ink-500">
                6 dígitos desde tu autenticador.
              </p>
            </div>
          </div>
          <Input
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            autoFocus
            disabled={busy}
            value={totpCode}
            onChange={(e) =>
              setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
            }
            className="text-center font-mono text-xl tracking-[0.5em]"
            placeholder="000000"
          />
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={busy || totpCode.length !== 6}
          >
            {busy ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Verificando…
              </>
            ) : (
              <>Validar código</>
            )}
          </Button>
        </form>
      )}

      {stage.kind === "bootstrap" && (
        <div className="space-y-3 rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 p-4 text-sm">
          <p className="font-medium text-fulkro-warning">
            MFA no configurado
          </p>
          <p className="text-fulkro-ink-500">
            Esta cuenta aún no tiene Yubikey ni TOTP enrolados. Ejecuta el
            script de bootstrap en el servidor para enrolar TOTP:
          </p>
          <pre className="rounded bg-fulkro-ink-100 px-3 py-2 font-mono text-xs text-fulkro-ink-700 overflow-auto">
            PYTHONPATH=. python3 backend/scripts/bootstrap_marcos_totp.py
          </pre>
          <p className="text-fulkro-ink-500">
            Después vuelve aquí y escanea el QR en tu autenticador.
          </p>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => setStage({ kind: "password" })}
          >
            Volver
          </Button>
        </div>
      )}
    </div>
  );
}
