"use client";

/**
 * ExcelTemplatesGrid · SAN-C.MB-10.1.
 *
 * Grid de las 16 plantillas Excel canónicas (CCN-STIC + manual ENS) con
 * un botón "Generar" por card. Descarga XLSX directa del backend.
 *
 * Refs: SAN-C.MB-10.1 · cierra fantasma frontend MB-10.1.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileSpreadsheet, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type ExcelTemplateInfo,
  generateExcelTemplate,
  listExcelTemplates,
} from "@/lib/api/excel-templates";

interface ExcelTemplatesGridProps {
  projectId: string;
}

export function ExcelTemplatesGrid({ projectId }: ExcelTemplatesGridProps) {
  const catalogQuery = useQuery<ExcelTemplateInfo[]>({
    queryKey: ["excel-templates-catalog"],
    queryFn: listExcelTemplates,
    staleTime: 60 * 60 * 1000, // catálogo canónico estable
  });

  const [busySlug, setBusySlug] = React.useState<string | null>(null);

  const handleGenerate = async (template: ExcelTemplateInfo) => {
    setBusySlug(template.slug);
    try {
      const blob = await generateExcelTemplate(projectId, template.slug);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${template.slug}_${projectId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${template.code} generado`, {
        description: template.title,
      });
    } catch (e) {
      toast.error("Error generando plantilla", {
        description: e instanceof Error ? e.message : template.title,
      });
    } finally {
      setBusySlug(null);
    }
  };

  if (catalogQuery.isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <Skeleton key={idx} className="h-40 w-full" />
        ))}
      </div>
    );
  }

  if (catalogQuery.isError || !catalogQuery.data) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          No se pudo cargar el catálogo de plantillas Excel.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
      {catalogQuery.data.map((template) => (
        <Card key={template.slug} className="flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-base">{template.title}</CardTitle>
              <Badge variant="outline" className="shrink-0">
                {template.code}
              </Badge>
            </div>
            {template.ccn_stic ? (
              <p className="text-xs text-muted-foreground">
                {template.ccn_stic}
              </p>
            ) : null}
          </CardHeader>
          <CardContent className="flex flex-1 flex-col justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {template.description}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleGenerate(template)}
              disabled={busySlug !== null}
            >
              {busySlug === template.slug ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generando…
                </>
              ) : (
                <>
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                  Generar (XLSX)
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
