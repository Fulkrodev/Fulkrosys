/**
 * A11AuditorVirtualButton · trigger UI A11 Auditor Virtual (MB-5.0).
 *
 * Backend: POST /api/v1/projects/{id}/agents/11/run-supplementary-audit
 * (wrapper auto-compone m10_audit_result + client_context).
 *
 * Cierra fantasma A11 detectado en MB-8.0 mini-audit.
 */
"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, ScanText, ShieldCheck, Sparkles } from "lucide-react";
import * as React from "react";
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
import { api } from "@/lib/api";

interface A11WrapperResponse {
  run_id: string;
  a11_result: {
    pac_priorizado?: Array<Record<string, unknown>>;
    preguntas_contextuales_sector?: Array<Record<string, unknown>>;
    narrativa_ejecutiva?: string;
    metadata?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

export function A11AuditorVirtualButton({
  projectId,
}: {
  projectId: string;
}) {
  const mutation = useMutation<A11WrapperResponse, Error, void>({
    mutationFn: () =>
      api<A11WrapperResponse>(
        `/api/v1/projects/${projectId}/agents/11/run-supplementary-audit`,
        { method: "POST" },
      ),
    onSuccess: () => {
      toast.success("Auditoría virtual completada");
    },
    onError: (err) => {
      toast.error("Auditoría virtual falló", {
        description: err.message,
      });
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck size={16} /> Auditoría virtual (A11)
        </CardTitle>
        <CardDescription>
          Análisis suplementario senior sobre el último audit-sim M10:
          PAC priorizado · 3-5 preguntas contextuales del sector ·
          narrativa ejecutiva con veredicto.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Sparkles size={14} />
          )}
          {mutation.isPending
            ? "Analizando…"
            : "Ejecutar auditoría virtual"}
        </Button>

        {mutation.isError ? (
          <Alert variant="danger">
            <AlertTitle>Error A11</AlertTitle>
            <AlertDescription>{mutation.error?.message}</AlertDescription>
          </Alert>
        ) : null}

        {mutation.data ? (
          <A11ResultBlock data={mutation.data} />
        ) : null}
      </CardContent>
    </Card>
  );
}

function A11ResultBlock({ data }: { data: A11WrapperResponse }) {
  const result = data.a11_result;
  const pac = result.pac_priorizado ?? [];
  const preguntas = result.preguntas_contextuales_sector ?? [];

  return (
    <div className="space-y-3 rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-50/50 p-3 text-xs">
      <p className="font-mono text-[10px] text-fulkro-ink-500">
        Basado en M10 run {data.run_id.slice(0, 8)}
      </p>

      {result.narrativa_ejecutiva ? (
        <div>
          <p className="mb-1 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
            <ScanText size={11} /> Narrativa ejecutiva
          </p>
          <div className="whitespace-pre-line rounded-md bg-white p-3 text-[12px] leading-relaxed text-fulkro-ink-700">
            {result.narrativa_ejecutiva}
          </div>
        </div>
      ) : null}

      {pac.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
            PAC priorizado · {pac.length} fases
          </p>
          <ol className="list-decimal space-y-1 pl-5">
            {pac.slice(0, 8).map((fase, idx) => (
              <li
                key={idx}
                className="rounded-md bg-white p-2 text-[11px] text-fulkro-ink-700"
              >
                <pre className="whitespace-pre-wrap font-sans">
                  {JSON.stringify(fase, null, 2)}
                </pre>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {preguntas.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-fulkro-ink-500">
            Preguntas contextuales sector · {preguntas.length}
          </p>
          <ul className="space-y-1">
            {preguntas.slice(0, 6).map((p, idx) => (
              <li
                key={idx}
                className="rounded-md bg-white p-2 text-[11px] text-fulkro-ink-700"
              >
                <pre className="whitespace-pre-wrap font-sans">
                  {JSON.stringify(p, null, 2)}
                </pre>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
