"use client";

import { Loader2, Paperclip, Send } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MAX_ROWS = 6;
const ROW_PX = 22;
const BASE_PX = 22;

export interface CopilotComposerHandle {
  focus: () => void;
  setValue: (value: string) => void;
}

export interface CopilotComposerProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onCancel?: () => void;
  placeholder?: string;
}

export const CopilotComposer = React.forwardRef<
  CopilotComposerHandle,
  CopilotComposerProps
>(function CopilotComposer(
  { isStreaming, onSend, onCancel, placeholder },
  ref,
) {
  const [value, setValue] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useImperativeHandle(
    ref,
    () => ({
      focus: () => textareaRef.current?.focus(),
      setValue: (next: string) => setValue(next),
    }),
    [],
  );

  React.useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    const lines = Math.min(MAX_ROWS, Math.max(1, value.split("\n").length));
    node.style.height = `${BASE_PX + (lines - 1) * ROW_PX}px`;
  }, [value]);

  function submit() {
    const text = value.trim();
    if (!text || isStreaming) return;
    setValue("");
    onSend(text);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className={cn(
        "flex items-end gap-2 rounded-xl border p-2",
      )}
      style={{
        backgroundColor: "var(--fulkro-surface-glass)",
        borderColor: "var(--fulkro-surface-glass-border)",
      }}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled
        title="Adjuntar archivo · disponible próximamente (Sesión 12)"
        aria-label="Adjuntar archivo (próximamente)"
      >
        <Paperclip className="h-4 w-4" strokeWidth={2.3} />
      </Button>
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder ?? "Pregunta a tu copiloto…"}
        rows={1}
        disabled={isStreaming}
        className="min-h-[44px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm focus-visible:ring-0"
      />
      {isStreaming ? (
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={onCancel}
          aria-label="Cancelar respuesta"
        >
          <Loader2 className="h-4 w-4 animate-spin" />
        </Button>
      ) : (
        <Button
          type="submit"
          size="icon"
          disabled={!value.trim()}
          aria-label="Enviar mensaje"
        >
          <Send className="h-4 w-4" strokeWidth={2.4} />
        </Button>
      )}
    </form>
  );
});
