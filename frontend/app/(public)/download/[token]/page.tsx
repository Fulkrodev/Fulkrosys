/**
 * /download/[token] · Dispatcher de descargas magic-link.
 *
 * 3 purposes soportados (M25 public_api dispatcher):
 *   - descarga_backup_archivo            (M25 archived backup ZIP) · activo
 *   - descarga_certificado_conformidad   (M27 cert)                · 501 stub
 *   - descarga_dossier_final             (M09 dossier)             · 501 stub
 *
 * Backend: GET /api/v1/public/download/{token} (metadata) +
 *          GET /api/v1/public/download/{token}/file (stream)
 *
 * Antes era TokenScaffold 18 LOC con expectedPurpose mismatch · ahora
 * dispatcher real consume m25/public_api endpoints.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileArchive, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMagicLinkStatus } from "@/hooks/magic-link";
import {
  type DownloadMetadata,
  getDownloadMetadata,
  downloadFileUrl,
} from "@/lib/api/public-portals";
import {
  isMagicLinkActive,
  type MagicLinkBackendPurpose,
} from "@/lib/magic-link-types";

const ALLOWED_PURPOSES: ReadonlySet<MagicLinkBackendPurpose> = new Set<MagicLinkBackendPurpose>([
  "descarga_backup_archivo",
  "descarga_certificado_conformidad",
  "descarga_dossier_final",
]);

export default function DownloadTokenPage({
  params,
}: {
  params: { token: string };
}) {
  const token = params.token;
  const status = useMagicLinkStatus(token);

  const meta = useQuery<DownloadMetadata>({
    queryKey: ["public-portal", "download-metadata", token],
    queryFn: () => getDownloadMetadata(token),
    enabled:
      Boolean(token) &&
      Boolean(status.data) &&
      ALLOWED_PURPOSES.has(status.data!.tipo_operacion),
    staleTime: 30_000,
    retry: false,
  });

  if (status.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> validando enlace…
        </CardContent>
      </Card>
    );
  }

  if (status.isError || !status.data) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="warning">
            <AlertTitle>Enlace no disponible</AlertTitle>
            <AlertDescription>
              Este enlace no es válido o ha caducado. Solicite uno nuevo a su
              responsable del proyecto.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!ALLOWED_PURPOSES.has(status.data.tipo_operacion)) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="info">
            <AlertTitle>Enlace de otra funcionalidad</AlertTitle>
            <AlertDescription>
              Este enlace corresponde a una operación distinta de la
              descarga.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!isMagicLinkActive(status.data)) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="warning">
            <AlertTitle>Enlace caducado o agotado</AlertTitle>
            <AlertDescription>
              Este enlace ya no permite descarga. Solicite uno nuevo a su
              responsable del proyecto.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (meta.isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> resolviendo descarga…
        </CardContent>
      </Card>
    );
  }

  if (meta.isError || !meta.data) {
    const message =
      meta.error instanceof Error ? meta.error.message : null;
    const isNotImplemented = message?.includes("pendiente de integracion");
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant={isNotImplemented ? "info" : "danger"}>
            <AlertTitle>
              {isNotImplemented
                ? "Descarga aún no disponible"
                : "No se pudo preparar la descarga"}
            </AlertTitle>
            <AlertDescription>
              {message ??
                "Reintente en unos minutos. Si persiste, contacte con su responsable del proyecto."}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return <DownloadView token={token} data={meta.data} />;
}

const TITLE_BY_PURPOSE: Record<string, string> = {
  descarga_backup_archivo: "Backup del proyecto cerrado",
  descarga_certificado_conformidad: "Certificado de conformidad ENS",
  descarga_dossier_final: "Dossier final de auditoría",
};

function DownloadView({
  token,
  data,
}: {
  token: string;
  data: DownloadMetadata;
}) {
  const title = TITLE_BY_PURPOSE[data.purpose] ?? "Descarga segura";

  function formatSize(bytes: number | null): string | null {
    if (!bytes) return null;
    const mb = bytes / (1024 * 1024);
    return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;
  }

  const sizeLabel = formatSize(data.size_bytes);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileArchive size={16} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5 rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-50 p-3 text-xs">
          <p className="font-mono text-fulkro-ink-700">{data.filename}</p>
          <div className="grid grid-cols-2 gap-y-1 text-fulkro-ink-500">
            <span>Tipo</span>
            <span className="font-mono">{data.content_type}</span>
            {sizeLabel ? (
              <>
                <span>Tamaño</span>
                <span className="font-mono">{sizeLabel}</span>
              </>
            ) : null}
            {data.expires_at ? (
              <>
                <span>Disponible hasta</span>
                <span>{new Date(data.expires_at).toLocaleDateString()}</span>
              </>
            ) : null}
            {data.sha256 ? (
              <>
                <span>SHA-256</span>
                <span
                  className="truncate font-mono text-[10px]"
                  title={data.sha256}
                >
                  {data.sha256.slice(0, 24)}…
                </span>
              </>
            ) : null}
          </div>
        </div>

        <a
          href={downloadFileUrl(token)}
          download
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-fulkro-primary-700 px-4 py-3 text-sm font-medium text-white hover:bg-fulkro-primary-700/90"
        >
          <Download size={16} /> Descargar archivo
        </a>

        <p className="text-[11px] text-fulkro-ink-500">
          La descarga queda registrada en el log de auditoría con su IP y
          timestamp.
        </p>

        {data.ed25519_signature ? (
          <div className="rounded-md bg-white p-2 font-mono text-[10px] text-fulkro-ink-500">
            <p className="font-medium">Firma Ed25519</p>
            <p className="break-all">{data.ed25519_signature}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

