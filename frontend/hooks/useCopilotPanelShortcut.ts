"use client";

import * as React from "react";

import { useCopilotStore } from "@/lib/stores/copilot-store";

const TYPING_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (TYPING_TAGS.has(target.tagName)) return true;
  return target.isContentEditable;
}

export function useCopilotPanelShortcut() {
  const toggle = useCopilotStore((s) => s.toggle);

  React.useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const isToggle =
        (event.metaKey || event.ctrlKey) &&
        !event.altKey &&
        !event.shiftKey &&
        event.key.toLowerCase() === "j";
      if (!isToggle) return;
      if (isTypingTarget(event.target)) return;
      event.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);
}
