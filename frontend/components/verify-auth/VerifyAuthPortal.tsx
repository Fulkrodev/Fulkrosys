"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  Mail,
  ShieldCheck,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getVerifyAuthData,
  requestVerifyAuthOtp,
  submitVerifyAuth,
} from "@/lib/api/public-portals";
import type {
  VerifyAuthData,
  VerifyAuthSignResponse,
} from "@/lib/public-portals-types";
import { formatDate } from "@/lib/utils";

export function VerifyAuthPortal({ token }: { token: string }) {
  const [data, setData] = React.useState<VerifyAuthData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const [accepted, setAccepted] = React.useState(false);
  const [otp, setOtp] = React.useState("");
  const [otpRequested, setOtpRequested] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [signed, setSigned] =
    React.useState<VerifyAuthSignResponse | null>(null);

  React.useEffect(() => {
    getVerifyAuthData(token)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        setError((e as Error).message);
        setLoading(false);
      });
  }, [token]);

  async function requestOtp() {
    try {
      const r = await requestVerifyAuthOtp(token);
      setOtpRequested(true);
      toast.success(`OTP enviado por ${r.delivery_method}`, {
        description: "El código expira en 10 minutos",
      });
    } catch (e) {
      toast.error("No se pudo solicitar el OTP", {
        description: (e as Error).message,
      });
    }
  }

  async function submit() {
    if (!accepted) return;
    setSubmitting(true);
    try {
      const result = await submitVerifyAuth(token, {
        accepted_legal: true,
        otp: otp || undefined,
      });
      setSigned(result);
      toast.success("Autorización firmada");
    } catch (e) {
      toast.error("No se pudo autorizar", {
        description: (e as Error).message,
      });
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex h-40 items-center justify-center gap-2 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> Cargando autorización…
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-fulkro-danger">
          No se pudo cargar la autorización. El enlace puede estar caducado,
          revocado, o ya ha sido firmado.
          <p className="mt-2 text-xs text-fulkro-ink-500">Detalle: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (signed) {
    return (
      <Card className="border-fulkro-success/40 bg-fulkro-success/5">
        <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
          <CheckCircle2 size={48} className="text-fulkro-success" />
          <h2 className="text-xl font-semibold text-fulkro-primary-700">
            Verificación autorizada
          </h2>
          <p className="text-sm text-fulkro-ink-700">
            Firmada el <strong>{formatDate(signed.signed_at)}</strong> para el
            run <code className="font-mono text-[11px]">{signed.run_id.slice(0, 8)}…</code>.
          </p>
          <p className="rounded bg-fulkro-ink-100/60 px-3 py-1 font-mono text-[11px] text-fulkro-ink-500">
            Hash SHA-256 de la firma:{" "}
            <span className="font-semibold">{signed.signature_hash}</span>
          </p>
          {signed.expected_completion && (
            <p className="text-xs text-fulkro-ink-500">
              Recibirás el informe el{" "}
              {formatDate(signed.expected_completion)}.
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  const disabled = !accepted || (data.requires_otp && !otp);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck size={18} className="text-fulkro-primary-700" />
            Autorización de verificación técnica
          </CardTitle>
          <p className="text-sm text-fulkro-ink-500">
            {data.cliente.razon_social} · solicitud como RSEG
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <dl className="grid gap-2 md:grid-cols-2">
            <Field label="Categoría ENS" value={data.run.category} />
            <Field
              label="Modo"
              value={
                data.run.mode === "internal"
                  ? "Interno"
                  : data.run.mode === "external"
                    ? "Externo"
                    : data.run.mode
              }
            />
            <Field
              label="Ventana ejecución"
              value={data.run.scope.scan_window}
            />
            {data.run.scheduled_start && (
              <Field
                label="Inicio programado"
                value={formatDate(data.run.scheduled_start)}
              />
            )}
          </dl>

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Objetivos autorizados
            </p>
            <ul className="mt-1 flex flex-wrap gap-1">
              {data.run.scope.targets.map((t) => (
                <li
                  key={t}
                  className="rounded bg-fulkro-primary-700/10 px-2 py-0.5 font-mono text-[11px]"
                >
                  {t}
                </li>
              ))}
            </ul>
          </div>

          {data.run.scope.web_apps.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
                Aplicaciones web
              </p>
              <ul className="mt-1 flex flex-wrap gap-1">
                {data.run.scope.web_apps.map((t) => (
                  <li
                    key={t}
                    className="rounded bg-fulkro-primary-700/10 px-2 py-0.5 font-mono text-[11px]"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Herramientas a usar
            </p>
            <ul className="mt-1 flex flex-wrap gap-1">
              {data.run.tools.map((t) => (
                <li
                  key={t}
                  className="rounded bg-fulkro-ink-100 px-2 py-0.5 font-mono text-[11px] text-fulkro-ink-700"
                >
                  {t}
                </li>
              ))}
            </ul>
          </div>

          {data.run.scope.exclusions.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
                Exclusiones
              </p>
              <ul className="mt-1 flex flex-wrap gap-1">
                {data.run.scope.exclusions.map((t) => (
                  <li
                    key={t}
                    className="rounded bg-fulkro-ink-100 px-2 py-0.5 font-mono text-[11px]"
                  >
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-fulkro-warning/40 bg-fulkro-warning/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-fulkro-warning">
            <AlertTriangle size={16} /> Declaración legal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-fulkro-ink-700">
            {data.legal_statement}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              aria-describedby="accept-helper"
              className="mt-1"
            />
            <span>
              He leído y acepto la declaración legal. Autorizo la ejecución de
              la verificación en los términos descritos.
            </span>
          </label>

          {data.requires_otp && (
            <div className="flex flex-col gap-2">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <Label htmlFor="otp-input">
                    Código de un solo uso (OTP de 6 dígitos)
                  </Label>
                  <Input
                    id="otp-input"
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(e) =>
                      setOtp(e.target.value.replace(/[^0-9]/g, ""))
                    }
                    placeholder="000000"
                    autoComplete="one-time-code"
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={requestOtp}
                  className="gap-1"
                  disabled={otpRequested}
                >
                  <Mail size={14} />
                  {otpRequested ? "Reenviado" : "Reenviar OTP"}
                </Button>
              </div>
              <p id="otp-helper" className="text-xs text-fulkro-ink-500">
                El código ha sido enviado al email registrado. Si no lo
                recibes, pulsa &quot;Reenviar OTP&quot;.
              </p>
            </div>
          )}

          <Button
            onClick={submit}
            disabled={disabled || submitting}
            className="gap-2"
          >
            {submitting ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <ClipboardCheck size={14} />
            )}
            Autorizar verificación
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
        {label}
      </dt>
      <dd className="font-mono text-sm text-fulkro-primary-700">{value}</dd>
    </div>
  );
}
