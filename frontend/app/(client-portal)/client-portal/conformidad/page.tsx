"use client";

/**
 * /client-portal/conformidad · cliente firma conformidad ENS tier-aware.
 *
 * SAN-E v3.MB-5.6 · audit-driven Escenario X (BasicDeclarationRow reuse).
 * - BASICA → E-041 self-declaration + distintivo
 * - MEDIA/ALTA → compromiso pre-auditoría ENAC
 *
 * Single page scroll · 6 sections tier-aware UX:
 * 1. ReadinessSection · checklist visual pre-firma
 * 2. DeclarationHeader · tier badge + workflow_label + intro text
 * 3. DeclarationSummarySection · responsible + contacto
 * 4. TierAwareNextStepSection · qué pasa después de firmar
 * 5. MarkReviewedSection · review + concerns
 * 6. PostSignSection (post-firma) · distintivo BASICA o commitment MEDIA/ALTA
 *
 * Sticky bottom: ConformidadSignButton drop-in SigningFlow.
 */
import { ConformidadSignButton } from "@/components/client-portal/conformidad/ConformidadSignButton";
import { DeclarationHeader } from "@/components/client-portal/conformidad/DeclarationHeader";
import { DeclarationSummarySection } from "@/components/client-portal/conformidad/DeclarationSummarySection";
import { MarkReviewedSection } from "@/components/client-portal/conformidad/MarkReviewedSection";
import { PostSignSection } from "@/components/client-portal/conformidad/PostSignSection";
import { ReadinessSection } from "@/components/client-portal/conformidad/ReadinessSection";
import { TierAwareNextStepSection } from "@/components/client-portal/conformidad/TierAwareNextStepSection";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useConformidadClient } from "@/hooks/useConformidadClient";


export default function ClientConformidadPage() {
  const {
    loading,
    error,
    projectId,
    declaration,
    readiness,
    notFound,
    markReviewed,
    refetch,
  } = useConformidadClient();

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Cargando conformidad ENS…
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <div className="rounded-md border border-fulkro-danger/30 bg-fulkro-danger/10 px-4 py-3 text-sm font-medium text-fulkro-danger">
          {error}
        </div>
      </main>
    );
  }

  if (notFound || !declaration) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <header className="mb-6">
          <h1
            aria-label="Conformidad ENS"
            className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[color:var(--fulkro-title)]"
          >
            Conformidad <TooltipENS term="ENS" />
          </h1>
        </header>

        {readiness && (
          <div className="mb-6">
            <ReadinessSection readiness={readiness} />
          </div>
        )}

        <p className="rounded-md border bg-card px-4 py-6 text-center text-sm text-[color:var(--fulkro-muted)]">
          Marcos aún no ha preparado tu declaración de conformidad. Completa
          los pasos previos arriba (<TooltipENS term="DdA" /> ·{" "}
          <TooltipENS term="MAGERIT" /> · pentest) y Marcos preparará tu
          declaración para que la firmes.
        </p>
      </main>
    );
  }

  const isSigned = declaration.signed_at !== null;
  const isReviewed = declaration.client_reviewed_at !== null;
  const readyForSign = readiness?.ready_for_conformity_sign ?? false;

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1
          aria-label="Conformidad ENS"
          className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[color:var(--fulkro-title)]"
        >
          Conformidad <TooltipENS term="ENS" />
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
          Última etapa del proceso <TooltipENS term="ENS" />. Revisa el estado
          de preparación, el responsable y el cronograma · firma con paso de
          seguridad adicional.
        </p>
      </header>

      <div className="space-y-5">
        {isSigned && projectId ? (
          <PostSignSection projectId={projectId} />
        ) : (
          <>
            {readiness && <ReadinessSection readiness={readiness} />}

            <AgentSuggestionBanner
              slug="a11_auditor_virtual_check"
              pageUrl="/client-portal/conformidad"
              dismissKey="conformidad_auditor_dismissed"
              tierGatedNote="Verificación de inconsistencias por el auditor virtual disponible desde categoría MEDIA."
            />

            <DeclarationHeader declaration={declaration} />

            <DeclarationSummarySection declaration={declaration} />

            <TierAwareNextStepSection declaration={declaration} />

            <MarkReviewedSection
              reviewedAt={declaration.client_reviewed_at}
              concernsNote={declaration.client_concerns_note}
              onMarkReviewed={markReviewed}
            />

            {projectId && (
              <ConformidadSignButton
                projectId={projectId}
                declarationId={declaration.id}
                tier={declaration.tier}
                declarationType={declaration.declaration_type}
                reviewed={isReviewed}
                readyForSign={readyForSign}
                onSigningComplete={() => void refetch()}
              />
            )}
          </>
        )}
      </div>
    </main>
  );
}
