/**
 * NextActionCard · card individual NextAction con CTA navegación motor
 * (FASE 8 · ADR-026).
 */
"use client";

import Link from "next/link";
import { ArrowRight, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { NextAction } from "@/lib/admin-workflow/schemas";

function priorityBadgeClass(priority: number): string {
  if (priority === 1) {
    return "bg-destructive/10 text-destructive";
  }
  if (priority === 2) {
    return "bg-fulkro-warning/10 text-fulkro-warning";
  }
  return "bg-fulkro-primary-50 text-fulkro-primary-700";
}

function priorityLabel(priority: number): string {
  if (priority === 1) {
    return "Alta";
  }
  if (priority === 2) {
    return "Media";
  }
  return "Baja";
}

export interface NextActionCardProps {
  action: NextAction;
  className?: string;
}

export function NextActionCard({ action, className }: NextActionCardProps) {
  return (
    <Card className={cn("transition-shadow hover:shadow-md", className)}>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
              {action.motor}
            </p>
            <h4 className="font-medium text-fulkro-ink-900">{action.label}</h4>
          </div>
          <Badge className={priorityBadgeClass(action.priority)}>
            Prioridad {priorityLabel(action.priority)}
          </Badge>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1 text-xs text-fulkro-ink-500">
            <Clock size={12} />
            <span>~{action.estimated_minutes} min</span>
          </div>
          {action.endpoint ? (
            <Link
              href={action.endpoint}
              className="inline-flex items-center gap-1 text-xs font-medium text-fulkro-primary-700 hover:text-fulkro-primary-800"
            >
              Ir <ArrowRight size={14} />
            </Link>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
