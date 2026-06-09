/**
 * LegacyDocumentSignFlow · preserva el flujo de firma_documento +
 * aprobacion_acta tal como estaba antes de la multiplex FASE 4.5 sub-bloque B.2.
 *
 * Consume fixture local `mockSignPayload` vía `useQuery` directo ·
 * cleanup definitivo cuando backend exponga firma_documento +
 * aprobacion_acta purposes en /api/v1/magic-links/{token}/status
 * (TODO-FASE-X-MAGIC-LINK-PORTAL-INTEGRATION-001).
 *
 * SAN-B.MB-6.5: migración del hook legacy `useMagicLink` (eliminado)
 * a `useQuery` inline · preserva UX 1:1 + test E2E magic-link.spec.ts.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, FileSignature, Loader2, ShieldCheck } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { MagicLinkMeta } from "@/components/public/MagicLinkMeta";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { mockSignPayload } from "@/lib/public-portal-fixtures";
import type { SignDocumentPayload } from "@/lib/sprint4-types";

export function LegacyDocumentSignFlow({ token }: { token: string }) {
  const { data, isLoading } = useQuery<SignDocumentPayload>({
    queryKey: ["magic-link-legacy", "sign", token],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 120));
      return mockSignPayload(token);
    },
    enabled: !!token,
    staleTime: 60_000,
  });
  const [otp, setOtp] = React.useState("");
  const [accepted, setAccepted] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [signed, setSigned] = React.useState(false);

  if (isLoading || !data) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> validando enlace…
        </CardContent>
      </Card>
    );
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
            Tu firma Ed25519 quedó registrada. Marcos recibirá notificación
            inmediata.
          </p>
        </CardContent>
      </Card>
    );
  }

  async function submit() {
    if (data?.requires_otp && otp.length !== 6) {
      toast.error("Introduce el código OTP de 6 dígitos");
      return;
    }
    if (!accepted) {
      toast.error("Marca la casilla de conformidad");
      return;
    }
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 400));
    setSubmitting(false);
    setSigned(true);
  }

  return (
    <>
      <MagicLinkMeta context={data} />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileSignature size={16} /> Firma de documento
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs font-mono text-fulkro-ink-500">
              {data.document_code}
            </p>
            <h2 className="text-base font-semibold text-fulkro-primary-700">
              {data.document_title}
            </h2>
            <p className="text-xs text-fulkro-ink-500">
              Firmante: {data.signatory_role}
            </p>
          </div>

          <div className="max-h-48 overflow-y-auto rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/30 p-3 text-xs leading-relaxed text-fulkro-ink-700">
            {data.preview_snippet}
          </div>

          {data.requires_otp && (
            <div className="space-y-1.5">
              <label
                className="text-xs font-medium text-fulkro-ink-700"
                htmlFor="otp"
              >
                Código OTP recibido por WhatsApp
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
              He leído el documento y firmo conforme. Acepto que mi firma
              quede registrada con hash Ed25519 y fecha en el audit log de
              FULKRO.
            </span>
          </label>

          <Button
            type="button"
            className="w-full"
            size="lg"
            onClick={submit}
            disabled={
              submitting ||
              (data.requires_otp && otp.length !== 6) ||
              !accepted
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
    </>
  );
}
