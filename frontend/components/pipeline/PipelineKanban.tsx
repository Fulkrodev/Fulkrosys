"use client";

import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { Loader2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { LeadCard } from "@/components/pipeline/LeadCard";
import { LeadColumn } from "@/components/pipeline/LeadColumn";
import { LeadDrawer } from "@/components/pipeline/LeadDrawer";
import { useLeads, useUpdateLeadStage } from "@/hooks/useLeads";
import type { Lead, LeadStage } from "@/lib/types";
import { LEAD_STAGES } from "@/lib/types";

export function PipelineKanban() {
  const { data, isLoading } = useLeads();
  const updateStage = useUpdateLeadStage();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [selectedLead, setSelectedLead] = React.useState<Lead | null>(null);

  const leads = React.useMemo(() => data?.items ?? [], [data]);
  const grouped = React.useMemo(() => groupByStage(leads), [leads]);

  const activeLead = React.useMemo(
    () => leads.find((l) => l.id === activeId) ?? null,
    [activeId, leads],
  );

  function onDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const lead = leads.find((l) => l.id === active.id);
    if (!lead) return;

    const overId = String(over.id);
    let targetStage: LeadStage | null = null;
    if (overId.startsWith("col-")) {
      targetStage = overId.slice(4) as LeadStage;
    } else {
      const overLead = leads.find((l) => l.id === overId);
      if (overLead) targetStage = overLead.stage;
    }

    if (!targetStage || targetStage === lead.stage) return;

    updateStage.mutate(
      { leadId: lead.id, stage: targetStage },
      {
        onError: () => toast.error("No se pudo mover el lead"),
        onSuccess: () => {
          const label =
            LEAD_STAGES.find((s) => s.id === targetStage)?.label ?? targetStage;
          toast.success(`"${lead.empresa}" → ${label}`);
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
        <Loader2 size={14} className="animate-spin" />
        Cargando pipeline…
      </div>
    );
  }

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        <div className="grid grid-cols-1 gap-3 pb-4 md:grid-cols-2 lg:grid-cols-4">
          {LEAD_STAGES.map(({ id, label }) => (
            <LeadColumn
              key={id}
              stage={id}
              label={label}
              leads={grouped[id] ?? []}
              onLeadClick={(lead) => setSelectedLead(lead)}
            />
          ))}
        </div>

        <DragOverlay>
          {activeLead ? <LeadCard lead={activeLead} dragOverlay /> : null}
        </DragOverlay>
      </DndContext>

      <LeadDrawer
        lead={selectedLead}
        open={!!selectedLead}
        onClose={() => setSelectedLead(null)}
      />
    </>
  );
}

function groupByStage(leads: Lead[]): Partial<Record<LeadStage, Lead[]>> {
  const map: Partial<Record<LeadStage, Lead[]>> = {};
  for (const lead of leads) {
    (map[lead.stage] ??= []).push(lead);
  }
  return map;
}
