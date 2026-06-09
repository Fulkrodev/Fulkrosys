"use client";

/**
 * DraftReportView · CLUSTER 3 Phase C4.3 auditor portal draft report.
 *
 * Display:
 * - Inline iframe HTML preview (GET endpoint · no signed · no PDF)
 * - "Generar borrador firmado" CTA (POST endpoint · signed PDF download)
 * - Auditor opinion textarea + recommendation selector (override defaults)
 * - Sample PDF metadata post-generation (sha256 + signature algo + recommendation)
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileText,
  Loader2,
} from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  type GeneratedReportMeta,
  type Recommendation,
  RECOMMENDATION_LABEL,
  RECOMMENDATION_VARIANT,
  downloadBlob,
  generateDraftReportAuditor,
  getDraftReportPreviewAuditor,
} from "@/lib/api/draft-report";

interface Props {
  token: string;
}

const RECOMMENDATION_VALUES: (Recommendation | "auto")[] = [
  "auto",
  "APROBAR",
  "APROBAR_CON_CONDICIONES",
  "NO_APROBAR",
];

export function DraftReportView({ token }: Props) {
  const [opinion, setOpinion] = React.useState("");
  const [auditorName, setAuditorName] = React.useState("");
  const [recommendation, setRecommendation] = React.useState<
    Recommendation | "auto"
  >("auto");
  const [periodStart, setPeriodStart] = React.useState("");
  const [periodEnd, setPeriodEnd] = React.useState("");
  const [lastMeta, setLastMeta] = React.useState<GeneratedReportMeta | null>(
    null,
  );

  const previewQ = useQuery<string>({
    queryKey: ["auditor-portal", "draft-report", "preview", token],
    queryFn: () => getDraftReportPreviewAuditor(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const generateMut = useMutation({
    mutationFn: async () => {
      const result = await generateDraftReportAuditor(token, {
        auditor_opinion_text: opinion.trim() || undefined,
        recommendation:
          recommendation !== "auto" ? recommendation : undefined,
        auditor_name: auditorName.trim() || undefined,
        audit_period_start: periodStart || undefined,
        audit_period_end: periodEnd || undefined,
      });
      const filename = `borrador_auditoria_${result.meta.pdf_sha256.slice(
        0, 8,
      )}.pdf`;
      downloadBlob(result.blob, filename);
      setLastMeta(result.meta);
      return result.meta;
    },
  });

  return (
    <div className="space-y-4" data-testid="draft-report-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Borrador del informe de auditoría
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Alert>
            <AlertTitle>Acceso de solo lectura</AlertTitle>
            <AlertDescription>
              Este es un borrador generado automáticamente combinando tus
              anotaciones, aclaraciones y la cobertura DdA-Evidencias. Puedes
              previsualizarlo abajo y descargar la versión firmada Ed25519
              cuando lo necesites.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Opinión preliminar (opcional)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <Label htmlFor="draft-auditor-name">
              Nombre del auditor (opcional)
            </Label>
            <Input
              id="draft-auditor-name"
              value={auditorName}
              onChange={(e) => setAuditorName(e.target.value)}
              placeholder="Auditor ENAC · acred X"
              aria-label="Nombre del auditor"
              data-testid="draft-auditor-name-input"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="draft-period-start">Periodo desde</Label>
              <Input
                id="draft-period-start"
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                aria-label="Inicio del periodo auditado"
                data-testid="draft-period-start"
              />
            </div>
            <div>
              <Label htmlFor="draft-period-end">Periodo hasta</Label>
              <Input
                id="draft-period-end"
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                aria-label="Fin del periodo auditado"
                data-testid="draft-period-end"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="draft-recommendation">Recomendación</Label>
            <Select
              value={recommendation}
              onValueChange={(v) =>
                setRecommendation(v as Recommendation | "auto")
              }
            >
              <SelectTrigger
                id="draft-recommendation"
                aria-label="Recomendación preliminar"
                data-testid="draft-recommendation-select"
                className="w-72"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RECOMMENDATION_VALUES.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v === "auto"
                      ? "Auto (derivado de los hallazgos)"
                      : RECOMMENDATION_LABEL[v]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="draft-opinion-text">
              Opinión libre (texto preliminar)
            </Label>
            <Textarea
              id="draft-opinion-text"
              rows={5}
              value={opinion}
              onChange={(e) => setOpinion(e.target.value)}
              placeholder="Resume tu opinión preliminar. Quedará embebida en el borrador firmado."
              aria-label="Opinión preliminar del auditor"
              data-testid="draft-opinion-textarea"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => generateMut.mutate()}
              disabled={generateMut.isPending}
              data-testid="draft-generate-button"
            >
              <Download size={14} className="mr-1" aria-hidden="true" />
              {generateMut.isPending
                ? "Generando…"
                : "Generar borrador firmado (Ed25519)"}
            </Button>
            {generateMut.isError ? (
              <span className="text-[12px] text-fulkro-danger-700">
                Error: {String(generateMut.error)}
              </span>
            ) : null}
          </div>
          {lastMeta ? (
            <Alert>
              <CheckCircle size={14} aria-hidden="true" />
              <AlertTitle>Borrador generado</AlertTitle>
              <AlertDescription>
                <p>
                  <Badge variant={RECOMMENDATION_VARIANT[lastMeta.recommendation]}>
                    {RECOMMENDATION_LABEL[lastMeta.recommendation]}
                  </Badge>
                </p>
                <p className="mt-1 font-mono text-[10px]">
                  sha256: {lastMeta.pdf_sha256.slice(0, 32)}…
                </p>
                <p className="font-mono text-[10px]">
                  algoritmo: {lastMeta.signature_algorithm} ·{" "}
                  {(lastMeta.size_bytes / 1024).toFixed(1)} KB
                </p>
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Previsualización del borrador</CardTitle>
        </CardHeader>
        <CardContent>
          {previewQ.isLoading ? (
            <div
              className="flex items-center gap-2 text-sm text-fulkro-ink-500"
              data-testid="draft-preview-loading"
            >
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              Renderizando previsualización…
            </div>
          ) : previewQ.isError || !previewQ.data ? (
            <Alert variant="danger" data-testid="draft-preview-error">
              <AlertCircle size={14} aria-hidden="true" />
              <AlertTitle>No se pudo renderizar la previsualización</AlertTitle>
              <AlertDescription>Reintenta más tarde.</AlertDescription>
            </Alert>
          ) : (
            <iframe
              srcDoc={previewQ.data}
              title="Previsualización del borrador del informe de auditoría"
              data-testid="draft-preview-iframe"
              sandbox="allow-same-origin"
              className="h-[900px] w-full rounded-md border border-fulkro-ink-300"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
