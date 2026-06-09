"use client";

import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";

import { LeadCard } from "@/components/pipeline/LeadCard";
import type { Lead, LeadStage } from "@/lib/types";
import { cn } from "@/lib/utils";

export function LeadColumn({
  stage,
  label,
  leads,
  onLeadClick,
}: {
  stage: LeadStage;
  label: string;
  leads: Lead[];
  onLeadClick: (lead: Lead) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `col-${stage}`,
    data: { type: "column", stage },
  });

  return (
    <div className="flex min-w-0 flex-col rounded-md border border-fulkro-ink-300/50 bg-[color:var(--fulkro-surface-glass)]">
      <div className="flex items-center justify-between rounded-t-md border-b border-fulkro-ink-300/50 bg-white/60 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-fulkro-primary-700">
        <span>{label}</span>
        <span className="rounded-full bg-fulkro-primary-700/10 px-2 py-0.5 font-mono text-[10px] text-fulkro-primary-700">
          {leads.length}
        </span>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[60px] flex-1 flex-col gap-2 p-2 transition-colors",
          isOver && "bg-fulkro-primary-500/10",
        )}
      >
        <SortableContext
          items={leads.map((l) => l.id)}
          strategy={verticalListSortingStrategy}
        >
          {leads.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onClick={() => onLeadClick(lead)}
            />
          ))}
        </SortableContext>
        {leads.length === 0 && (
          // Sub-atom Sesión 3B-2B.3 Phase C.4 · WCAG color-contrast fix.
          // Previous: text-[color:var(--fulkro-muted)] (#6E6E7A) on
          // surface-glass tinted background fell below 4.5:1 AA at 14px.
          // Switched to text-fulkro-ink-700 (always passes AA on any tint).
          <p className="mt-4 text-center text-sm font-medium text-fulkro-ink-700">
            Sin leads en esta etapa
          </p>
        )}
      </div>
    </div>
  );
}
