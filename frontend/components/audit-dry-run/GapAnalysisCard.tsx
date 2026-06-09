"use client";

/**
 * GapAnalysisCard · destaca NC mayores (gaps críticos) primero
 * (ADR-037 SAN-D MB-15.4 · TRAD-9 fulkro palette).
 *
 * Si 0 NC mayores · banner verde "ready para auditoría".
 * Si ≥1 NC mayor · banner rojo destacado · lista NCs con códigos
 * + nombres + acciones sugeridas.
 */
import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { M10FindingSummary } from "@/lib/api/audit-dry-run";

interface Props {
  findings: M10FindingSummary[];
}

export function GapAnalysisCard({ findings }: Props) {
  const ncMayores = findings.filter((f) => f.evaluacion === "no_conforme_mayor");
  const ncMenores = findings.filter((f) => f.evaluacion === "no_conforme_menor");

  if (ncMayores.length === 0 && ncMenores.length === 0) {
    return (
      <Card className="border-l-4 border-l-fulkro-success">
        <CardContent className="flex items-center gap-3 p-4">
          <CheckCircle2
            className="h-6 w-6 shrink-0 text-fulkro-success"
            strokeWidth={2.3}
          />
          <div>
            <p className="font-medium">Sin gaps detectados</p>
            <p className="text-sm text-muted-foreground">
              Proyecto en buen estado para auditoría externa
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-l-4 border-l-fulkro-danger">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base text-fulkro-danger">
          <AlertTriangle className="h-5 w-5" strokeWidth={2.3} />
          Gap analysis · {ncMayores.length} NC mayores · {ncMenores.length} NC menores
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {ncMayores.length > 0 && (
          <p className="text-sm">
            Resolver NC mayores antes de auditoría externa · auditor humano
            detectaría mismos gaps.
          </p>
        )}

        {ncMayores.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold text-fulkro-danger">
              No conformidades mayores
            </h4>
            <ul className="space-y-2">
              {ncMayores.map((f) => (
                <FindingRow key={f.measure_code} finding={f} variant="danger" />
              ))}
            </ul>
          </div>
        )}

        {ncMenores.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold text-fulkro-warning">
              No conformidades menores
            </h4>
            <ul className="space-y-2">
              {ncMenores.map((f) => (
                <FindingRow key={f.measure_code} finding={f} variant="warning" />
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FindingRow({
  finding,
  variant,
}: {
  finding: M10FindingSummary;
  variant: "danger" | "warning";
}) {
  return (
    <li className="rounded-md border bg-card p-3">
      <div className="flex flex-wrap items-start gap-2">
        <Badge variant={variant} className="font-mono text-xs">
          {finding.measure_code}
        </Badge>
        <p className="flex-1 text-sm font-medium">
          {finding.measure_name || finding.measure_code}
        </p>
        <Badge variant="outline">{finding.nivel_madurez}</Badge>
      </div>
    </li>
  );
}
