"use client";

import { CSS } from "@dnd-kit/utilities";
import { useSortable } from "@dnd-kit/sortable";
import { FileText, GripVertical } from "lucide-react";

import { RAGDot } from "@/components/data/RAGBadge";
import type { Lead } from "@/lib/types";
import { cn } from "@/lib/utils";

function formatEuros(v: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(v);
}

function relative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.round(diff / 60_000);
  if (min < 1) return "ahora";
  if (min < 60) return `${min} min`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.round(hours / 24);
  return `${days} d`;
}

export function LeadCard({
  lead,
  onClick,
  dragOverlay = false,
}: {
  lead: Lead;
  onClick?: () => void;
  dragOverlay?: boolean;
}) {
  const sortable = useSortable({
    id: lead.id,
    data: { type: "lead", stage: lead.stage },
  });
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = sortable;

  const style: React.CSSProperties = dragOverlay
    ? {}
    : {
        transform: CSS.Transform.toString(transform),
        transition,
      };

  // Sub-atom Sesión 3B-2B.3 Phase C.4 · WCAG nested-interactive fix.
  //
  // Previous structure (FAIL):
  //   <div {...attributes} onClick={openDetail}>      ← role=button + tabIndex via dnd-kit
  //     <button data-drag-handle {...listeners} />    ← nested button inside
  //   </div>
  // axe rule `nested-interactive` (serious · 5 nodes) flagged the nesting.
  //
  // New structure (PASS):
  //   <div ref={setNodeRef} className="relative ...">    ← positioning wrapper · NO role
  //     <button onClick={openDetail} className="..." >   ← single click target
  //       {all card content}
  //     </button>
  //     <button data-drag-handle {...attributes} {...listeners} />   ← sibling · NOT nested
  //   </div>
  // Two sibling buttons · no nesting · drag handle gets focus role from dnd-kit
  // attributes · outer div is purely presentational positioning.

  const cardContent = (
    <>
      <div className="mb-2 flex items-start justify-between gap-2 pr-6">
        <p className="truncate font-bold text-[color:var(--fulkro-title)]">
          {lead.empresa}
        </p>
      </div>

      <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--fulkro-muted)]">
        <RAGDot status={lead.rag} className="h-2 w-2" />
        <span className="font-mono">{lead.score}</span>
        {lead.pliego_attached && (
          <span
            className="inline-flex items-center gap-1 text-fulkro-primary-700"
            title="Pliego adjunto"
          >
            <FileText size={12} />
            Pliego
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center justify-between text-xs">
        <span className="font-semibold text-fulkro-primary-700">
          {formatEuros(lead.value_eur)}
        </span>
        <span className="text-fulkro-ink-500">
          {relative(lead.last_touched_at)}
        </span>
      </div>
    </>
  );

  return (
    <div
      ref={dragOverlay ? undefined : setNodeRef}
      style={style}
      className={cn(
        "group relative rounded-md border bg-white text-sm shadow-md transition",
        "hover:border-fulkro-primary-700/30 hover:shadow-lg",
        isDragging && !dragOverlay
          ? "opacity-50"
          : "border-[color:var(--fulkro-surface-glass-border)]",
        dragOverlay && "shadow-ink ring-2 ring-fulkro-primary-700/20",
      )}
    >
      {dragOverlay ? (
        <div className="p-3">{cardContent}</div>
      ) : (
        <button
          type="button"
          onClick={onClick}
          aria-label={`Abrir detalle de ${lead.empresa}`}
          className="block w-full p-3 text-left rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
        >
          {cardContent}
        </button>
      )}

      {!dragOverlay && (
        <button
          type="button"
          data-drag-handle
          className="absolute right-2 top-2 z-10 text-fulkro-ink-500 opacity-40 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 rounded-sm"
          aria-label={`Arrastrar lead ${lead.empresa}`}
          {...attributes}
          {...listeners}
        >
          <GripVertical size={14} />
        </button>
      )}
    </div>
  );
}
