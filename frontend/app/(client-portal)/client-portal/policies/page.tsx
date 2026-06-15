"use client";

/**
 * /client-portal/policies · SAN-E v3.MB-6 atom 1.
 *
 * CCN-STIC 805 cliente in-portal workflow:
 *  1. Header tier-aware · progress bar
 *  2. Accordion per familia (mitigación 25 cards fatiga UX)
 *  3. PolicyRow per policy · review individual (revisada_ok/con_pregunta/suggest_change)
 *  4. PolicyBulkSignButton sticky bottom · firma bulk única
 *
 * Q1.C híbrida: review individual + firma bulk una vez (audit ENAC + UX).
 */
import { AlertCircle, Info, ShieldCheck } from "lucide-react";

import { PolicyBulkSignButton } from "@/components/client-portal/policies/PolicyBulkSignButton";
import { PolicyFamilyAccordion } from "@/components/client-portal/policies/PolicyFamilyAccordion";
import { PolicyHeader } from "@/components/client-portal/policies/PolicyHeader";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { usePoliciesClient } from "@/hooks/usePoliciesClient";

export default function PoliciesPage() {
  const { loading, error, projectId, summary, policies, reviewPolicy, refetch } =
    usePoliciesClient();

  return (
    <PageContainer variant="reading">
      <div className="space-y-6 pb-32">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <ShieldCheck className="h-5 w-5" aria-hidden />
          <span className="flex items-center gap-1.5 text-xs uppercase tracking-wide font-semibold">
            Portal cliente · Políticas <TooltipENS term="ENS" />
          </span>
        </div>
        <h1 className="text-2xl font-bold text-fulkro-ink-800">
          Mis políticas de seguridad
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Tu consultor redactó las políticas obligatorias{" "}
          <TooltipENS term="CCN_STIC_805" /> (PSI nivel 1 + Normativas nivel 2 +
          procedimientos) para tu organización. Revisa cada una · si tienes
          dudas abre una pregunta · firma todas a la vez con una única firma
          electrónica al final.
        </p>
      </header>

      {/* Banner R30 inverso · 1.D.F.bis.III.A v3.11 */}
      <Alert data-testid="cliente-policies-banner">
        <Info className="size-4" />
        <AlertTitle>Marcos redactó las políticas y procedimientos</AlertTitle>
        <AlertDescription>
          Tu papel es revisar el contenido · firmar la versión final cuando
          estés conforme. Si algo no queda claro o quieres sugerir un cambio,
          usa el botón &quot;Con pregunta&quot; / &quot;Sugerir cambio&quot; en
          cada política · Marcos lo revisará y te responderá desde el chat.
        </AlertDescription>
      </Alert>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      )}

      {error && (
        <Card className="p-5 border-destructive/40 bg-destructive/5">
          <div className="flex items-start gap-2 text-sm">
            <AlertCircle
              className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0"
              aria-hidden
            />
            <div>
              <div className="font-semibold text-destructive">
                Error cargando políticas
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && summary && projectId && (
        <>
          <PolicyHeader summary={summary} />

          <AgentSuggestionBanner
            slug="a11_auditor_virtual_check"
            pageUrl="/client-portal/policies"
            dismissKey="policies_auditor_dismissed"
            tierGatedNote="Sugerencias IA del auditor disponibles desde categoría MEDIA."
          />

          {summary.generated_count < summary.expected_count && (
            <Card className="p-4 border-fulkro-info/40 bg-fulkro-info/10">
              <div className="text-sm text-fulkro-info">
                El consultor todavía está redactando algunas políticas
                ({summary.generated_count}/{summary.expected_count}). Las
                pendientes aparecerán automáticamente cuando estén listas.
              </div>
            </Card>
          )}

          <PolicyFamilyAccordion
            policies={policies}
            onReview={reviewPolicy}
            disabled={summary.bulk_signed}
          />

          <PolicyBulkSignButton
            projectId={projectId}
            tier={summary.tier}
            expectedCount={summary.expected_count}
            ready={summary.ready_for_bulk_sign}
            alreadySigned={summary.bulk_signed}
            onSigningComplete={refetch}
          />
        </>
      )}
      </div>
    </PageContainer>
  );
}
