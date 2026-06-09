/**
 * SignFlowDisclaimer · disclaimer compartido para los sign-flows ADR-011.
 *
 * Wording neutro confirmado por Marcos (FASE 4.5 sub-bloque B.2):
 * sin referencias a eIDAS / Reglamento (UE) 910/2014 / artículo 26
 * (FASE 0 ya eliminó esos términos del repo).
 *
 * Reusable por todos los flujos de firma/aprobación (ApprovePropuestaFlow,
 * ApproveFacturaFlow, ValidateScopeChangeFlow, AcceptResidualRiskFlow,
 * SignDPAFlow, ConfirmConformidadFlow).
 */

interface SignFlowDisclaimerProps {
  /** Frase contextual (ej: "su aprobación de la propuesta"). */
  actionLabel: string;
  /** Código del item (ej: "P-001-2026") · opcional. */
  itemReference?: string;
  /** Nota legal específica del purpose (ej: RGPD para DPA) · opcional. */
  legalNote?: string;
}

export function SignFlowDisclaimer({
  actionLabel,
  itemReference,
  legalNote,
}: SignFlowDisclaimerProps) {
  return (
    <div className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/30 p-4 text-sm text-fulkro-ink-600">
      <p>
        Mediante esta confirmación queda registrada {actionLabel}
        {itemReference ? (
          <>
            {" "}
            (<span className="font-mono">{itemReference}</span>)
          </>
        ) : null}
        {" "}en el expediente del proyecto, junto con el timestamp del
        servidor, la dirección IP de origen y el código de verificación
        introducido.
      </p>
      <p className="mt-2">
        Esta confirmación tiene efectos formales según se detalla en el
        contrato del proyecto.
      </p>
      {legalNote ? (
        <p className="mt-2 text-xs text-fulkro-ink-500">{legalNote}</p>
      ) : null}
    </div>
  );
}
