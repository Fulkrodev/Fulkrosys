"use client";

/**
 * RectoresGeneratorPanel · SAN-C.MB-9.bis.3.
 *
 * Genera y descarga 2 documentos rectores del SGSI:
 *
 * - Manual SGSI (E-160 CCN-STIC 805): documento maestro con 4 niveles
 *   documentación + roles + procesos + métricas + mejora continua.
 * - Plan Director Seguridad (E-170 trianual): misión/visión + estrategia
 *   3 años + KPIs CCN-STIC 815 + responsables alta dirección.
 *
 * Refs: SAN-C.MB-9.bis.3 · cierra fantasma frontend MB-9.4.
 */
import * as React from "react";
import { FileText, Loader2, ScrollText } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  generateManualSgsiDocx,
  generatePlanDirectorDocx,
} from "@/lib/api/documents";

interface RectoresGeneratorPanelProps {
  projectId: string;
}

type Busy = "sgsi" | "director" | null;

export function RectoresGeneratorPanel({
  projectId,
}: RectoresGeneratorPanelProps) {
  const [busy, setBusy] = React.useState<Busy>(null);

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSgsi = async () => {
    setBusy("sgsi");
    try {
      const blob = await generateManualSgsiDocx(projectId);
      downloadBlob(blob, `manual_sgsi_${projectId}.docx`);
      toast.success("Manual SGSI generado", {
        description: "CCN-STIC 805 · 4 niveles documentación · firmable RSEG.",
      });
    } catch (e) {
      toast.error("Error generando Manual SGSI", {
        description:
          e instanceof Error ? e.message : "Inténtalo de nuevo.",
      });
    } finally {
      setBusy(null);
    }
  };

  const handleDirector = async () => {
    setBusy("director");
    try {
      const blob = await generatePlanDirectorDocx(projectId);
      downloadBlob(blob, `plan_director_${projectId}.docx`);
      toast.success("Plan Director generado", {
        description: "Trianual · KPIs CCN-STIC 815 · firmable Sponsor + RSEG.",
      });
    } catch (e) {
      toast.error("Error generando Plan Director", {
        description:
          e instanceof Error ? e.message : "Inténtalo de nuevo.",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documentos rectores</CardTitle>
        <p className="text-sm text-muted-foreground">
          Manual SGSI (CCN-STIC 805) · Plan Director Seguridad (trianual con
          KPIs CCN-STIC 815). Firmables por RSEG y Dirección.
        </p>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button onClick={handleSgsi} disabled={busy !== null}>
          {busy === "sgsi" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generando…
            </>
          ) : (
            <>
              <FileText className="mr-2 h-4 w-4" />
              Manual SGSI
            </>
          )}
        </Button>
        <Button
          onClick={handleDirector}
          disabled={busy !== null}
          variant="outline"
        >
          {busy === "director" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generando…
            </>
          ) : (
            <>
              <ScrollText className="mr-2 h-4 w-4" />
              Plan Director
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
