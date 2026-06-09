"use client";

/**
 * A11SeniorLayerCard · vista PAC + preguntas sectoriales + narrativa
 * ejecutiva A11 (ADR-037 SAN-D MB-15.4).
 *
 * A11 (Agent11AuditorVirtual) genera capa senior sobre M10:
 * - veredicto + probabilidad_certificacion_primera + plazo
 * - PAC priorizado sector-aware (3-5 fases)
 * - preguntas_contextuales (3-5 preguntas sectoriales)
 * - narrativa_md (markdown 400-600 palabras)
 *
 * Si A11 fallo · payload contiene `error` + `fallback: true` ·
 * card muestra fallback notice.
 */
import { AlertTriangle, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface Props {
  payload: Record<string, unknown>;
}

export function A11SeniorLayerCard({ payload }: Props) {
  const hasError = Boolean(payload.error || payload.fallback);

  if (hasError) {
    return (
      <Card className="border-l-4 border-l-fulkro-warning">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-fulkro-warning">
            <AlertTriangle className="h-4 w-4" strokeWidth={2.3} />
            A11 senior layer · fallback
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            A11 LLM no disponible en esta ejecución. M10 score determinista
            persistido. Reintentar más tarde o verificar configuración LLM.
          </p>
          {typeof payload.error === "string" && (
            <code className="mt-2 block text-xs text-muted-foreground">
              {payload.error}
            </code>
          )}
        </CardContent>
      </Card>
    );
  }

  const veredicto = typeof payload.veredicto === "string" ? payload.veredicto : null;
  const probability =
    typeof payload.probabilidad_certificacion_primera === "number"
      ? payload.probabilidad_certificacion_primera
      : null;
  const narrativa = typeof payload.narrativa_md === "string" ? payload.narrativa_md : null;
  const pac = Array.isArray(payload.pac) ? payload.pac : [];
  const sectoriales = Array.isArray(payload.preguntas_contextuales)
    ? payload.preguntas_contextuales
    : [];

  return (
    <Card className="border-l-4 border-l-fulkro-info">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-fulkro-info" strokeWidth={2.3} />
          A11 senior layer · auditor profesional
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {(veredicto || probability !== null) && (
          <div className="flex flex-wrap items-center gap-2">
            {veredicto && (
              <Badge
                variant={
                  veredicto.includes("favorable")
                    ? "success"
                    : veredicto.includes("desfavorable")
                      ? "danger"
                      : "warning"
                }
              >
                {veredicto.replace(/_/g, " ")}
              </Badge>
            )}
            {probability !== null && (
              <span className="text-sm text-muted-foreground">
                Probabilidad certificación primera:{" "}
                <strong className="text-fulkro-info">
                  {Math.round(probability * 100)}%
                </strong>
              </span>
            )}
          </div>
        )}

        {narrativa && (
          <div>
            <h4 className="mb-2 text-sm font-semibold">Narrativa ejecutiva</h4>
            <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">
              {narrativa}
            </pre>
          </div>
        )}

        {pac.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold">
              Plan de Acción Correctivo ({pac.length} fases)
            </h4>
            <ol className="space-y-2 text-sm">
              {pac.map((fase, idx) => (
                <li key={idx} className="rounded-md border bg-card p-2">
                  <code className="text-xs">{JSON.stringify(fase)}</code>
                </li>
              ))}
            </ol>
          </div>
        )}

        {sectoriales.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-semibold">
              Preguntas sectoriales ({sectoriales.length})
            </h4>
            <ul className="space-y-2 text-sm">
              {sectoriales.map((q, idx) => (
                <li key={idx} className="rounded-md border bg-card p-2">
                  <code className="text-xs">{JSON.stringify(q)}</code>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
