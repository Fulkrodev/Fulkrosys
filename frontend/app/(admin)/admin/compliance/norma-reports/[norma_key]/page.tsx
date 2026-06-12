"use client";

/**
 * /admin/compliance/norma-reports/[norma_key] · detalle de una norma (J#2).
 *
 * Cierra el dead-link de norma-reports/page.tsx (enlazaba aquí pero la página
 * no existía → 404 · eslabón muerto). Muestra el último reporte (Markdown) +
 * histórico + marcar revisado. Fondos sólidos (FRENTE G). Reusa norma-api.ts.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, CheckCircle2, FileText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { SafeMarkdown } from "@/lib/client-messages/markdown";
import {
  getNormaHistory,
  getNormaLatest,
  markReportReviewed,
} from "@/lib/admin-compliance-monitor/norma-api";

const STATUS_BADGE: Record<string, "secondary" | "warning" | "danger" | "outline"> = {
  green: "secondary",
  yellow: "warning",
  red: "danger",
  unknown: "outline",
};

export default function NormaDetailPage() {
  const params = useParams<{ norma_key: string }>();
  const normaKey = params.norma_key;
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");

  const latest = useQuery({
    queryKey: ["norma", normaKey, "latest"],
    queryFn: () => getNormaLatest(normaKey),
    enabled: Boolean(normaKey),
  });
  const history = useQuery({
    queryKey: ["norma", normaKey, "history"],
    queryFn: () => getNormaHistory(normaKey),
    enabled: Boolean(normaKey),
  });

  const reviewMut = useMutation({
    mutationFn: (reportId: string) => markReportReviewed(reportId, notes.trim() || null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["norma", normaKey] });
      setNotes("");
    },
  });

  return (
    <div className="flex flex-col gap-6 p-6">
      <Link
        href="/admin/compliance/norma-reports"
        className="inline-flex w-fit items-center gap-1 text-sm text-fulkro-ink-600 hover:underline"
      >
        <ArrowLeft size={14} /> Volver a normas
      </Link>

      {latest.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : latest.isError ? (
        <Card className="border-fulkro-danger-300 bg-white">
          <CardContent className="flex items-center gap-2 py-4 text-fulkro-danger-700">
            <AlertTriangle size={16} /> No se pudo cargar el reporte de {normaKey}.
            <Button variant="ghost" size="sm" onClick={() => void latest.refetch()}>
              Reintentar
            </Button>
          </CardContent>
        </Card>
      ) : latest.data ? (
        <>
          <header className="flex items-start justify-between gap-4">
            <div>
              <h1 className="flex items-center gap-2 text-2xl font-semibold text-fulkro-ink-900">
                <FileText className="text-fulkro-primary" /> {latest.data.norma_name}
              </h1>
              <p className="mt-1 text-sm text-fulkro-ink-600">
                Score: <strong>{latest.data.compliance_score.toFixed(1)} %</strong> ·
                {" "}
                <Badge variant={STATUS_BADGE[latest.data.status] ?? "outline"}>
                  {latest.data.status}
                </Badge>
              </p>
            </div>
          </header>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle>Último reporte</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[480px] overflow-auto rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-4 text-sm text-fulkro-ink-800">
                <SafeMarkdown body={latest.data.report_md_content} />
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {latest.data.reviewed_by_marcos_at ? (
                  <p className="inline-flex items-center gap-1 text-sm text-fulkro-ink-600">
                    <CheckCircle2 size={14} className="text-fulkro-success-700" />
                    Revisado el {latest.data.reviewed_by_marcos_at.slice(0, 16).replace("T", " ")}
                  </p>
                ) : (
                  <>
                    <label htmlFor="review-notes" className="text-sm font-medium">
                      Notas de revisión (opcional)
                    </label>
                    <Textarea
                      id="review-notes"
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={3}
                      placeholder="Observaciones de la revisión…"
                      aria-label="Notas de revisión del reporte"
                    />
                    <Button
                      className="self-start"
                      disabled={reviewMut.isPending}
                      onClick={() => reviewMut.mutate(latest.data.id)}
                    >
                      {reviewMut.isPending ? "Marcando…" : "Marcar como revisado"}
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardHeader>
              <CardTitle>Histórico</CardTitle>
            </CardHeader>
            <CardContent>
              {history.isLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-fulkro-ink-200 text-left text-fulkro-ink-500">
                      <th className="px-2 py-2">Periodo</th>
                      <th className="px-2 py-2">Score</th>
                      <th className="px-2 py-2">Estado</th>
                      <th className="px-2 py-2">Generado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(history.data ?? []).map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-fulkro-ink-100 last:border-b-0 hover:bg-fulkro-ink-50"
                      >
                        <td className="px-2 py-2 font-mono text-xs">
                          {r.period_start.slice(0, 10)} → {r.period_end.slice(0, 10)}
                        </td>
                        <td className="px-2 py-2">{r.compliance_score.toFixed(1)} %</td>
                        <td className="px-2 py-2">
                          <Badge variant={STATUS_BADGE[r.status] ?? "outline"}>
                            {r.status}
                          </Badge>
                        </td>
                        <td className="px-2 py-2 font-mono text-xs text-fulkro-ink-500">
                          {r.generated_at.slice(0, 16).replace("T", " ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
