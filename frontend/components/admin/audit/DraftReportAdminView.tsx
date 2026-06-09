"use client";

/**
 * DraftReportAdminView · CLUSTER 3 Phase C4.3 · admin twin.
 *
 * Same preview iframe + admin POST endpoint generate signed PDF.
 * Mirror DraftReportView pero con admin permissions + cross-project legit.
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
  generateDraftReportAdmin,
  getDraftReportPreviewAdmin,
} from "@/lib/api/draft-report";

interface Props {
  projectId: string;
}

const RECOMMENDATION_VALUES: (Recommendation | "auto")[] = [
  "auto",
  "APROBAR",
  "APROBAR_CON_CONDICIONES",
  "NO_APROBAR",
];

export function DraftReportAdminView({ projectId }: Props) {
  const [opinion, setOpinion] = React.useState("");
  const [recommendation, setRecommendation] = React.useState<
    Recommendation | "auto"
  >("auto");
  const [lastMeta, setLastMeta] = React.useState<GeneratedReportMeta | null>(
    null,
  );

  const previewQ = useQuery<string>({
    queryKey: ["admin", "audit", "draft-report", "preview", projectId],
    queryFn: () => getDraftReportPreviewAdmin(projectId),
    staleTime: 60_000,
  });

  const generateMut = useMutation({
    mutationFn: async () => {
      const result = await generateDraftReportAdmin(projectId, {
        auditor_opinion_text: opinion.trim() || undefined,
        recommendation:
          recommendation !== "auto" ? recommendation : undefined,
      });
      const filename = `borrador_admin_${result.meta.pdf_sha256.slice(
        0, 8,
      )}.pdf`;
      downloadBlob(result.blob, filename);
      setLastMeta(result.meta);
      return result.meta;
    },
  });

  return (
    <div className="space-y-4" data-testid="draft-report-admin-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Borrador del informe de auditoría · admin
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Alert>
            <AlertTitle>Generación admin</AlertTitle>
            <AlertDescription>
              Genera un borrador del informe firmado Ed25519. Cada generación
              queda registrada en el audit log inmutable como{" "}
              <code className="font-mono">admin.draft_report.generated</code>.
            </AlertDescription>
          </Alert>
          <div>
            <Label htmlFor="draft-admin-recommendation">Recomendación</Label>
            <Select
              value={recommendation}
              onValueChange={(v) =>
                setRecommendation(v as Recommendation | "auto")
              }
            >
              <SelectTrigger
                id="draft-admin-recommendation"
                className="w-72"
                aria-label="Recomendación"
                data-testid="draft-admin-recommendation-select"
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
            <Label htmlFor="draft-admin-opinion">Opinión preliminar</Label>
            <Textarea
              id="draft-admin-opinion"
              rows={4}
              value={opinion}
              onChange={(e) => setOpinion(e.target.value)}
              placeholder="Opinión que se embebe en el borrador (opcional)…"
              aria-label="Opinión preliminar admin"
              data-testid="draft-admin-opinion-textarea"
            />
          </div>
          <Button
            onClick={() => generateMut.mutate()}
            disabled={generateMut.isPending}
            data-testid="draft-admin-generate-button"
          >
            <Download size={14} className="mr-1" aria-hidden="true" />
            {generateMut.isPending
              ? "Generando…"
              : "Generar borrador firmado (admin)"}
          </Button>
          {generateMut.isError ? (
            <Alert variant="danger">
              <AlertCircle size={14} aria-hidden="true" />
              <AlertTitle>No se pudo generar</AlertTitle>
              <AlertDescription>{String(generateMut.error)}</AlertDescription>
            </Alert>
          ) : null}
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
                  sha256: {lastMeta.pdf_sha256.slice(0, 32)}… ·{" "}
                  {(lastMeta.size_bytes / 1024).toFixed(1)} KB
                </p>
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Previsualización</CardTitle>
        </CardHeader>
        <CardContent>
          {previewQ.isLoading ? (
            <div
              className="flex items-center gap-2 text-sm text-fulkro-ink-500"
              data-testid="draft-admin-preview-loading"
            >
              <Loader2 size={14} className="animate-spin" aria-hidden="true" />
              Renderizando previsualización…
            </div>
          ) : previewQ.isError || !previewQ.data ? (
            <Alert variant="danger" data-testid="draft-admin-preview-error">
              <AlertCircle size={14} aria-hidden="true" />
              <AlertTitle>No se pudo renderizar</AlertTitle>
              <AlertDescription>Reintenta más tarde.</AlertDescription>
            </Alert>
          ) : (
            <iframe
              srcDoc={previewQ.data}
              title="Previsualización del borrador (admin)"
              data-testid="draft-admin-preview-iframe"
              sandbox="allow-same-origin"
              className="h-[900px] w-full rounded-md border border-fulkro-ink-300"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
