"use client";

/**
 * Admin LLM observability page · MB-7 atom 7.5 Q3.A.
 *
 * Cost summary tile + top consumers + anomaly alerts + paginated log.
 * Admin-only (require_owner enforced by backend endpoints).
 *
 * Q3.A cement: cliente NEVER ve este panel. Solo Marcos.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, TrendingUp, Zap } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";


interface CostSummary {
  period: string;
  n_calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
}


interface TopConsumer {
  feature: string;
  n_calls: number;
  total_tokens: number;
  cost_usd: number;
}


interface Anomaly {
  id: number;
  feature: string;
  model: string;
  total_tokens: number;
  cost_usd: number | null;
  latency_ms: number;
  status: string;
  error_message: string | null;
  created_at: string | null;
  reason: string;
}


type Period = "today" | "week" | "month" | "all";


export default function LLMObservabilityPage() {
  const [period, setPeriod] = useState<Period>("today");
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [topConsumers, setTopConsumers] = useState<TopConsumer[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api<CostSummary>(
        `/api/v1/admin/llm-observability/cost-summary?period=${period}`,
      ),
      api<{ items: TopConsumer[] }>(
        `/api/v1/admin/llm-observability/top-consumers?period=${period}&limit=10`,
      ),
      api<{ items: Anomaly[] }>(
        `/api/v1/admin/llm-observability/anomalies?period=${period}`,
      ),
    ])
      .then(([summaryResp, topResp, anomResp]) => {
        if (cancelled) return;
        setSummary(summaryResp);
        setTopConsumers(topResp.items);
        setAnomalies(anomResp.items);
      })
      .catch(() => {
        if (cancelled) return;
        setSummary(null);
        setTopConsumers([]);
        setAnomalies([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
            LLM Observability
          </h1>
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            Coste agregado de invocaciones LLM, top consumidores y anomalías.
          </p>
          <a
            href="/admin/llm-observability/golden-eval"
            className="mt-2 inline-block text-sm font-medium text-[color:var(--fulkro-accent)] hover:underline"
            data-testid="golden-eval-link"
          >
            Golden Eval · Regression Harness →
          </a>
        </div>
        <div className="flex gap-2">
          {(["today", "week", "month", "all"] as Period[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={`rounded-md px-3 py-1.5 text-sm font-bold ${
                p === period
                  ? "bg-[color:var(--fulkro-accent)] text-white"
                  : "bg-fulkro-surface-glass-strong text-[color:var(--fulkro-body)] hover:bg-fulkro-surface-glass"
              }`}
            >
              {p === "today" ? "Hoy" : p === "week" ? "7 días" : p === "month" ? "30 días" : "Todo"}
            </button>
          ))}
        </div>
      </header>

      {loading ? (
        <div className="grid place-items-center py-20 text-[color:var(--fulkro-muted)]">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : (
        <>
          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Llamadas
                </p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
                  {summary?.n_calls ?? 0}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Tokens totales
                </p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
                  {(summary?.total_tokens ?? 0).toLocaleString("es-ES")}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Coste USD
                </p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
                  ${(summary?.cost_usd ?? 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  Latencia media
                </p>
                <p className="mt-2 text-3xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
                  {Math.round(summary?.avg_latency_ms ?? 0)} ms
                </p>
              </CardContent>
            </Card>
          </section>

          <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Top consumidores
                </CardTitle>
              </CardHeader>
              <CardContent>
                {topConsumers.length === 0 ? (
                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    Sin actividad.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs font-bold uppercase text-[color:var(--fulkro-subtitle)]">
                      <tr>
                        <th className="pb-2">Feature</th>
                        <th className="pb-2 text-right">Llamadas</th>
                        <th className="pb-2 text-right">Tokens</th>
                        <th className="pb-2 text-right">USD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topConsumers.map((c) => (
                        <tr key={c.feature} className="border-t border-fulkro-surface-glass-border">
                          <td className="py-2 font-medium">{c.feature}</td>
                          <td className="py-2 text-right">{c.n_calls}</td>
                          <td className="py-2 text-right">{c.total_tokens.toLocaleString("es-ES")}</td>
                          <td className="py-2 text-right">${c.cost_usd.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                  Anomalías
                </CardTitle>
              </CardHeader>
              <CardContent>
                {anomalies.length === 0 ? (
                  <p className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                    <Zap className="h-4 w-4" /> Sin anomalías.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {anomalies.slice(0, 10).map((a) => (
                      <li
                        key={a.id}
                        className="rounded-md border border-amber-300/30 bg-amber-500/10 px-3 py-2 text-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-[color:var(--fulkro-title)]">
                            {a.feature}
                          </span>
                          <span className="text-xs font-medium text-[color:var(--fulkro-muted)]">
                            {a.model}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-amber-800">{a.reason}</p>
                        {a.error_message && (
                          <p className="mt-1 text-xs text-rose-700">
                            {a.error_message}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
