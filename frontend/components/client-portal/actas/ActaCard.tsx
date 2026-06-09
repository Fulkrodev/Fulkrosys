"use client";

/**
 * Acta card · summary list item · SAN-E v3.MB-6 atom 5.
 */
import { ChevronRight, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  type ActaClientView,
  type ActaSubtype,
  ACTA_SUBTYPE_SHORT_LABELS,
} from "@/lib/api/actas";
import { cn } from "@/lib/utils";

interface Props {
  acta: ActaClientView;
  onSelect: (id: string) => void;
  selected: boolean;
}

type BadgeVariant =
  | "default"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "secondary";

const SUBTYPE_BADGE_VARIANT: Record<ActaSubtype, BadgeVariant> = {
  kickoff: "info",
  checkpoint: "success",
  audit: "warning",
  cierre: "default",
  other: "secondary",
};

export function SubtypeBadge({ subtype }: { subtype: ActaSubtype | null }) {
  if (!subtype) return <Badge variant="secondary">—</Badge>;
  return (
    <Badge
      variant={SUBTYPE_BADGE_VARIANT[subtype]}
      data-subtype={subtype}
    >
      {ACTA_SUBTYPE_SHORT_LABELS[subtype]}
    </Badge>
  );
}

export function ActaCard({ acta, onSelect, selected }: Props) {
  const reviewed = acta.client_review_status === "revisada_ok";
  const signed = acta.client_signing_intent_id != null;
  return (
    <Card
      data-testid={`acta-card-${acta.id}`}
      data-subtype={acta.acta_subtype ?? ""}
      onClick={() => onSelect(acta.id)}
      className={cn(
        "p-4 cursor-pointer hover:bg-fulkro-ink-50 transition-colors",
        selected && "ring-2 ring-fulkro-primary-700 ring-offset-2",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <FileText
            className="h-4 w-4 mt-0.5 text-fulkro-primary-700 flex-shrink-0"
            aria-hidden
          />
          <div className="min-w-0">
            <div className="font-semibold text-sm text-fulkro-ink-800 truncate">
              {acta.titulo ?? acta.codigo ?? "Acta"}
            </div>
            <div className="text-xs text-fulkro-ink-500 mt-0.5">
              {acta.codigo ?? ""}
              {acta.fecha &&
                ` · ${new Date(acta.fecha).toLocaleDateString("es-ES")}`}
            </div>
            {reviewed && (
              <div className="text-xs text-fulkro-success mt-0.5">
                ✓ Revisada
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <SubtypeBadge subtype={acta.acta_subtype} />
          {signed ? (
            <Badge variant="success">Firmada</Badge>
          ) : (
            <Badge variant="info">Pendiente</Badge>
          )}
        </div>
        <ChevronRight
          className="h-4 w-4 text-fulkro-ink-600 flex-shrink-0"
          aria-hidden
        />
      </div>
    </Card>
  );
}
