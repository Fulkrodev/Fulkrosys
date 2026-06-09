"use client";

/**
 * IsoCoveragePanel · SAN-C.MB-10.7.
 *
 * Permite al consultor introducir los controles ISO 27001 implementados
 * por el cliente y obtener cobertura ENS automática + gaps ENS-only +
 * estimación horas ahorradas (mapping CCN-STIC 825).
 *
 * Refs: SAN-C.MB-10.7 · cierra fantasma frontend MB-10.7.
 */
import * as React from "react";
import { ListChecks, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { api } from "@/lib/api";

interface IsoCoverageResponse {
  project_id: string | null;
  iso_controls_implemented: string[];
  ens_measures_total: number;
  ens_measures_covered: string[];
  ens_measures_gaps: string[];
  coverage_percent: number;
  effort_hours_saved_estimate: number;
  coverage_per_family: Record<string, { total: number; covered: number }>;
}

interface IsoCoveragePanelProps {
  projectId: string;
}

export function IsoCoveragePanel({ projectId }: IsoCoveragePanelProps) {
  const [controlsText, setControlsText] = React.useState(
    "A.5.1, A.5.2, A.5.16, A.5.18, A.8.5, A.8.7, A.8.9",
  );
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState<IsoCoverageResponse | null>(null);

  const handleCalculate = async () => {
    const controls = controlsText
      .split(/[,\s\n]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    if (controls.length === 0) {
      toast.warning("Indica al menos un control ISO 27001");
      return;
    }
    setBusy(true);
    try {
      const res = await api<IsoCoverageResponse>(
        `/api/v1/diagnosis/projects/${projectId}/cross-compliance/iso27001/coverage`,
        {
          method: "POST",
          json: { iso_controls_implemented: controls },
        },
      );
      setResult(res);
      toast.success("Cobertura ENS calculada", {
        description: `${res.coverage_percent.toFixed(1)}% medidas cubiertas`,
      });
    } catch (e) {
      toast.error("Error calculando cobertura", {
        description: e instanceof Error ? e.message : "Inténtalo de nuevo.",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <InfoTag term="ENS" display="ENS" /> ↔{" "}
          <InfoTag term="ISO_27001" display="ISO 27001" /> cobertura cruzada
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Si el cliente tiene ISO 27001 vigente · introduce los controles
          Anexo A:2022 implementados y obtén cobertura ENS automática vía
          mapping CCN-STIC 825 + estimación horas ahorradas.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium" htmlFor="iso-controls">
            Controles ISO implementados (separa con comas o saltos):
          </label>
          <textarea
            id="iso-controls"
            value={controlsText}
            onChange={(e) => setControlsText(e.target.value)}
            rows={3}
            className="rounded-md border px-3 py-2 text-sm font-mono"
            placeholder="A.5.1, A.5.2, A.8.5..."
          />
          <Button onClick={handleCalculate} disabled={busy}>
            {busy ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calculando…
              </>
            ) : (
              <>
                <ListChecks className="mr-2 h-4 w-4" />
                Calcular cobertura
              </>
            )}
          </Button>
        </div>

        {result ? (
          <div className="space-y-3 rounded-md border p-3">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-2xl font-bold">
                {result.coverage_percent.toFixed(1)}%
              </span>
              <span className="text-sm text-muted-foreground">
                cobertura ENS · {result.ens_measures_covered.length} de{" "}
                {result.ens_measures_total} medidas cubiertas
              </span>
              <Badge variant="outline">
                ≈ {result.effort_hours_saved_estimate} h ahorradas
              </Badge>
            </div>

            <div>
              <p className="text-sm font-medium">
                Cobertura por familia ENS:
              </p>
              <div className="grid grid-cols-2 gap-1 text-xs md:grid-cols-3">
                {Object.entries(result.coverage_per_family).map(
                  ([family, stats]) => (
                    <div
                      key={family}
                      className="flex justify-between rounded border bg-muted/30 px-2 py-1"
                    >
                      <span className="font-mono">{family}</span>
                      <span>
                        {stats.covered}/{stats.total}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>

            {result.ens_measures_gaps.length > 0 ? (
              <details className="text-sm">
                <summary className="cursor-pointer font-medium">
                  Gaps ENS-only ({result.ens_measures_gaps.length}) — requieren
                  trabajo adicional
                </summary>
                <p className="mt-2 font-mono text-xs">
                  {result.ens_measures_gaps.join(" · ")}
                </p>
              </details>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
