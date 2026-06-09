"use client";

/**
 * AuditScheduleCountdown · SAN-C.MB-10.6.
 *
 * Countdown de próxima auditoría programada (bienal art. 31 RD 311/2022 ·
 * extraordinaria por cambio sustancial). Render compacto con badge color
 * por urgencia (rojo < 30d · ámbar 30-90d · verde > 90d).
 *
 * Refs: SAN-C.MB-10.6 · cierra fantasma frontend MB-10.6.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

interface AuditScheduleEntry {
  id: string;
  audit_type: string;
  next_audit_due: string;
  last_audit_completed: string | null;
  last_audit_result: string | null;
  triggered_by: string;
  days_until_due: number;
}

const TYPE_LABEL: Record<string, string> = {
  biannual: "Bienal (art. 31)",
  extraordinary: "Extraordinaria",
  internal: "Interna",
};

function variantForDays(days: number): "outline" | "warning" | "danger" {
  if (days <= 30) return "danger";
  if (days <= 90) return "warning";
  return "outline";
}

interface AuditScheduleCountdownProps {
  projectId: string;
}

export function AuditScheduleCountdown({
  projectId,
}: AuditScheduleCountdownProps) {
  const query = useQuery<AuditScheduleEntry[]>({
    queryKey: ["audit-schedule", projectId],
    queryFn: () =>
      api(`/api/v1/conformity/projects/${projectId}/audit-schedule?horizon_days=730`),
    staleTime: 60 * 1000,
  });

  if (query.isLoading) return <Skeleton className="h-24 w-full" />;
  if (query.isError || !query.data) return null;
  if (query.data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4" />
            Auditorías programadas
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Sin auditorías programadas en los próximos 24 meses. La auditoría
            bienal (art. 31 RD 311/2022) se activará automáticamente al
            obtener conformidad Media/Alta.
          </p>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4" />
          Auditorías programadas
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Art. 31 RD 311/2022 · auditoría externa bienal Media/Alta +
          extraordinarias por cambios sustanciales (cloud · CPD · fusión).
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {query.data.map((entry) => {
          const dueDate = new Date(entry.next_audit_due).toLocaleDateString();
          const days = entry.days_until_due;
          return (
            <div
              key={entry.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm"
            >
              <div className="min-w-0">
                <p className="font-medium">
                  {TYPE_LABEL[entry.audit_type] ?? entry.audit_type}
                </p>
                <p className="text-xs text-muted-foreground">
                  Vence {dueDate} · disparador: {entry.triggered_by}
                </p>
              </div>
              <Badge variant={variantForDays(days)}>
                {days >= 0
                  ? `${days} días`
                  : `Vencida hace ${Math.abs(days)}d`}
              </Badge>
            </div>
          );
        })}
        {query.data.some((e) => e.days_until_due <= 90) ? (
          <Alert variant="warning">
            <AlertTitle>Auditoría próxima</AlertTitle>
            <AlertDescription className="text-sm">
              Iniciar contacto con entidad certificadora ENAC y preparar
              dossier auditoría interna (E-701) con antelación mínima 90 días.
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
