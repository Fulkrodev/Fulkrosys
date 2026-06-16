/**
 * /sign/[token] · multiplex sign-flow per backend purpose.
 *
 * FASE 4.5 sub-bloque B.2 · multiplex extension:
 * - useMagicLinkStatus (real backend) resuelve el purpose del link.
 * - Switch sobre tipo_operacion → componente sign-flow específico:
 *   · firma_documento → DocumentSigningFlow (Ed25519 real · m05 hash chain)
 *   · aprobacion_acta → ApproveActaFlow (firma del asistente · m18)
 *   · aprobacion_propuesta → ApprovePropuestaFlow
 *   · aprobacion_factura → ApproveFacturaFlow
 *   · validacion_cambio_alcance → ValidateScopeChangeFlow
 *   · aceptacion_riesgo_residual → AcceptResidualRiskFlow
 *   · consentimiento_tratamiento_datos → SignDPAFlow
 *   · confirmacion_conformidad → ConfirmConformidadFlow
 *
 * Si el endpoint backend devuelve 404 (token inválido/expirado o inexistente),
 * se muestra una página de error honesta (NO un formulario de firma falso).
 */
"use client";

import { Loader2 } from "lucide-react";
import { redirect } from "next/navigation";

import { AcceptResidualRiskFlow } from "@/components/sign-flows/AcceptResidualRiskFlow";
import { ApproveActaFlow } from "@/components/sign-flows/ApproveActaFlow";
import { ApproveFacturaFlow } from "@/components/sign-flows/ApproveFacturaFlow";
import { ApprovePropuestaFlow } from "@/components/sign-flows/ApprovePropuestaFlow";
import { ConfirmConformidadFlow } from "@/components/sign-flows/ConfirmConformidadFlow";
import { ContractCanvasSignFlow } from "@/components/sign-flows/ContractCanvasSignFlow";
import { DocumentSigningFlow } from "@/components/sign-flows/DocumentSigningFlow";
import { SignDPAFlow } from "@/components/sign-flows/SignDPAFlow";
import { ValidateScopeChangeFlow } from "@/components/sign-flows/ValidateScopeChangeFlow";
import { Card, CardContent } from "@/components/ui/card";
import { useMagicLinkStatus } from "@/hooks/magic-link";

export default function SignTokenPage({
  params,
}: {
  params: { token: string };
}) {
  const token = params.token;
  const { data: status, isLoading, isError } = useMagicLinkStatus(token);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> validando enlace…
        </CardContent>
      </Card>
    );
  }

  // Token no resuelto por el backend (inválido/expirado o inexistente):
  // página de error honesta. Antes caía a un mock de firma (LegacyDocumentSignFlow),
  // ya borrado: un enlace inválido NO debe mostrar un formulario de firma falso.
  if (isError || !status) {
    return (
      <Card>
        <CardContent className="space-y-2 p-6 text-sm">
          <p className="font-semibold text-fulkro-ink-700">
            Enlace no válido o expirado
          </p>
          <p className="text-xs text-fulkro-ink-500">
            El enlace de firma no pudo procesarse. Solicita uno nuevo o
            contacta con tu responsable del proyecto.
          </p>
        </CardContent>
      </Card>
    );
  }

  switch (status.tipo_operacion) {
    case "aprobacion_acta":
      // Flujo REAL (reemplaza el mock LegacyDocumentSignFlow): consume el
      // magic-link + registra la firma del asistente en el acta (m18).
      return <ApproveActaFlow token={token} status={status} />;
    case "firma_documento":
      // §3.1 · flujo REAL (reemplaza el mock LegacyDocumentSignFlow): consume el
      // magic-link + registra la firma Ed25519 del documento (acta E-012 /
      // MAGERIT E-028 / DdA E-040 / conformidad · m05 hash chain R6).
      return <DocumentSigningFlow token={token} status={status} />;
    case "aprobacion_propuesta":
      return <ApprovePropuestaFlow token={token} status={status} />;
    case "aprobacion_factura":
      return <ApproveFacturaFlow token={token} status={status} />;
    case "validacion_cambio_alcance":
      return <ValidateScopeChangeFlow token={token} status={status} />;
    case "aceptacion_riesgo_residual":
      return <AcceptResidualRiskFlow token={token} status={status} />;
    case "consentimiento_tratamiento_datos":
      return <SignDPAFlow token={token} status={status} />;
    case "confirmacion_conformidad":
      return <ConfirmConformidadFlow token={token} status={status} />;
    case "firma_contrato":
      return <ContractCanvasSignFlow token={token} status={status} />;
    // Portales token-gated NO-firma. El builder universal m12 (service.py:317)
    // entrega TODO purpose como /ml/consume?token= → /sign/{token}; reenviar
    // estos al portal correcto en vez de caer al "no soportado" (cierra el
    // dead-end de acceso por email · auditor ENAC, pentester, remediación).
    case "auditor_portal_enac":
      redirect(`/auditor-portal/${encodeURIComponent(token)}/summary`);
    case "portal_pentester_externo":
      redirect(`/pentester-portal/${encodeURIComponent(token)}`);
    case "portal_remediacion":
      redirect(`/remediation/${encodeURIComponent(token)}`);
    default:
      return (
        <Card>
          <CardContent className="space-y-2 p-6 text-sm">
            <p className="font-semibold text-fulkro-ink-700">
              Tipo de operación no soportado en esta página
            </p>
            <p className="text-xs text-fulkro-ink-500">
              Este enlace ({status.tipo_operacion}) corresponde a otra
              funcionalidad. Contacte con su responsable del proyecto si
              necesita avanzar.
            </p>
          </CardContent>
        </Card>
      );
  }
}
