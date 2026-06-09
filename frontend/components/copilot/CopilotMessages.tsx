"use client";

import * as React from "react";

import { CopilotMessage } from "@/components/copilot/CopilotMessage";
import type { CopilotMessage as CopilotMessageType } from "@/lib/sprint4-types";

export interface CopilotMessagesProps {
  messages: CopilotMessageType[];
  emptyState?: React.ReactNode;
}

export function CopilotMessages({ messages, emptyState }: CopilotMessagesProps) {
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div
      ref={scrollRef}
      className="scrollbar-fulkro-light flex-1 space-y-3 overflow-y-auto px-1"
    >
      {messages.length === 0 && emptyState ? (
        <div className="flex h-full items-center justify-center px-4 py-8 text-center text-sm text-[color:var(--fulkro-muted)]">
          {emptyState}
        </div>
      ) : (
        messages.map((m) => <CopilotMessage key={m.id} message={m} />)
      )}
    </div>
  );
}
