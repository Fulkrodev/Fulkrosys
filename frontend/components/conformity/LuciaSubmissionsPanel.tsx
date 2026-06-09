"use client";

/**
 * LuciaSubmissionsPanel · SAN-C.MB-10.3.
 *
 * Lista submissions LUCIA del proyecto + estado credenciales. Si el
 * cliente no ha registrado credenciales OAuth en CCN-CERT, el panel
 * indica fallback ``pending_credentials`` y los pasos a seguir.
 *
 * Refs: SAN-C.MB-10.3 · cierra fantasma frontend MB-10.3.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Info, Loader2 } from "lucide-react";

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

interface LuciaCredentialsStatus {
  configured: boolean;
  fallback_mode?: string;
  next_step?: string;
  organization_id?: string;
  endpoint_base_url?: string;
  verified_at?: string | null;
  expires_at?: string | null;
}

interface LuciaSubmission {
  id: string;
  incident_id: string | null;
  submission_id_remote: string | null;
  status: string;
  submitted_at: string | null;
  last_status_check: string | null;
  error_detail: string | null;
  created_at: string;
}

const STATUS_VARIANT: Record<string, "outline" | "success" | "warning" | "danger"> = {
  pending_credentials: "warning",
  pending: "outline",
  sent: "outline",
  acknowledged: "success",
  closed: "success",
  error: "danger",
};

interface LuciaSubmissionsPanelProps {
  projectId: string;
}

export function LuciaSubmissionsPanel({ projectId }: LuciaSubmissionsPanelProps) {
  const credsQuery = useQuery<LuciaCredentialsStatus>({
    queryKey: ["lucia-creds-status", projectId],
    queryFn: () =>
      api(`/api/v1/conformity/projects/${projectId}/lucia/credentials-status`),
    staleTime: 60 * 1000,
  });

  const submissionsQuery = useQuery<LuciaSubmission[]>({
    queryKey: ["lucia-submissions", projectId],
    queryFn: () =>
      api(`/api/v1/conformity/projects/${projectId}/lucia/submissions`),
    staleTime: 30 * 1000,
  });

  if (credsQuery.isLoading || submissionsQuery.isLoading) {
    return <Skeleton className="h-32 w-full" />;
  }

  const creds = credsQuery.data;
  const submissions = submissionsQuery.data ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          LUCIA federación CCN-CERT
          {creds?.configured ? (
            <Badge variant="outline" className="bg-green-50 text-green-700">
              <CheckCircle2 className="mr-1 h-3 w-3" />
              Credenciales OK
            </Badge>
          ) : (
            <Badge variant="outline">Sin credenciales</Badge>
          )}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Notificación incidentes significativos a CCN-CERT (art. 33 RD 311/2022 ·
          CCN-STIC 845). Requiere acreditación cliente sector público / NIS2.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {!creds?.configured ? (
          <Alert variant="info">
            <Info className="h-4 w-4" />
            <AlertTitle>Modo fallback · pending_credentials</AlertTitle>
            <AlertDescription className="text-sm">
              {creds?.next_step ??
                "Cliente debe aportar credenciales OAuth LUCIA. Mientras, los incidentes se generan en JSON canónico para subida manual al portal."}
            </AlertDescription>
          </Alert>
        ) : null}

        <div>
          <h3 className="mb-2 text-sm font-semibold">
            Submissions ({submissions.length})
          </h3>
          {submissions.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin submissions registrados todavía.
            </p>
          ) : (
            <div className="space-y-2">
              {submissions.map((s) => (
                <div
                  key={s.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium">
                      {s.submission_id_remote ?? "(sin ID remoto)"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Creado {new Date(s.created_at).toLocaleString()} ·{" "}
                      {s.submitted_at ? "enviado" : "no enviado"}
                    </p>
                  </div>
                  <Badge variant={STATUS_VARIANT[s.status] ?? "outline"}>
                    {s.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
