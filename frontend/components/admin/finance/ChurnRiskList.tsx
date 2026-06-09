"use client";

/**
 * ChurnRiskList · top retainers high+critical risk (MB-18.5 ADR-040).
 *
 * Heurístico explicable: muestra score + risk_factors text + recommended_action.
 * Cero ML black-box · Marcos puede auditar cada signal.
 */
import {
  AlertTriangle,
  Activity,
  Inbox,
  RefreshCw,
  Stethoscope,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import type {
  ChurnRiskRow,
  RetainerRiskLevel,
} from "@/lib/billing/schemas";

interface ChurnRiskListProps {
  rows: ChurnRiskRow[];
  loading: boolean;
  onRefresh: () => void;
  onScan: () => Promise<void>;
  scanning?: boolean;
}

function riskBadgeVariant(
  level: RetainerRiskLevel,
): "info" | "warning" | "danger" | "success" {
  switch (level) {
    case "critical":
      return "danger";
    case "high":
      return "warning";
    case "medium":
      return "info";
    default:
      return "success";
  }
}

function riskLabel(level: RetainerRiskLevel): string {
  switch (level) {
    case "critical":
      return "Crítico";
    case "high":
      return "Alto";
    case "medium":
      return "Medio";
    default:
      return "Bajo";
  }
}

export function ChurnRiskList({
  rows,
  loading,
  onRefresh,
  onScan,
  scanning,
}: ChurnRiskListProps) {
  return (
    <Card data-testid="churn-risk-list">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-fulkro-warning-700" />
              Retainers en riesgo
              <Badge variant="warning">{rows.length}</Badge>
            </CardTitle>
            <CardDescription>
              Score heurístico explicable · NO ML black-box. Cada signal
              es auditable.
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRefresh}
              data-testid="btn-refresh-churn"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Recargar
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => void onScan()}
              disabled={scanning}
              data-testid="btn-scan-churn"
            >
              <Stethoscope className="mr-2 h-4 w-4" />
              {scanning ? "Escaneando..." : "Lanzar scan"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p
            className="text-sm text-fulkro-ink-500"
            data-testid="churn-loading"
          >
            Cargando retainers...
          </p>
        ) : rows.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center gap-2 py-8 text-center"
            data-testid="churn-empty"
          >
            <Inbox className="h-10 w-10 text-fulkro-ink-300" />
            <p className="text-sm text-fulkro-ink-500">
              Sin retainers en riesgo · todo saludable.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {rows.map((row) => (
              <ChurnRow key={row.signal_id} row={row} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChurnRow({ row }: { row: ChurnRiskRow }) {
  return (
    <div
      className="rounded-md border border-fulkro-ink-100 p-3"
      data-testid={`churn-row-${row.retainer_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Badge
              variant={riskBadgeVariant(row.risk_level)}
              data-testid={`churn-level-${row.retainer_id}`}
            >
              {riskLabel(row.risk_level)}
            </Badge>
            <span className="text-sm text-fulkro-ink-700">
              Score: <strong>{row.churn_risk_score}</strong>
            </span>
            <span className="text-xs text-fulkro-ink-500">
              {new Date(row.computed_at).toLocaleString("es-ES")}
            </span>
          </div>
          {row.recommended_action ? (
            <p className="mt-2 text-sm text-fulkro-ink-700">
              <AlertTriangle className="inline h-3 w-3 mr-1 text-fulkro-warning-700" />
              {row.recommended_action}
            </p>
          ) : null}
          {row.primary_risk_factors.length > 0 ? (
            <ul
              className="mt-2 ml-5 list-disc text-xs text-fulkro-ink-500"
              data-testid={`churn-factors-${row.retainer_id}`}
            >
              {row.primary_risk_factors.map((factor) => (
                <li key={factor}>{factor}</li>
              ))}
            </ul>
          ) : null}
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-fulkro-ink-500">
            {row.days_since_portal_login !== null ? (
              <span>Login: hace {row.days_since_portal_login}d</span>
            ) : null}
            {row.tasks_overdue_count > 0 ? (
              <span>Tareas overdue: {row.tasks_overdue_count}</span>
            ) : null}
            {row.invoices_overdue_count > 0 ? (
              <span>Facturas overdue: {row.invoices_overdue_count}</span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
