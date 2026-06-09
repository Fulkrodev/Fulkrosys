"use client";

import * as React from "react";
import { Quote } from "lucide-react";

import type { Citation } from "@/lib/sprint4-types";
import { cn } from "@/lib/utils";

/** Clickable citation chip with a hover tooltip showing the source excerpt. */
export function AgentCitation({
  citation,
  className,
}: {
  citation: Citation;
  className?: string;
}) {
  const [open, setOpen] = React.useState(false);
  return (
    <span className={cn("relative inline-block", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="inline-flex items-center gap-1 rounded border border-fulkro-primary-700/30 bg-fulkro-primary-700/5 px-1.5 py-0.5 font-mono text-[10px] text-fulkro-primary-700 hover:bg-fulkro-primary-700/10"
      >
        [{citation.framework} {citation.article}]
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-0 z-30 mb-1 w-64 rounded-md border border-fulkro-ink-300/60 bg-white p-2 text-left text-[11px] leading-snug text-fulkro-ink-700 shadow-ink"
        >
          <span className="mb-1 flex items-center gap-1 font-semibold text-fulkro-primary-700">
            <Quote size={10} /> {citation.framework} {citation.article}
          </span>
          {citation.excerpt}
        </span>
      )}
    </span>
  );
}
