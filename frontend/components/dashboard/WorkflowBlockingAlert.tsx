"use client";

/**
 * WorkflowBlockingAlert · banner destacado destructive en home admin
 * (ADR-036 SAN-D MB-17.5). Lista feature flags blocking transición a
 * target_phase con fix_url cada uno · CTA "Resolver" llamando al
 * motor correspondiente.
 *
 * Coherencia visual ADR-035: shadcn Card composition + Button asChild
 * + fulkro-danger palette · iconos lucide · sin styling hardcoded.
 *
 * Default targetPhase = 9 (Conformidad) · puede customizarse para
 * mostrar bloqueantes a fase intermedia (8 Verificación etc).
 */
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { workflowApi } from "@/lib/api/workflow";
import { cn } from "@/lib/utils";

interface Props {
  projectId: string;
  targetPhase?: number;
}

export function WorkflowBlockingAlert({
  projectId,
  targetPhase = 9,
}: Props) {
  const { data } = useQuery({
    queryKey: ["workflow-blocking", projectId, targetPhase],
    queryFn: () => workflowApi.canTransition(projectId, targetPhase),
    refetchInterval: 60_000,
    staleTime: 30_000,
    enabled: Boolean(projectId),
  });

  if (!data || data.can_transition || data.blocking_issues.length === 0) {
    return null;
  }

  const issueWord = data.blocking_issues.length === 1 ? "bloqueante" : "bloqueantes";

  return (
    <Card className="border-l-4 border-l-fulkro-danger">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-fulkro-danger">
          <AlertTriangle className="h-5 w-5" strokeWidth={2.3} />
          Transición bloqueada · Fase {data.target_phase}: {data.target_phase_label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-muted-foreground">
          Resuelve {data.blocking_issues.length} {issueWord} antes de avanzar a {data.target_phase_label}:
        </p>
        <ul className="space-y-2">
          {data.blocking_issues.map((issue) => (
            <li
              key={issue.feature_key}
              className="flex flex-wrap items-start justify-between gap-3 rounded-md border bg-card p-3"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{issue.description}</p>
                <code className="text-xs text-muted-foreground">
                  {issue.feature_key}
                </code>
              </div>
              <Link
                href={issue.fix_url}
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "shrink-0",
                )}
              >
                Resolver
                <ArrowRight className="ml-1 h-3 w-3" strokeWidth={2.3} />
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
