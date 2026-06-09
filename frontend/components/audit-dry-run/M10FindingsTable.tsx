"use client";

/**
 * M10FindingsTable · 58 preguntas M10 deterministas con badges
 * fulkro palette (ADR-037 SAN-D MB-15.4 · TRAD-9).
 *
 * Filtros UI: todas / con evidencia / NC mayores / NC menores.
 * Maturity badge L0-L5: L0/L1=danger · L2/L3=warning · L4/L5=success.
 * Evaluación badge: conforme=success · NCmenor=warning · NCmayor=danger.
 */
import { Filter } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  AuditEvaluacion,
  M10FindingSummary,
} from "@/lib/api/audit-dry-run";

type FilterKey = "all" | "with_evidence" | "nc_mayor" | "nc_menor";

const EVALUACION_VARIANT: Record<AuditEvaluacion, "success" | "warning" | "danger" | "info" | "outline"> = {
  conforme: "success",
  no_conforme_menor: "warning",
  no_conforme_mayor: "danger",
  observacion: "info",
  no_aplica: "outline",
};

const EVALUACION_LABEL: Record<AuditEvaluacion, string> = {
  conforme: "Conforme",
  no_conforme_menor: "NC menor",
  no_conforme_mayor: "NC mayor",
  observacion: "Observación",
  no_aplica: "No aplica",
};

function maturityVariant(level: string): "success" | "warning" | "danger" | "outline" {
  if (level === "L4" || level === "L5") return "success";
  if (level === "L2" || level === "L3") return "warning";
  if (level === "L0" || level === "L1") return "danger";
  return "outline";
}

interface Props {
  findings: M10FindingSummary[];
}

export function M10FindingsTable({ findings }: Props) {
  const [filter, setFilter] = useState<FilterKey>("all");

  const filtered = useMemo(() => {
    if (filter === "with_evidence") {
      return findings.filter(
        (f) =>
          f.evaluacion === "conforme" ||
          f.evaluacion === "no_conforme_menor" ||
          f.evaluacion === "observacion",
      );
    }
    if (filter === "nc_mayor") {
      return findings.filter((f) => f.evaluacion === "no_conforme_mayor");
    }
    if (filter === "nc_menor") {
      return findings.filter((f) => f.evaluacion === "no_conforme_menor");
    }
    return findings;
  }, [findings, filter]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" strokeWidth={2.3} />
            Findings M10 ({findings.length})
          </CardTitle>
          <div className="flex flex-wrap gap-1">
            <FilterButton active={filter === "all"} onClick={() => setFilter("all")}>
              Todas
            </FilterButton>
            <FilterButton
              active={filter === "with_evidence"}
              onClick={() => setFilter("with_evidence")}
            >
              Con evidencia
            </FilterButton>
            <FilterButton
              active={filter === "nc_menor"}
              onClick={() => setFilter("nc_menor")}
            >
              NC menores
            </FilterButton>
            <FilterButton
              active={filter === "nc_mayor"}
              onClick={() => setFilter("nc_mayor")}
              danger
            >
              NC mayores
            </FilterButton>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Sin findings para este filtro.
          </p>
        ) : (
          <ul className="space-y-2">
            {filtered.map((f) => (
              <li
                key={f.measure_code}
                className="flex flex-wrap items-start gap-3 rounded-md border p-3 text-sm"
              >
                <Badge variant="outline" className="font-mono text-xs">
                  {f.measure_code}
                </Badge>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{f.measure_name || f.measure_code}</p>
                </div>
                <Badge variant={EVALUACION_VARIANT[f.evaluacion]}>
                  {EVALUACION_LABEL[f.evaluacion]}
                </Badge>
                <Badge variant={maturityVariant(f.nivel_madurez)}>
                  {f.nivel_madurez}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function FilterButton({
  active,
  onClick,
  children,
  danger,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
}) {
  const variant: "primary" | "danger" | "outline" = active
    ? danger
      ? "danger"
      : "primary"
    : "outline";
  return (
    <Button size="sm" variant={variant} onClick={onClick}>
      {children}
    </Button>
  );
}
