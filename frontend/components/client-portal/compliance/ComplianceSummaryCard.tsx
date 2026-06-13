"use client";

/**
 * ComplianceSummaryCard · Cliente UI Bloque 4 Phase A v3.12.
 *
 * Card per área compliance (5 áreas: conformity · remediations · tasks · evidences · gaps).
 * R29 firmísimo:
 *   - Status badge color-coded (verde OK · ámbar atención · rojo crítico empático)
 *   - Title friendly Spanish
 *   - friendly_message corto · accionable
 *   - "Ver detalles" link si detail_url disponible
 *   - pending_count subtle (NO alarma)
 */
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  HelpCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  HEALTH_LABELS,
  HEALTH_VARIANTS,
  type ComplianceArea,
  type HealthIndicator,
} from "@/lib/api/client-compliance-summary";

interface ComplianceSummaryCardProps {
  area: ComplianceArea;
}

function statusIcon(status: HealthIndicator) {
  if (status === "ok") {
    return <CheckCircle2 className="h-5 w-5 text-emerald-700" />;
  }
  if (status === "warning") {
    return <Clock className="h-5 w-5 text-amber-600" />;
  }
  if (status === "critical") {
    return <AlertCircle className="h-5 w-5 text-rose-600" />;
  }
  return <HelpCircle className="h-5 w-5 text-slate-600" />;
}

export function ComplianceSummaryCard({ area }: ComplianceSummaryCardProps) {
  const status = area.status as HealthIndicator;
  const statusLabel = HEALTH_LABELS[status] ?? area.status;
  const statusVariant = HEALTH_VARIANTS[status] ?? "outline";

  return (
    <Card
      data-testid="compliance-summary-card"
      data-area-key={area.area_key}
      data-status={status}
      className={
        status === "critical"
          ? "border-rose-200"
          : status === "warning"
            ? "border-amber-200"
            : ""
      }
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="shrink-0 mt-0.5">{statusIcon(status)}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium text-base leading-tight">
                {area.title}
              </h3>
              <Badge variant={statusVariant} className="text-xs">
                {statusLabel}
              </Badge>
            </div>
            <p
              className="text-sm text-muted-foreground"
              data-testid="friendly-message"
            >
              {area.friendly_message}
            </p>
          </div>
          {area.detail_url && (
            <Link
              href={area.detail_url}
              className="shrink-0 text-xs text-primary hover:underline inline-flex items-center gap-1"
              data-testid="detail-link"
            >
              Ver
              <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
