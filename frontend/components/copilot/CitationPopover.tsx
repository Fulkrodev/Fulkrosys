"use client";

import * as React from "react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Citation } from "@/lib/sprint4-types";
import { cn } from "@/lib/utils";

export interface CitationPopoverProps {
  citation: Citation;
  className?: string;
}

export function CitationPopover({ citation, className }: CitationPopoverProps) {
  const headerLabel =
    citation.framework ||
    citation.measure ||
    citation.article ||
    citation.excerpt;
  const subLabel =
    citation.measure && citation.measure !== headerLabel
      ? citation.measure
      : citation.article || undefined;
  const preview = citation.preview ?? citation.excerpt;
  const chunkShort = citation.chunk_id ? citation.chunk_id.slice(0, 8) : null;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          style={{
            backgroundColor: "var(--fulkro-surface-glass-strong)",
            borderColor: "var(--fulkro-surface-glass-border)",
          }}
          className={cn(
            "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold text-[color:var(--fulkro-spark)] transition-colors hover:bg-[color:var(--fulkro-surface-glass)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--fulkro-primary-700)]",
            className,
          )}
          aria-label={`Ver chunk RAG ${citation.excerpt}`}
        >
          {citation.excerpt}
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={6}
        className="w-96 max-w-[min(96vw,420px)] space-y-2 border-[color:var(--fulkro-surface-glass-border)]"
        style={{
          backgroundColor: "var(--fulkro-surface-glass)",
          backdropFilter: "blur(14px) saturate(140%)",
          WebkitBackdropFilter: "blur(14px) saturate(140%)",
        }}
      >
        <div className="text-xs font-bold text-[color:var(--fulkro-title)]">
          {headerLabel}
          {subLabel ? (
            <span className="ml-1 font-medium text-[color:var(--fulkro-muted)]">
              · {subLabel}
            </span>
          ) : null}
        </div>
        {preview ? (
          <p className="text-xs leading-relaxed text-[color:var(--fulkro-body)]">
            {preview}
          </p>
        ) : (
          <p className="text-xs italic text-[color:var(--fulkro-muted)]">
            Vista previa no disponible · este chunk se muestra solo como
            referencia normativa.
          </p>
        )}
        {chunkShort ? (
          <div className="text-[10px] uppercase tracking-wide text-[color:var(--fulkro-muted)]">
            chunk_id: {chunkShort}…
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}
