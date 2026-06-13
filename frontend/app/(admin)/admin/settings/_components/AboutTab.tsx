"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { ApiError } from "@/lib/api";
import type {
  AnalyticsPrefs,
  AdminSettingsAbout,
  AdminSettingsResponse,
} from "@/lib/admin-settings/schemas";
import { getAdminSettingsAbout } from "@/lib/admin-settings/api";

type Props = {
  analyticsPrefs: AnalyticsPrefs;
  onUpdateAnalyticsPrefs: (
    payload: AnalyticsPrefs,
  ) => Promise<AdminSettingsResponse>;
};

export function AboutTab({
  analyticsPrefs,
  onUpdateAnalyticsPrefs,
}: Props) {
  const [about, setAbout] = useState<AdminSettingsAbout | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCorpusMetric, setShowCorpusMetric] = useState(
    analyticsPrefs.show_corpus_metric ?? true,
  );

  useEffect(() => {
    getAdminSettingsAbout()
      .then(setAbout)
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error al cargar info sistema",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const handleToggleCorpus = async (value: boolean) => {
    const previous = showCorpusMetric;
    setShowCorpusMetric(value);
    try {
      await onUpdateAnalyticsPrefs({ show_corpus_metric: value });
      toast.success("Preferencia actualizada");
    } catch (err) {
      setShowCorpusMetric(previous);
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al actualizar",
      );
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Información del sistema</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !about) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Información del sistema</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="danger">
            <AlertDescription>
              {error ?? "No se pudo cargar la información"}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Información del sistema</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Versión
              </dt>
              <dd className="mt-1 font-mono text-sm">
                {about.version}
              </dd>
            </div>

            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Commit hash
              </dt>
              <dd className="mt-1 font-mono text-sm">
                {about.commit_hash.substring(0, 12)}
              </dd>
            </div>

            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Uptime
              </dt>
              <dd className="mt-1 text-sm">
                {about.uptime_days} días
              </dd>
            </div>

            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Clientes activos
              </dt>
              <dd className="mt-1 text-sm">
                <Badge variant="secondary">
                  {about.active_clients_count}
                </Badge>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {showCorpusMetric && (
        <Card>
          <CardHeader>
            <CardTitle>Corpus normativo ENS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              <div className="flex items-baseline justify-between">
                <span className="text-base font-medium text-[color:var(--fulkro-body)]">
                  Cobertura ingestion
                </span>
                <span className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
                  {about.corpus_completion_pct.toFixed(1)}%
                </span>
              </div>
              <Progress value={about.corpus_completion_pct} />
              <dl className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
                <div>
                  <dt className="text-fulkro-ink-500">Sources indexed</dt>
                  <dd className="font-mono">
                    {about.corpus_sources_count} / {about.corpus_sources_target}
                  </dd>
                </div>
                <div>
                  <dt className="text-fulkro-ink-500">Chunks total</dt>
                  <dd className="font-mono">
                    {about.corpus_chunks_total.toLocaleString()}
                  </dd>
                </div>
              </dl>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Tests + cobertura</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Suite passing
              </dt>
              <dd className="mt-1 text-2xl font-semibold text-fulkro-success">
                {about.suite_passing}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wider text-fulkro-ink-500">
                Test/code ratio
              </dt>
              <dd className="mt-1 text-2xl font-bold text-[color:var(--fulkro-title)]">
                {about.test_loc_ratio_avg.toFixed(2)}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preferencias visualización</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4 rounded border border-fulkro-ink-300/40 p-4">
            <div className="flex flex-col gap-1">
              <Label htmlFor="show_corpus_metric">
                Mostrar métrica corpus
              </Label>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Activa/desactiva la sección &ldquo;Corpus normativo ENS&rdquo;
                en este panel
              </p>
            </div>
            <Switch
              id="show_corpus_metric"
              checked={showCorpusMetric}
              onCheckedChange={handleToggleCorpus}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
