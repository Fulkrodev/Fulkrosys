import { cn } from "@/lib/utils";
import type { RagStatus } from "@/lib/types";

const LABELS: Record<RagStatus, string> = {
  green: "OK",
  amber: "Atención",
  red: "Crítico",
};

const STYLES: Record<RagStatus, string> = {
  green: "bg-fulkro-success/10 text-fulkro-success border-fulkro-success/25",
  amber: "bg-fulkro-warning/10 text-fulkro-warning border-fulkro-warning/30",
  red: "bg-fulkro-danger/10 text-fulkro-danger border-fulkro-danger/30",
};

export function RAGBadge({
  status,
  label,
  className,
  size = "md",
}: {
  status: RagStatus;
  label?: string;
  className?: string;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        size === "sm"
          ? "px-2 py-0.5 text-[10px]"
          : "px-2.5 py-1 text-xs",
        STYLES[status],
        className,
      )}
    >
      <span className={cn("rag-dot", `rag-dot-${status}`)} />
      {label ?? LABELS[status]}
    </span>
  );
}

export function RAGDot({
  status,
  className,
}: {
  status: RagStatus;
  className?: string;
}) {
  return <span className={cn("rag-dot", `rag-dot-${status}`, className)} />;
}
