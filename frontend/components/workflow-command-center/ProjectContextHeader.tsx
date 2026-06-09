/**
 * ProjectContextHeader · top section per-cliente (16% pantalla) · sub-atom 1.C.D.B.2 v3.8.
 *
 * Cliente macro + tier + categoría + archetype + status + 3 KPI cards micro.
 */
"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

import { Kpi3MicroRow } from "./Kpi3MicroRow";

interface ProjectContextHeaderProps {
  projectId: string;
  projectNombre: string;
  categoria: string | null;
  archetype: string | null;
  currentPhase: string;
  progressPct: number;
  progressCompleted: number;
  progressTotal: number;
  dimsCaptured: number;
  dimsTotal: number;
  proximoHitoDays: number | null;
}

export function ProjectContextHeader({
  projectNombre,
  categoria,
  archetype,
  currentPhase,
  progressPct,
  progressCompleted,
  progressTotal,
  dimsCaptured,
  dimsTotal,
  proximoHitoDays,
}: ProjectContextHeaderProps) {
  return (
    <header className="space-y-4 border-b pb-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2">
            <Link
              href="/admin/workflow-command-center"
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "-ml-2 h-7",
              )}
            >
              <ArrowLeft className="mr-1 size-3" />
              Command Center
            </Link>
          </div>
          <h1 className="text-xl font-semibold">{projectNombre}</h1>
          <div className="flex items-center gap-2 flex-wrap">
            {categoria && (
              <Badge variant="default" className="text-xs">
                {categoria}
              </Badge>
            )}
            {archetype && (
              <Badge variant="secondary" className="text-xs">
                {archetype}
              </Badge>
            )}
            <Badge variant="outline" className="text-xs">
              Fase {currentPhase}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-3 min-w-[180px]">
          <div className="flex-1">
            <Progress value={progressPct} className="h-2" />
          </div>
          <span className="text-sm font-semibold tabular-nums">
            {progressPct}%
          </span>
        </div>
      </div>
      <Kpi3MicroRow
        dimsCaptured={dimsCaptured}
        dimsTotal={dimsTotal}
        completedCount={progressCompleted}
        totalCount={progressTotal}
        proximoHitoDays={proximoHitoDays}
      />
    </header>
  );
}
