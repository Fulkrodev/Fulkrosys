"use client";

/**
 * Checkin card · summary list item · SAN-E v3.MB-6 atom 4.
 */
import { CalendarCheck, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { type RetainerCheckin } from "@/lib/api/retainer-checkin";
import { cn } from "@/lib/utils";

interface Props {
  checkin: RetainerCheckin;
  onSelect: (id: string) => void;
  selected: boolean;
}

function ragBadge(rag: RetainerCheckin["rag_overall"]) {
  if (rag === "red") return <Badge variant="danger">RAG Rojo</Badge>;
  if (rag === "amber") return <Badge variant="warning">RAG Ámbar</Badge>;
  if (rag === "green") return <Badge variant="success">RAG Verde</Badge>;
  return <Badge variant="secondary">—</Badge>;
}

export function CheckinCard({ checkin, onSelect, selected }: Props) {
  const reviewed = checkin.client_review_status === "revisada_ok";
  const signed = checkin.client_signing_intent_id != null;
  return (
    <Card
      data-testid={`checkin-card-${checkin.id}`}
      data-period-quarter={checkin.period_quarter ?? ""}
      data-rag={checkin.rag_overall ?? ""}
      onClick={() => onSelect(checkin.id)}
      className={cn(
        "p-4 cursor-pointer hover:bg-fulkro-ink-50 transition-colors",
        selected && "ring-2 ring-fulkro-primary-700 ring-offset-2",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <CalendarCheck
            className="h-4 w-4 mt-0.5 text-fulkro-primary-700 flex-shrink-0"
            aria-hidden
          />
          <div className="min-w-0">
            <div className="font-semibold text-sm text-fulkro-ink-800">
              Comité {checkin.period_quarter ?? "—"}
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {new Date(checkin.period_start).toLocaleDateString("es-ES")} →{" "}
              {new Date(checkin.period_end).toLocaleDateString("es-ES")}
            </div>
            {reviewed && (
              <div className="text-xs text-fulkro-success mt-0.5">
                ✓ Revisado
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {signed ? (
            <Badge variant="success">Firmado</Badge>
          ) : (
            <Badge variant="info">Pendiente</Badge>
          )}
          {ragBadge(checkin.rag_overall)}
        </div>
        <ChevronRight className="h-4 w-4 text-fulkro-ink-600 flex-shrink-0" aria-hidden />
      </div>
    </Card>
  );
}
