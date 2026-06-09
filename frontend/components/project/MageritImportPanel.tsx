/**
 * MageritImportPanel · Import XML análisis MAGERIT (SAN-C MB-11.4).
 *
 * Soporta FULKRO native (round-trip) y PILAR-compatible best-effort
 * (esquema MAGERIT v3 con xpath //asset, //threat, //safeguard).
 * NO soporta PILAR ``.mgr`` propietario.
 *
 * Flujo: drag-drop → preview (dry-run) → confirm import (persist).
 */
"use client";

import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, FileUp, Loader2, Upload } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  type ImportXmlPreviewResponse,
  type ImportXmlResponse,
  importMageritXml,
  previewMageritXml,
} from "@/lib/admin-magerit-import/api";

interface Props {
  analysisId: string;
}

export function MageritImportPanel({ analysisId }: Props) {
  const [file, setFile] = useState<File | null>(null);

  const previewMutation = useMutation<ImportXmlPreviewResponse, Error, File>({
    mutationFn: (f) => previewMageritXml(analysisId, f),
  });

  const importMutation = useMutation<ImportXmlResponse, Error, File>({
    mutationFn: (f) => importMageritXml(analysisId, f),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            Importar XML análisis <InfoTag term="MAGERIT" display="MAGERIT" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Formatos soportados</AlertTitle>
            <AlertDescription className="text-sm space-y-1 mt-1">
              <div>
                <Badge variant="secondary">FULKRO native</Badge> Round-trip del
                export-xml de FULKRO.
              </div>
              <div>
                <TooltipENS term="PILAR">
                  <Badge variant="secondary">PILAR-compat</Badge>
                </TooltipENS>{" "}
                XML estructurado MAGERIT v3 (xpath //asset, //threat, //safeguard).
              </div>
              <div className="text-muted-foreground text-xs mt-2">
                NO soportado: PILAR <code>.mgr</code> binario propietario
                (CCN no publica spec). Usar PILAR Desktop para exportar XML
                primero.
              </div>
            </AlertDescription>
          </Alert>

          <div className="border-2 border-dashed rounded-lg p-6 text-center">
            <FileUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <input
              id="xml-file"
              type="file"
              accept=".xml,application/xml,text/xml"
              aria-label="Seleccionar archivo XML del análisis MAGERIT a importar"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block mx-auto text-sm"
            />
            {file && (
              <p className="mt-2 text-sm">
                Seleccionado: <strong>{file.name}</strong> (
                {(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => file && previewMutation.mutate(file)}
              disabled={!file || previewMutation.isPending}
            >
              {previewMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Preview
            </Button>
            <Button
              onClick={() => file && importMutation.mutate(file)}
              disabled={!file || importMutation.isPending || !previewMutation.data}
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Confirmar import
            </Button>
          </div>
        </CardContent>
      </Card>

      {previewMutation.data && !importMutation.data && (
        <Alert>
          <AlertTitle>Preview · sin persistir aún</AlertTitle>
          <AlertDescription className="space-y-2 mt-2 text-sm">
            <Badge>{previewMutation.data.detected_format}</Badge>
            <ul className="list-disc pl-5">
              <li>
                <InfoTag term="activo" display="Activos" />:{" "}
                {previewMutation.data.assets_count}
              </li>
              <li>
                <InfoTag term="amenaza" display="Threats" />:{" "}
                {previewMutation.data.threat_assessments_count}
              </li>
              <li>
                <InfoTag term="salvaguarda" display="Salvaguardas" />:{" "}
                {previewMutation.data.safeguards_count}
              </li>
            </ul>
            {previewMutation.data.sample_asset_codes.length > 0 && (
              <div className="text-xs">
                Sample codes:{" "}
                {previewMutation.data.sample_asset_codes.join(", ")}
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}

      {importMutation.data && (
        <Alert variant="success">
          <AlertTitle>Import completado</AlertTitle>
          <AlertDescription className="space-y-1 mt-2 text-sm">
            <div>Formato detectado: {importMutation.data.detected_format}</div>
            <div>Activos creados: {importMutation.data.assets_created}</div>
            <div>
              Threat assessments:{" "}
              {importMutation.data.threat_assessments_created}
            </div>
            <div>
              Salvaguardas: {importMutation.data.safeguards_created}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {(previewMutation.error || importMutation.error) && (
        <Alert variant="danger">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription className="text-sm">
            {previewMutation.error?.message ?? importMutation.error?.message}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
