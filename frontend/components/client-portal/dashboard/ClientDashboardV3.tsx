"use client";

/**
 * ClientDashboardV3 · MB-7 atom 7.1 plan v6.
 *
 * Adaptive client dashboard · 3 zones:
 *   1) Hero adaptativo (greeting + tier + phase + countdown)
 *   2) "Tu trabajo de hoy" (max 5 actions priorizadas)
 *   3) Resumen visual (workflow + messages + docs + invoice)
 *
 * Q5.2 + Q5.3 plan v6 cement: NO role dimension. Same view for all
 * users of the client.
 */
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { Skeleton } from "@/components/ui/skeleton";
import { useClientDashboard } from "@/hooks/useClientDashboard";

import { DocumentsCountCard } from "./DocumentsCountCard";
import { HeroAdaptativo } from "./HeroAdaptativo";
import { MessagesPreviewCard } from "./MessagesPreviewCard";
import { TodayActionsCards } from "./TodayActionsCards";
import { UpcomingInvoiceCard } from "./UpcomingInvoiceCard";
import { WorkflowStepperCard } from "./WorkflowStepperCard";

export function ClientDashboardV3() {
  const { data, loading, error, refetch } = useClientDashboard();

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8 md:px-6 md:py-10">
        <div className="rounded-xl border border-rose-300/40 bg-rose-500/10 px-5 py-4 text-base font-semibold text-rose-700">
          {error}
          <button
            type="button"
            onClick={() => void refetch()}
            className="ml-3 rounded bg-rose-500 px-3 py-1 text-sm font-bold text-white"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div
        className="mx-auto max-w-6xl space-y-4 px-4 py-8 md:px-6 md:py-10"
        data-testid="dashboard-loading"
      >
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <main
      className="mx-auto max-w-6xl space-y-6 px-4 py-6 md:px-6 md:py-10"
      data-testid="client-dashboard-v3"
    >
      {/* Zone 1 · Hero adaptativo */}
      <HeroAdaptativo
        context={data.context}
        workflowSummary={data.workflow_summary}
      />

      {/* IA Coach suggestion · MB-7 atom 7.4-bis · only MEDIA+ */}
      <AgentSuggestionBanner
        slug="a12_coach_suggestion"
        pageUrl="/client-portal/dashboard"
        dismissKey="dashboard_coach_dismissed"
      />

      {/* Zone 2 · Tu trabajo de hoy */}
      <TodayActionsCards actions={data.today_actions} />

      {/* Zone 3 · Resumen visual */}
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <WorkflowStepperCard
          currentPhase={data.context.current_phase}
          phaseStep={data.context.phase_step}
        />
        <MessagesPreviewCard
          messages={data.recent_messages}
          unread={data.notifications_unread}
        />
        <div className="space-y-4">
          <DocumentsCountCard count={data.new_documents_count} />
          <UpcomingInvoiceCard invoice={data.upcoming_invoice} />
        </div>
      </section>
    </main>
  );
}
