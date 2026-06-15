"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { remediationClientApi } from "@/lib/api/remediation-client";

const QKEY = ["client-portal", "remediation", "jobs"] as const;

// Chips amistosos · NUNCA rojo (R29). Estados negativos en ámbar suave.
function chipClass(estado: string): string {
  if (estado.includes("seguro") || estado.includes("correcto")) {
    return "bg-emerald-100 text-emerald-800";
  }
  if (estado.includes("autorización")) {
    return "bg-amber-100 text-amber-800";
  }
  if (estado.includes("revis")) {
    return "bg-amber-100 text-amber-800";
  }
  return "bg-slate-100 text-slate-700";
}

export function RemediationClienteView() {
  const qc = useQueryClient();
  const jobsQ = useQuery({
    queryKey: QKEY,
    queryFn: () => remediationClientApi.list(),
    staleTime: 20_000,
  });
  const authorize = useMutation({
    mutationFn: (jobId: string) => remediationClientApi.authorize(jobId),
    onSuccess: () => {
      toast.success("¡Gracias! Lo aplicamos por ti. Sin prisa por tu parte.");
      void qc.invalidateQueries({ queryKey: QKEY });
    },
    onError: (e) => {
      // R29: nada de error crudo al cliente · detalle a consola para soporte.
      console.error("Remediation authorize error:", e);
      toast.error(
        "Hubo un problema al procesar tu solicitud. Por favor, inténtalo de nuevo.",
      );
    },
  });

  const jobs = jobsQ.data?.jobs ?? [];
  const pending = jobs.filter((j) => j.necesita_autorizacion);
  const rest = jobs.filter((j) => !j.necesita_autorizacion);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900">
          <ShieldCheck className="size-6 text-emerald-600" />
          Mejoras automáticas de seguridad
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Estas son las mejoras que aplicamos en tus sistemas para protegerlos. La
          mayoría se hacen solas; algunas necesitan tu visto bueno antes. Sin prisa
          por tu parte.
        </p>
      </div>

      {jobsQ.isLoading ? (
        <div className="flex items-center gap-2 py-6 text-slate-600">
          <Loader2 className="size-4 animate-spin" /> Cargando…
        </div>
      ) : jobsQ.isError ? (
        <Alert className="border-amber-200 bg-amber-50">
          <AlertTitle className="text-amber-900">
            No pudimos cargar tus mejoras
          </AlertTitle>
          <AlertDescription className="text-amber-800">
            Recarga la página en un momento.
          </AlertDescription>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => void jobsQ.refetch()}
            data-testid="remediation-cliente-retry"
          >
            Reintentar
          </Button>
        </Alert>
      ) : jobs.length === 0 ? (
        <Card className="border-slate-200 bg-white">
          <CardContent className="py-8 text-center text-slate-600">
            <CheckCircle2 className="mx-auto mb-2 size-8 text-emerald-500" />
            Todo en orden por ahora. Te avisaremos si hay algo que mejorar.
          </CardContent>
        </Card>
      ) : (
        <>
          {pending.length > 0 ? (
            <Card className="border-amber-200 bg-white">
              <CardHeader>
                <CardTitle className="text-lg text-slate-900">
                  Necesitan tu autorización
                </CardTitle>
                <CardDescription className="text-slate-600">
                  Son cambios que podrían afectar a algún acceso · por eso te
                  pedimos el visto bueno antes de aplicarlos.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {pending.map((job) => (
                  <div
                    key={job.id}
                    className="rounded-lg border border-amber-200 bg-amber-50/60 p-4"
                  >
                    <p className="font-semibold text-slate-900">{job.title}</p>
                    {job.explicacion ? (
                      <p className="mt-1 text-sm text-slate-700">
                        {job.explicacion}
                      </p>
                    ) : null}
                    <Button
                      size="sm"
                      className="mt-3 bg-emerald-600 text-white hover:bg-emerald-700"
                      disabled={authorize.isPending}
                      onClick={() => authorize.mutate(job.id)}
                      data-testid="remediation-cliente-authorize"
                    >
                      {authorize.isPending ? (
                        <Loader2 className="mr-1 size-3.5 animate-spin" />
                      ) : null}
                      Autorizar esta mejora
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Card className="border-slate-200 bg-white">
            <CardHeader>
              <CardTitle className="text-lg text-slate-900">Historial</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {rest.length === 0 ? (
                <p className="py-2 text-sm text-slate-500">
                  Aún no hay mejoras aplicadas.
                </p>
              ) : (
                rest.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between gap-3 rounded-md border border-slate-100 bg-slate-50 p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-900">
                        {job.title}
                      </p>
                      {job.explicacion ? (
                        <p className="truncate text-xs text-slate-500">
                          {job.explicacion}
                        </p>
                      ) : null}
                    </div>
                    <span
                      className={
                        "shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold " +
                        chipClass(job.estado)
                      }
                    >
                      {job.estado}
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
