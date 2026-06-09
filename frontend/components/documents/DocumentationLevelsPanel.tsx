"use client";

/**
 * DocumentationLevelsPanel · SAN-C.MB-10.8.
 *
 * Visualiza la jerarquía CCN-STIC 805 de 4 niveles documentación SGSI con
 * los templates existentes agrupados por nivel canónico.
 *
 * Refs: SAN-C.MB-10.8 · cierra fantasma frontend MB-10.8.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { BookMarked } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

interface LevelSummary {
  level: number;
  name: string;
  description: string;
  approver_role: string;
  template_codes: string[];
  template_count: number;
}

const LEVEL_COLOR: Record<number, string> = {
  1: "bg-blue-50 text-blue-700 border-blue-200",
  2: "bg-violet-50 text-violet-700 border-violet-200",
  3: "bg-emerald-50 text-emerald-700 border-emerald-200",
  4: "bg-amber-50 text-amber-700 border-amber-200",
};

export function DocumentationLevelsPanel() {
  const query = useQuery<LevelSummary[]>({
    queryKey: ["m06-documentation-levels"],
    queryFn: () => api("/api/v1/documentation-levels"),
    staleTime: 60 * 60 * 1000,
  });

  if (query.isLoading) return <Skeleton className="h-48 w-full" />;
  if (query.isError || !query.data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookMarked className="h-4 w-4" />
          Jerarquía documental SGSI (CCN-STIC 805 · 4 niveles)
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          PSI · Normativas · Procedimientos · Instrucciones técnicas. Templates
          M06 mapeados al nivel canónico para auditoría ENAC.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {query.data.map((lvl) => (
          <div
            key={lvl.level}
            className={`rounded-md border p-3 ${
              LEVEL_COLOR[lvl.level] ?? ""
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium">
                  Nivel {lvl.level} — {lvl.name}
                </p>
                <p className="mt-1 text-xs">
                  Aprueba: <span className="font-mono">{lvl.approver_role}</span>
                </p>
              </div>
              <Badge variant="outline">
                {lvl.template_count} plantillas
              </Badge>
            </div>
            <p className="mt-2 text-sm">{lvl.description}</p>
            {lvl.template_codes.length > 0 ? (
              <details className="mt-2 text-xs">
                <summary className="cursor-pointer font-medium">
                  Ver template codes ({lvl.template_count})
                </summary>
                <p className="mt-1 font-mono">
                  {lvl.template_codes.join(" · ")}
                </p>
              </details>
            ) : (
              <p className="mt-2 text-xs italic">
                Plantillas técnicas se generan per cliente durante FASE 6.
              </p>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
