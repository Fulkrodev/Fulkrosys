/**
 * ClientUploadModal · 1.C.G.B v3.10 · cliente upload documento permission-limited.
 *
 * Diferencias vs admin UploadDocumentModal (1.C.G.A):
 * - NO tags ENS (admin gestiona taxonomía Anexo II · R30 inverso)
 * - NO clasificacion B/M/A selector (admin asigna · cliente NO ve admin enum)
 * - SÍ description simple opcional ("Adjunto: certificado ISO 27001")
 * - SÍ folder selector friendly (sin códigos K.XX visibles · solo nombres)
 * - Tono warm + amable · R29 sostener (NO presión coercitiva)
 * - Mensaje success amable: "Subido · Marcos lo revisará pronto"
 */
"use client";

import { CheckCircle2, Loader2, Upload } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  uploadClientDocument,
  type ClientFolderNode,
} from "@/lib/api/files-extended";
import { ClientApiError } from "@/lib/client-portal-api";

interface ClientUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folders: ClientFolderNode[];
  defaultFolderId?: string | null;
  onUploaded?: () => void;
}

export function ClientUploadModal({
  open,
  onOpenChange,
  folders,
  defaultFolderId,
  onUploaded,
}: ClientUploadModalProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [folderId, setFolderId] = React.useState<string>(defaultFolderId ?? "");
  const [descripcion, setDescripcion] = React.useState<string>("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setFile(null);
      setFolderId(defaultFolderId ?? "");
      setDescripcion("");
      setError(null);
      setSuccess(false);
    }
  }, [open, defaultFolderId]);

  async function handleUpload() {
    if (!file) {
      setError("Selecciona un archivo");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const buf = await file.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(buf).reduce(
          (acc, byte) => acc + String.fromCharCode(byte),
          "",
        ),
      );
      await uploadClientDocument({
        nombre: file.name,
        contenido_base64: base64,
        tipo_mime: file.type || "application/octet-stream",
        folder_id: folderId || undefined,
        descripcion: descripcion.trim() || undefined,
      });
      setSuccess(true);
      onUploaded?.();
      // Cierre diferido para mostrar success
      setTimeout(() => onOpenChange(false), 1200);
    } catch (err) {
      if (err instanceof ClientApiError) setError(err.message);
      else if (err instanceof Error) setError(err.message);
      else setError("No se pudo subir el documento");
    } finally {
      setSubmitting(false);
    }
  }

  // Folders flat friendly · solo nombres (sin códigos K.XX técnicos)
  const flatFolders = React.useMemo(() => {
    const out: { id: string; label: string }[] = [];
    function walk(nodes: ClientFolderNode[], depth: number) {
      nodes.forEach((n) => {
        out.push({
          id: n.id,
          label: `${"  ".repeat(depth)}${n.name}`,
        });
        if (n.children) walk(n.children, depth + 1);
      });
    }
    walk(folders, 0);
    return out;
  }, [folders]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload size={16} />
            Compartir un documento
          </DialogTitle>
          <DialogDescription>
            Sube archivos de tu organización: certificados, evidencias, capturas,
            ejemplos. Marcos los revisará y los integrará al expediente.
          </DialogDescription>
        </DialogHeader>

        {success ? (
          <Alert variant="success">
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>¡Listo!</AlertTitle>
            <AlertDescription>
              Subido correctamente. Marcos lo revisará pronto.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-3">
            <div>
              <Label htmlFor="client-file">Archivo</Label>
              <Input
                id="client-file"
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                disabled={submitting}
              />
              {file ? (
                <p className="mt-1 text-xs text-fulkro-ink-500">
                  {file.name} · {(file.size / 1024).toFixed(1)} KB
                </p>
              ) : null}
            </div>

            <div>
              <Label htmlFor="client-folder">Carpeta (opcional)</Label>
              <Select value={folderId} onValueChange={setFolderId}>
                <SelectTrigger id="client-folder">
                  <SelectValue placeholder="Sin carpeta · Marcos la organizará" />
                </SelectTrigger>
                <SelectContent>
                  {flatFolders.map((f) => (
                    <SelectItem key={f.id} value={f.id}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="mt-1 text-xs text-fulkro-ink-500">
                Si no estás seguro, déjalo vacío. Marcos lo guardará en su sitio.
              </p>
            </div>

            <div>
              <Label htmlFor="client-descripcion">Descripción (opcional)</Label>
              <Textarea
                id="client-descripcion"
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                placeholder='Ej. "Certificado ISO 27001 renovado en abril 2026"'
                rows={2}
                disabled={submitting}
              />
            </div>

            {error ? (
              <Alert variant="danger">
                <AlertTitle>No se pudo subir</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
          </div>
        )}

        {!success ? (
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!file || submitting}
            >
              {submitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Subiendo…
                </>
              ) : (
                <>
                  <Upload size={14} />
                  Subir
                </>
              )}
            </Button>
          </DialogFooter>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
