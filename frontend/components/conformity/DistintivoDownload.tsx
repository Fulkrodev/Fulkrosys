"use client";

/**
 * Distintivo Download · SAN-C.MB-9.bis.1.
 *
 * Renderiza preview del distintivo SVG público + 4 acciones:
 *
 * - Descargar Declaración Conformidad Básica E-180 (DOCX firmable RSEG)
 * - Descargar distintivo SVG
 * - Copiar snippet HTML embed-able en sede electrónica
 * - Abrir vista pública (sin auth)
 *
 * Refs: SAN-C.MB-9.bis.1 · cierra fantasma frontend MB-9.2.
 */
import * as React from "react";
import { Copy, Download, ExternalLink, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type CertIdInfo,
  generateDeclarationDocx,
  getCertIdInfo,
  getPublicBadgeUrl,
} from "@/lib/api/conformity";

interface DistintivoDownloadProps {
  projectId: string;
}

export function DistintivoDownload({ projectId }: DistintivoDownloadProps) {
  const [info, setInfo] = React.useState<CertIdInfo | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [generating, setGenerating] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getCertIdInfo(projectId)
      .then((data) => {
        if (!cancelled) {
          setInfo(data);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("No se pudo resolver el cert_id del proyecto");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const handleGenerateDeclaration = async () => {
    setGenerating(true);
    try {
      const blob = await generateDeclarationDocx(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `declaracion_conformidad_${
        info?.cert_id ?? projectId
      }.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Declaración descargada", {
        description: "Firmar por RSEG y publicar en sede electrónica.",
      });
    } catch (e) {
      toast.error("Error generando declaración", {
        description: e instanceof Error ? e.message : "Inténtalo de nuevo.",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleCopyEmbed = async () => {
    if (!publicBadgeAbsoluteUrl) return;
    const snippet = `<a href="${publicBadgeAbsoluteUrl}" target="_blank" rel="noopener">\n  <img src="${publicBadgeAbsoluteUrl}" alt="Distintivo Conformidad ENS" width="200" />\n</a>`;
    try {
      await navigator.clipboard.writeText(snippet);
      toast.success("Snippet copiado", {
        description: "Pega el HTML en la sede electrónica del cliente.",
      });
    } catch {
      toast.error("Copia fallida", {
        description: "Selecciona y copia manualmente el snippet.",
      });
    }
  };

  const handleDownloadSvg = () => {
    if (!publicBadgePath || !info) return;
    const a = document.createElement("a");
    a.href = publicBadgePath;
    a.download = `distintivo_${info.cert_id}.svg`;
    a.click();
  };

  const handleOpenPublic = () => {
    if (!publicBadgePath) return;
    window.open(publicBadgePath, "_blank", "noopener,noreferrer");
  };

  const publicBadgePath = info?.cert_id
    ? getPublicBadgeUrl(info.cert_id)
    : null;
  const publicBadgeAbsoluteUrl =
    publicBadgePath && typeof window !== "undefined"
      ? `${window.location.origin}${publicBadgePath}`
      : publicBadgePath;

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distintivo Conformidad ENS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Resolviendo cert_id…
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !info) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distintivo Conformidad ENS</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error ?? "Distintivo no disponible para este proyecto."}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Distintivo Conformidad ENS
          {info.category ? (
            <Badge variant="outline">{info.category}</Badge>
          ) : null}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          CCN-STIC 809 · cert_id <code className="text-xs">{info.cert_id}</code>
          {info.issued_date ? <> · emitido {info.issued_date}</> : null}
          {info.expiry_date ? <> · vence {info.expiry_date}</> : null}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {publicBadgePath ? (
          <div className="flex items-center justify-center rounded-md border bg-muted/30 p-6">
            <img
              src={publicBadgePath}
              alt="Distintivo Conformidad ENS"
              className="max-h-32"
            />
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleGenerateDeclaration} disabled={generating}>
            {generating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generando…
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Descargar Declaración (DOCX)
              </>
            )}
          </Button>
          {publicBadgePath ? (
            <>
              <Button variant="outline" onClick={handleDownloadSvg}>
                <Download className="mr-2 h-4 w-4" />
                Descargar SVG
              </Button>
              <Button variant="outline" onClick={handleCopyEmbed}>
                <Copy className="mr-2 h-4 w-4" />
                Copiar snippet HTML
              </Button>
              <Button variant="ghost" onClick={handleOpenPublic}>
                <ExternalLink className="mr-2 h-4 w-4" />
                Vista pública
              </Button>
            </>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
