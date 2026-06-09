"use client";

/**
 * Incident card · summary list item · SAN-E v3.MB-6 atom 3.
 */
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Info,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { type IncidentClient } from "@/lib/api/incidents";
import { cn } from "@/lib/utils";

interface Props {
  incident: IncidentClient;
  onSelect: (id: string) => void;
  selected: boolean;
}

function severityIcon(severity: string | null) {
  if (severity === "critical") {
    return <AlertCircle className="h-4 w-4 text-destructive" aria-hidden />;
  }
  if (severity === "high") {
    return <AlertTriangle className="h-4 w-4 text-fulkro-warning" aria-hidden />;
  }
  return <Info className="h-4 w-4 text-fulkro-info" aria-hidden />;
}

function severityBadge(severity: string | null) {
  if (severity === "critical") return <Badge variant="danger">Crítica</Badge>;
  if (severity === "high") return <Badge variant="warning">Alta</Badge>;
  if (severity === "medium") return <Badge variant="info">Media</Badge>;
  return <Badge variant="secondary">Baja</Badge>;
}

function stateBadge(state: string | null) {
  if (state === "closed") return <Badge variant="success">Cerrado</Badge>;
  if (state === "resolved") return <Badge variant="info">Resuelto</Badge>;
  return <Badge variant="secondary">{state ?? "—"}</Badge>;
}

export function IncidentCard({ incident, onSelect, selected }: Props) {
  const reviewed = incident.client_review_status === "revisada_ok";
  return (
    <Card
      data-testid={`incident-card-${incident.id}`}
      data-workflow-state={incident.workflow_state}
      data-severity={incident.severidad}
      onClick={() => onSelect(incident.id)}
      className={cn(
        "p-4 cursor-pointer hover:bg-fulkro-ink-50 transition-colors",
        selected && "ring-2 ring-fulkro-primary-700 ring-offset-2",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {severityIcon(incident.severidad)}
          <div className="min-w-0">
            <div className="font-semibold text-sm text-fulkro-ink-800 truncate">
              {incident.descripcion?.slice(0, 80) ?? "Incident sin descripción"}
              {(incident.descripcion?.length ?? 0) > 80 && "…"}
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {incident.fecha &&
                new Date(incident.fecha).toLocaleDateString("es-ES", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })}
              {reviewed && " · ✓ Revisado"}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {severityBadge(incident.severidad)}
          {stateBadge(incident.workflow_state)}
        </div>
        <ChevronRight className="h-4 w-4 text-fulkro-ink-600 flex-shrink-0" aria-hidden />
      </div>
    </Card>
  );
}
