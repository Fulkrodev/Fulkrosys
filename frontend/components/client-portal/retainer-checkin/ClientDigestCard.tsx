"use client";

/**
 * ClientDigestCard · sub-atom 1.D.X.VERIFY 2b · cliente digest visibility R29.
 *
 * Muestra el último resumen mensual generado por consultor.
 * NUNCA presión · NUNCA alarma · NUNCA rojo.
 *
 * - Score con color suave (verde · ámbar · naranja_suave · neutral)
 * - Trend MoM con emoji ↑↓≈✨ (sin números brutos · sin "% caída")
 * - Last review date + nombre consultor
 * - Summary friendly server-side · NO inventar métricas
 *
 * Empty state amable cuando no hay snapshot todavía.
 */

import { useQuery } from "@tanstack/react-query";
import { CalendarHeart, Loader2 } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type ClientDigestView,
  cloudConnectorsClientApi,
} from "@/lib/api/cloud-connectors-client";

const COLOR_HINT_CLASSES: Record<ClientDigestView["trend_color_hint"], string> = {
  verde: "border-emerald-300 bg-emerald-50/40 text-emerald-800",
  ambar: "border-amber-300 bg-amber-50/40 text-amber-800",
  // CRITICAL R29: NUNCA rojo aunque score baje · naranja suave informativo
  naranja_suave: "border-orange-200 bg-orange-50/30 text-orange-800",
  neutral: "border-fulkro-ink-200 bg-fulkro-ink-50/40 text-fulkro-ink-700",
};

const SCORE_VARIANT_CLASSES: Record<string, string> = {
  high: "text-emerald-700",
  mid: "text-amber-700",
  // NUNCA rojo · solo naranja muy suave informativo
  low: "text-orange-700",
};

function scoreBucket(score: number): string {
  if (score >= 85) return "high";
  if (score >= 60) return "mid";
  return "low";
}

const TREND_LABEL_FRIENDLY: Record<ClientDigestView["trend_label"], string> = {
  mejora: "Vamos mejorando",
  igual: "Mantenemos el rumbo",
  baja: "Algo a revisar juntos",
  primer_resumen: "Tu primer resumen",
};

export function ClientDigestCard() {
  const query = useQuery<ClientDigestView | null>({
    queryKey: ["cliente", "retainer", "digest", "latest"],
    queryFn: async () => {
      const res = await cloudConnectorsClientApi.getLatestDigest();
      return res.digest;
    },
    staleTime: 30_000,
  });
  const data = query.data ?? null;
  const loading = query.isLoading;
  const error = query.error;

  if (loading) {
    return (
      <Card data-testid="client-digest-loading">
        <CardContent className="flex items-center gap-2 p-4 text-sm text-fulkro-ink-500">
          <Loader2 className="size-4 animate-spin" />
          Cargando tu resumen…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="client-digest-error">
        <CardContent className="p-4 text-sm text-fulkro-ink-500">
          No pudimos cargar tu resumen ahora. Vuelve a intentarlo en un rato.
        </CardContent>
      </Card>
    );
  }

  if (!data || !data.has_snapshot) {
    return (
      <Card
        className="border-fulkro-primary-200 bg-fulkro-primary-50/30"
        data-testid="client-digest-empty"
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-fulkro-primary-800">
            <CalendarHeart className="size-5" />
            Tu resumen mensual
          </CardTitle>
          <CardDescription className="text-fulkro-ink-700">
            {data?.summary_friendly ??
              "Tu primer resumen mensual estará listo pronto."}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const colorClasses = COLOR_HINT_CLASSES[data.trend_color_hint];
  const lastReviewLabel = data.last_review_at
    ? new Date(data.last_review_at).toLocaleDateString("es-ES", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <Card
      className={`border ${colorClasses}`}
      data-testid="client-digest-card"
    >
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarHeart className="size-5" />
            Tu resumen mensual
          </CardTitle>
          {lastReviewLabel && (
            <span
              className="text-xs italic text-fulkro-ink-500"
              data-testid="client-digest-review-date"
            >
              Revisado por {data.consultant_name} · {lastReviewLabel}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
            <p className="text-xs text-fulkro-ink-500">Cómo vamos</p>
            <p
              className={`mt-1 text-3xl font-semibold ${
                SCORE_VARIANT_CLASSES[scoreBucket(data.compliance_score)]
              }`}
              data-testid="client-digest-score"
            >
              {data.compliance_score}
              <span className="ml-1 text-sm font-normal text-fulkro-ink-500">
                / 100
              </span>
            </p>
          </div>
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-3">
            <p className="text-xs text-fulkro-ink-500">Evolución del mes</p>
            <p
              className="mt-1 text-lg font-medium text-fulkro-ink-800"
              data-testid="client-digest-trend"
            >
              <span className="mr-2 text-2xl" aria-hidden="true">
                {data.trend_emoji}
              </span>
              {TREND_LABEL_FRIENDLY[data.trend_label]}
            </p>
          </div>
        </div>

        <p
          className="text-sm leading-relaxed text-fulkro-ink-700"
          data-testid="client-digest-summary"
        >
          {data.summary_friendly}
        </p>

        {data.changes_reviewed_count > 0 && (
          <p
            className="text-xs italic text-fulkro-ink-500"
            data-testid="client-digest-changes-count"
          >
            {data.changes_reviewed_count} elemento(s) revisado(s) este mes ·
            si quieres comentarlos, díselo a {data.consultant_name} en la
            próxima reunión.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
