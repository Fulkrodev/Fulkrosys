/**
 * BaseSignFlow · esqueleto reusable para los 6 sign-flow components
 * de FASE 4.5 sub-bloque B.2 (ApprovePropuesta, ApproveFactura,
 * ValidateScopeChange, AcceptResidualRisk, SignDPA, ConfirmConformidad).
 *
 * Responsabilidades:
 * - Render Card + título + icono + summary slot (children)
 * - Render SignFlowDisclaimer
 * - OTP input cuando requires_otp (deriva de MAGIC_LINK_OTP_REQUIRED)
 * - Justificación opcional para rechazos
 * - Mutación useMagicLinkConsume con success/error states
 *
 * Cada flow específico (ApprovePropuestaFlow etc.) compone este esqueleto
 * pasando el scope parsed contextualizado.
 */
"use client";

import { BadgeCheck, Loader2, ShieldCheck } from "lucide-react";
import * as React from "react";
import { type LucideIcon } from "lucide-react";

import { SignFlowDisclaimer } from "@/components/sign-flows/SignFlowDisclaimer";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fulkroToast } from "@/lib/toast";
import {
  MAGIC_LINK_OTP_REQUIRED,
  type MagicLinkBackendPurpose,
  type MagicLinkStatus,
} from "@/lib/magic-link-types";
import { useMagicLinkConsume } from "@/hooks/magic-link";

export interface BaseSignFlowProps {
  token: string;
  status: MagicLinkStatus;
  /** Texto del icono + título del Card (ej: "Aprobación de propuesta"). */
  title: string;
  /** Icono lucide-react del Card header. */
  icon: LucideIcon;
  /** Etiqueta de la acción para el disclaimer (ej: "su aprobación de la propuesta"). */
  actionLabel: string;
  /** Código del item (ej: "P-001-2026") · opcional. */
  itemReference?: string;
  /** Nota legal específica · opcional. */
  legalNote?: string;
  /** Texto del botón de acción positiva (ej: "Aprobar propuesta"). */
  approveLabel: string;
  /** Texto del botón de rechazo (ej: "Rechazar"). */
  rejectLabel?: string;
  /** Si la decisión negativa requiere justificación obligatoria. */
  requireRejectJustification?: boolean;
  /** Mensaje de éxito tras consumir el link. */
  successMessage: string;
  /** Resumen contextual del scope · render en el body. */
  children: React.ReactNode;
}

export function BaseSignFlow({
  token,
  status,
  title,
  icon: Icon,
  actionLabel,
  itemReference,
  legalNote,
  approveLabel,
  rejectLabel = "Rechazar",
  requireRejectJustification = true,
  successMessage,
  children,
}: BaseSignFlowProps) {
  const requiresOtp = MAGIC_LINK_OTP_REQUIRED.has(
    status.tipo_operacion as MagicLinkBackendPurpose,
  );

  const [otp, setOtp] = React.useState("");
  const [decision, setDecision] = React.useState<"approve" | "reject" | null>(null);
  const [justificacion, setJustificacion] = React.useState("");
  const [done, setDone] = React.useState(false);

  const consume = useMagicLinkConsume(token);

  async function submit(decisionValue: "approve" | "reject") {
    if (requiresOtp && otp.length !== 6) {
      fulkroToast.error("Introduce el código de verificación de 6 dígitos");
      return;
    }
    if (
      decisionValue === "reject" &&
      requireRejectJustification &&
      justificacion.trim().length < 5
    ) {
      fulkroToast.error("Indique brevemente el motivo del rechazo");
      return;
    }
    setDecision(decisionValue);
    try {
      await consume.mutateAsync({
        otp: requiresOtp ? otp : undefined,
        decision: decisionValue,
        justificacion: justificacion.trim() || undefined,
      });
      setDone(true);
      fulkroToast.success(successMessage);
    } catch (err) {
      fulkroToast.error("No se pudo registrar la confirmación", {
        description: err instanceof Error ? err.message : undefined,
      });
      setDecision(null);
    }
  }

  if (done) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <BadgeCheck size={32} className="text-fulkro-success" />
          <h1 className="text-xl font-semibold text-fulkro-primary-700">
            {decision === "approve" ? "Confirmado" : "Decisión registrada"}
          </h1>
          <p className="text-sm text-fulkro-ink-500">{successMessage}</p>
        </CardContent>
      </Card>
    );
  }

  const submitting = consume.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon size={16} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {children}

        <SignFlowDisclaimer
          actionLabel={actionLabel}
          itemReference={itemReference}
          legalNote={legalNote}
        />

        {requiresOtp ? (
          <div className="space-y-1.5">
            <label
              htmlFor="otp"
              className="text-xs font-medium text-fulkro-ink-700"
            >
              Código de verificación
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
        ) : null}

        <div className="space-y-1.5">
          <label
            htmlFor="justificacion"
            className="text-xs font-medium text-fulkro-ink-700"
          >
            Justificación (obligatoria si rechaza)
          </label>
          <textarea
            id="justificacion"
            value={justificacion}
            onChange={(e) => setJustificacion(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-fulkro-ink-300/60 bg-white p-2 text-sm focus:border-fulkro-primary-500 focus:outline-none focus:ring-1 focus:ring-fulkro-primary-500"
            placeholder="Indique cualquier comentario o motivo de rechazo…"
          />
        </div>

        <div className="flex gap-2">
          <Button
            type="button"
            className="flex-1"
            size="lg"
            onClick={() => submit("approve")}
            disabled={submitting || (requiresOtp && otp.length !== 6)}
          >
            {submitting && decision === "approve" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <ShieldCheck size={14} />
            )}
            {approveLabel}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="lg"
            onClick={() => submit("reject")}
            disabled={submitting}
          >
            {rejectLabel}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
