/**
 * PhaseCard · card individual per fase con status badge + progress bar
 * (FASE 8 · ADR-026).
 */
"use client";

import { CheckCircle2, Circle, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  PHASE_LABELS,
  type PhaseRoadmapEntry,
  type PhaseStatus,
} from "@/lib/admin-workflow/schemas";

const STATUS_BADGE_VARIANT: Record<PhaseStatus, "default" | "secondary" | "outline"> = {
  done: "default",
  in_progress: "secondary",
  pending: "outline",
};

const STATUS_LABEL: Record<PhaseStatus, string> = {
  done: "Completada",
  in_progress: "En curso",
  pending: "Pendiente",
};

const STATUS_ICON: Record<PhaseStatus, typeof CheckCircle2> = {
  done: CheckCircle2,
  in_progress: Clock,
  pending: Circle,
};

const STATUS_PROGRESS_COLOR: Record<PhaseStatus, "primary" | "success" | "warning"> = {
  done: "success",
  in_progress: "primary",
  pending: "warning",
};

export interface PhaseCardProps {
  entry: PhaseRoadmapEntry;
  onClick?: (phase: PhaseRoadmapEntry) => void;
  className?: string;
}

export function PhaseCard({ entry, onClick, className }: PhaseCardProps) {
  const Icon = STATUS_ICON[entry.status];
  const handleClick = onClick ? () => onClick(entry) : undefined;

  return (
    <Card
      onClick={handleClick}
      className={cn(
        "transition-shadow",
        onClick && "cursor-pointer hover:shadow-md",
        entry.is_current && "border-fulkro-primary-500",
        className,
      )}
    >
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Icon
              size={18}
              className={cn(
                entry.status === "done" && "text-fulkro-success",
                entry.status === "in_progress" && "text-fulkro-primary-700",
                entry.status === "pending" && "text-fulkro-ink-600",
              )}
            />
            <h3 className="font-semibold text-fulkro-ink-900">
              {PHASE_LABELS[entry.phase]}
            </h3>
          </div>
          <Badge variant={STATUS_BADGE_VARIANT[entry.status]}>
            {STATUS_LABEL[entry.status]}
          </Badge>
        </div>
        <Progress
          value={entry.pct_completed}
          color={STATUS_PROGRESS_COLOR[entry.status]}
        />
        <p className="text-xs text-fulkro-ink-500">
          {entry.pct_completed.toFixed(0)}% completado
        </p>
      </CardContent>
    </Card>
  );
}
