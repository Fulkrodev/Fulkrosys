"use client";

import { AlertTriangle } from "lucide-react";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CitationPopover } from "@/components/copilot/CitationPopover";
import type { CopilotMessage as CopilotMessageType } from "@/lib/sprint4-types";
import { cn } from "@/lib/utils";

export interface CopilotMessageProps {
  message: CopilotMessageType;
}

export function CopilotMessage({ message }: CopilotMessageProps) {
  const isUser = message.role === "user";
  const isCorpusGap = message.metadata?.corpus_gap === true;

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          style={{ background: "var(--fulkro-sidebar-gradient)" }}
          className="max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] font-medium leading-relaxed text-white shadow-sm"
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl px-4 py-3 text-[15px] leading-relaxed",
        isCorpusGap &&
          "border-l-4 border-[color:var(--fulkro-warning,_#d97706)] bg-[color:var(--fulkro-warning,_#d97706)]/5 pl-3",
      )}
      style={
        isCorpusGap
          ? undefined
          : {
              backgroundColor: "var(--fulkro-surface-glass-strong)",
              borderColor: "var(--fulkro-surface-glass-border)",
            }
      }
    >
      {isCorpusGap ? (
        <div className="flex items-center gap-1.5 text-xs font-semibold text-[color:var(--fulkro-warning,_#d97706)]">
          <AlertTriangle className="h-3 w-3" strokeWidth={2.4} />
          Fuente no disponible aún en corpus FULKRO
        </div>
      ) : null}

      <div className="prose prose-sm max-w-none text-[color:var(--fulkro-body)]">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ href, children, ...props }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-[color:var(--fulkro-spark)] underline-offset-2 hover:underline"
                {...props}
              >
                {children}
              </a>
            ),
            code: ({ children, ...props }) => (
              <code
                className="rounded bg-[color:var(--fulkro-surface-glass-strong)] px-1 py-0.5 text-[12px]"
                {...props}
              >
                {children}
              </code>
            ),
          }}
        >
          {message.content || (message.streaming ? "_Pensando…_" : "")}
        </ReactMarkdown>
        {message.streaming ? (
          <span className="ml-1 inline-block h-3.5 w-1 translate-y-0.5 animate-pulse rounded-sm bg-[color:var(--fulkro-subtitle)]" />
        ) : null}
      </div>

      {message.citations && message.citations.length > 0 ? (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {message.citations.map((c) => (
            <CitationPopover key={c.id} citation={c} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
