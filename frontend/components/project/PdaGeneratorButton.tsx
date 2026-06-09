"use client";

/**
 * PdaGeneratorButton · SAN-C.MB-9.bis.2.
 *
 * Genera y descarga Plan de Adecuación (E-150 CCN-STIC 806) DOCX
 * aglutinando datos cross-motor M01+M02+M03+M04+M17 (categoría +
 * análisis riesgos + DdA + gaps + plan WBS).
 *
 * Refs: SAN-C.MB-9.bis.2 · cierra fantasma frontend MB-9.3.
 */
import * as React from "react";
import { FileDown, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { generatePdaDocx } from "@/lib/api/planning";

interface PdaGeneratorButtonProps {
  projectId: string;
}

export function PdaGeneratorButton({ projectId }: PdaGeneratorButtonProps) {
  const [generating, setGenerating] = React.useState(false);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const blob = await generatePdaDocx(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `plan_adecuacion_${projectId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PdA generado", {
        description:
          "CCN-STIC 806 · enviar a dirección para revisión y firma.",
      });
    } catch (e) {
      toast.error("Error generando PdA", {
        description:
          e instanceof Error
            ? e.message
            : "Verificar datos M01+M02+M03+M04 disponibles.",
      });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Plan de Adecuación <TooltipENS term="PDA" /> (CCN-STIC 806)
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Documento maestro · aglutina categorización · análisis de riesgos ·{" "}
          <InfoTag term="DdA" display="DdA" /> · gaps · plan acciones correctivas ·
          concienciación.
        </p>
      </CardHeader>
      <CardContent>
        <Button onClick={handleGenerate} disabled={generating}>
          {generating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generando PdA…
            </>
          ) : (
            <>
              <FileDown className="mr-2 h-4 w-4" />
              Generar Plan Adecuación (DOCX)
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
