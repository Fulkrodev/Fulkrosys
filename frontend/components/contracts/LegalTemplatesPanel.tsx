"use client";

/**
 * LegalTemplatesPanel · SAN-C.MB-10.2.
 *
 * Lista 7 modelos legales DOCX canónicos con CTA "Generar". Para
 * plantillas que requieren ``provider_name`` (terceros · DPA · pentesting),
 * abre prompt simple para capturar los datos del proveedor antes
 * de invocar el endpoint.
 *
 * Refs: SAN-C.MB-10.2 · cierra fantasma frontend MB-10.2.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2 } from "lucide-react";
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
  type LegalTemplateInfo,
  generateLegalTemplate,
  listLegalTemplates,
} from "@/lib/api/legal-templates";

interface LegalTemplatesPanelProps {
  projectId: string;
}

export function LegalTemplatesPanel({ projectId }: LegalTemplatesPanelProps) {
  const catalogQuery = useQuery<LegalTemplateInfo[]>({
    queryKey: ["legal-templates-catalog"],
    queryFn: listLegalTemplates,
    staleTime: 60 * 60 * 1000,
  });

  const [busySlug, setBusySlug] = React.useState<string | null>(null);

  const handleGenerate = async (template: LegalTemplateInfo) => {
    let providerName: string | undefined;
    let providerCif: string | undefined;
    if (template.requires_provider) {
      providerName =
        window.prompt(
          `${template.code} requiere proveedor. Nombre del proveedor:`,
        ) ?? undefined;
      if (!providerName) {
        toast.warning("Generación cancelada", {
          description: "Se necesita el nombre del proveedor.",
        });
        return;
      }
      providerCif =
        window.prompt(`CIF/identificador fiscal de ${providerName} (opcional):`) ??
        undefined;
    }

    setBusySlug(template.slug);
    try {
      const blob = await generateLegalTemplate(projectId, template.slug, {
        provider_name: providerName,
        provider_cif: providerCif,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${template.slug}_${projectId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${template.code} generado`, {
        description: template.title,
      });
    } catch (e) {
      toast.error("Error generando modelo legal", {
        description: e instanceof Error ? e.message : template.title,
      });
    } finally {
      setBusySlug(null);
    }
  };

  if (catalogQuery.isLoading) {
    return <Skeleton className="h-40 w-full" />;
  }
  if (catalogQuery.isError || !catalogQuery.data) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          No se pudo cargar el catálogo de modelos legales.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Modelos legales (DOCX)</CardTitle>
        <p className="text-sm text-muted-foreground">
          7 plantillas canónicas: contrato servicios · NDA · encargo RGPD · cadena
          suministro CCN-STIC 823 · confidencialidad empleados · DPA · pentesting.
        </p>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {catalogQuery.data.map((template) => (
          <div
            key={template.slug}
            className="flex flex-col gap-2 rounded-md border p-3"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium">{template.title}</p>
              <Badge variant="outline" className="shrink-0">
                {template.code}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {template.description}
            </p>
            {template.requires_provider ? (
              <Badge variant="outline" className="w-fit">
                Requiere proveedor
              </Badge>
            ) : null}
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
                  <FileText className="mr-2 h-4 w-4" />
                  Generar (DOCX)
                </>
              )}
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
