"use client";

/**
 * DPC anual header · countdown + status badge · SAN-E v3.MB-6 atom 2.
 */
import { Calendar, CheckCircle2, Clock, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { type DpcDeclaration } from "@/lib/api/dpc-anual";
import { cn } from "@/lib/utils";

interface Props {
  declaration: DpcDeclaration;
}

function severityFromDays(days: number | null): "info" | "warning" | "critical" | "ok" {
  if (days === null) return "info";
  if (days < 0) return "critical";
  if (days <= 7) return "critical";
  if (days <= 30) return "warning";
  return "info";
}

export function DpcAnualHeader({ declaration }: Props) {
  const signed = declaration.status === "signed";
  const days = declaration.days_until_anniversary;
  const severity = severityFromDays(days);

  return (
    <Card
      data-testid="dpc-header"
      className={cn(
        "p-5",
        signed && "border-fulkro-success/40 bg-fulkro-success/5",
        !signed && severity === "critical" && "border-destructive/40 bg-destructive/5",
        !signed && severity === "warning" && "border-fulkro-warning/40 bg-fulkro-warning/5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {signed ? (
            <CheckCircle2 className="h-5 w-5 mt-0.5 text-fulkro-success flex-shrink-0" aria-hidden />
          ) : severity === "critical" ? (
            <ShieldAlert className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0" aria-hidden />
          ) : (
            <Calendar className="h-5 w-5 mt-0.5 text-fulkro-primary-700 flex-shrink-0" aria-hidden />
          )}
          <div className="min-w-0">
            <div className="text-xs uppercase tracking-wide font-semibold text-fulkro-primary-700">
              DPC anual {declaration.anniversary_year}
            </div>
            <div className="text-sm text-fulkro-ink-700 mt-0.5">
              Anniversary {new Date(declaration.anniversary_date).toLocaleDateString("es-ES", {
                day: "2-digit",
                month: "long",
                year: "numeric",
              })}
            </div>
            {!signed && days !== null && (
              <div className="text-xs mt-1 inline-flex items-center gap-1 text-fulkro-ink-600">
                <Clock className="h-3 w-3" aria-hidden />
                {days >= 0
                  ? `Quedan ${days} días`
                  : `Vencida hace ${Math.abs(days)} días`}
              </div>
            )}
          </div>
        </div>
        {signed ? (
          <Badge variant="success" className="flex-shrink-0">Firmada</Badge>
        ) : severity === "critical" ? (
          <Badge variant="danger" className="flex-shrink-0">Urgente</Badge>
        ) : severity === "warning" ? (
          <Badge variant="warning" className="flex-shrink-0">Próxima</Badge>
        ) : (
          <Badge variant="secondary" className="flex-shrink-0">Programada</Badge>
        )}
      </div>
    </Card>
  );
}
