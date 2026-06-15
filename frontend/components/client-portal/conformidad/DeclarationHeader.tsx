"use client";

/**
 * DeclarationHeader · tier-aware text BASICA vs MEDIA/ALTA.
 *
 * SAN-E v3.MB-5.6.D · workflow_label + next_step_post_signature backend driven.
 */
import { Award, FileSignature } from "lucide-react";

import type { ConformidadDeclarationClientView } from "@/lib/api/conformidad";


interface Props {
  declaration: ConformidadDeclarationClientView;
}


const TIER_BADGES: Record<string, { label: string; className: string }> = {
  BASICA: {
    label: "Categoría BÁSICA",
    className: "bg-fulkro-info/10 text-fulkro-info",
  },
  MEDIA: {
    label: "Categoría MEDIA",
    className: "bg-fulkro-warning/10 text-fulkro-warning",
  },
  ALTA: {
    label: "Categoría ALTA",
    className: "bg-fulkro-danger/10 text-fulkro-danger",
  },
};


// Medidas aplicables del Anexo II RD 311/2022 por categoría (BOE-A-2022-7191):
// BÁSICA 52 · MEDIA 68 · ALTA 73 (el total de 73 sólo aplica a ALTA). Antes el
// copy decía "73 medidas" para TODAS las categorías → impreciso legalmente en la
// declaración del cliente.
const MEDIDAS_POR_CATEGORIA: Record<string, number> = {
  BASICA: 52,
  MEDIA: 68,
  ALTA: 73,
};

export function DeclarationHeader({ declaration }: Props) {
  const tierBadge = TIER_BADGES[declaration.tier] ?? {
    label: declaration.tier,
    className: "bg-fulkro-ink-100 text-[color:var(--fulkro-muted)]",
  };

  const isBasica = declaration.declaration_type === "initial";
  const Icon = isBasica ? Award : FileSignature;
  const medidasCount = MEDIDAS_POR_CATEGORIA[declaration.tier] ?? 73;

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-3">
        <Icon className="h-6 w-6 text-fulkro-primary-700" />
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${tierBadge.className}`}
        >
          {tierBadge.label}
        </span>
      </div>

      <h2 className="mb-2 text-xl font-semibold text-[color:var(--fulkro-title)]">
        {declaration.workflow_label}
      </h2>

      <p className="text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
        {isBasica ? (
          <>
            Esta firma <strong>certifica</strong> que tu organización cumple
            las {medidasCount} medidas del Anexo II del Real Decreto 311/2022
            (ENS) aplicables a tu categoría. Tras firmar generaremos
            automáticamente tu distintivo de conformidad y tu identificador de
            certificación.
          </>
        ) : (
          <>
            Esta firma documenta tu <strong>compromiso</strong> de cumplir las
            {" "}{medidasCount} medidas del Anexo II del ENS aplicables a tu
            categoría. Tras firmar, Marcos enviará tu dossier al auditor ENAC
            acreditado para la certificación formal.
          </>
        )}
      </p>

      {/* #2 Ola 7 · quién firma · muchas PYMEs no saben que firma la Dirección */}
      {declaration.signer_explanation && (
        <div
          className="mt-3 flex gap-2 rounded-md border border-fulkro-info/30 bg-fulkro-info/5 p-3 text-sm leading-relaxed text-[color:var(--fulkro-body)]"
          data-testid="declaration-signer-explanation"
        >
          <FileSignature className="mt-0.5 h-4 w-4 shrink-0 text-fulkro-info" />
          <span>{declaration.signer_explanation}</span>
        </div>
      )}
    </section>
  );
}
