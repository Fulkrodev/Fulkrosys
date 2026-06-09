"use client";

/**
 * EvidenciasUploadPage · cliente file uploader (ADR-038 SAN-D MB-14.7).
 *
 * Coherencia visual: shadcn Card + Button · fulkro palette · lucide.
 * Audit: backend registra EVIDENCE_UPLOAD action hash chain via
 * AuditLogService.
 *
 * MB-6 atom 6 · UX feedback antivirus scan (ENS mp.s.5):
 *  - Post-upload toast: "Escaneando antivirus..." (Q3 B async pattern)
 *  - Drop-in: ScanStatusBadge + useEvidenceScanPolling reusable cross-portal
 */
import { CheckCircle2, Loader2, ShieldCheck, Upload, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".doc",
  ".xlsx",
  ".xls",
  ".png",
  ".jpg",
  ".jpeg",
  ".txt",
  ".csv",
  ".zip",
];

const MAX_SIZE_MB = 50;

export function EvidenciasUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (description) formData.append("description", description);

      // Get CSRF token (clientApi pattern)
      const { getCsrfToken } = await import("@/lib/csrf");
      const csrf = getCsrfToken();
      const headers: HeadersInit = {};
      if (csrf) headers["X-CSRF-Token"] = csrf;

      const res = await fetch(
        "/api/v1/client-portal/evidencias/upload",
        {
          method: "POST",
          credentials: "include",
          headers,
          body: formData,
        },
      );

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Upload fallo: ${res.status} ${detail}`);
      }

      setSuccess(true);
      setFile(null);
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error upload");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Subir evidencia</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Formatos aceptados: {ALLOWED_EXTENSIONS.join(", ")}. Máximo{" "}
            {MAX_SIZE_MB} MB. Cada subida queda registrada en audit log
            cifrado.
          </p>

          <input
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setSuccess(false);
              setError(null);
            }}
            disabled={uploading}
            className="block w-full text-sm"
          />

          {file && (
            <div className="flex items-center gap-2 rounded-md bg-muted p-2 text-sm">
              <span className="flex-1 truncate">{file.name}</span>
              <span className="text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setFile(null)}
                disabled={uploading}
              >
                <X className="h-3 w-3" strokeWidth={2.3} />
              </Button>
            </div>
          )}

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Descripción (opcional · ej. medida ENS relacionada)..."
            rows={3}
            className="w-full rounded border bg-card p-2 text-sm"
            disabled={uploading}
          />

          <Button
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Subiendo...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" strokeWidth={2.3} />
                Subir evidencia
              </>
            )}
          </Button>

          {success && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 rounded-md bg-fulkro-success/10 p-2 text-sm text-fulkro-success">
                <CheckCircle2 className="h-4 w-4" strokeWidth={2.3} />
                Evidencia subida y registrada en audit log.
              </div>
              <div className="flex items-center gap-2 rounded-md bg-fulkro-info/10 p-2 text-xs text-fulkro-info">
                <ShieldCheck className="h-4 w-4 flex-shrink-0" strokeWidth={2.3} />
                <span>
                  Análisis antivirus iniciado (ClamAV · ENS mp.s.5). Si el
                  archivo presenta amenazas, quedará en cuarentena hasta
                  revisión.
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-md bg-fulkro-danger/10 p-2 text-sm text-fulkro-danger">
              {error}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
