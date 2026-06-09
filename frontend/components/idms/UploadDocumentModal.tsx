/**
 * UploadDocumentModal · 1.C.G.A v3.10 · admin drag-drop file upload.
 *
 * Reuse endpoint existing POST /api/v1/idms/projects/{id}/idms/intake.
 * Conversión file → base64 client-side (consistente con pattern m24 existing).
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Upload } from "lucide-react";
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
import { idmsApi, type IdmsFolderNode } from "@/lib/api/idms";

const CLASIFICACIONES = [
  { value: "politica", label: "Política" },
  { value: "procedimiento", label: "Procedimiento" },
  { value: "registro", label: "Registro" },
  { value: "evidencia", label: "Evidencia" },
  { value: "informe", label: "Informe" },
  { value: "contrato", label: "Contrato" },
  { value: "otro", label: "Otro" },
] as const;

interface UploadDocumentModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folders: IdmsFolderNode[];
  defaultFolderId?: string | null;
}

export function UploadDocumentModal({
  projectId,
  open,
  onOpenChange,
  folders,
  defaultFolderId,
}: UploadDocumentModalProps) {
  const queryClient = useQueryClient();
  const [file, setFile] = React.useState<File | null>(null);
  const [folderId, setFolderId] = React.useState<string>(defaultFolderId ?? "");
  const [clasificacion, setClasificacion] = React.useState<string>("otro");
  const [tagsRaw, setTagsRaw] = React.useState<string>("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setFile(null);
      setFolderId(defaultFolderId ?? "");
      setClasificacion("otro");
      setTagsRaw("");
      setError(null);
    }
  }, [open, defaultFolderId]);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Selecciona un archivo");
      const buf = await file.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(buf).reduce(
          (acc, byte) => acc + String.fromCharCode(byte),
          "",
        ),
      );
      const tags = tagsRaw
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean)
        .map((value) => ({
          type: "measure_ens",
          value,
          source: "manual",
          confidence: 1.0,
        }));
      return idmsApi.intake(projectId, {
        nombre: file.name,
        contenido_base64: base64,
        tipo_mime: file.type || "application/octet-stream",
        folder_id: folderId || undefined,
        clasificacion,
        tags: tags.length > 0 ? tags : undefined,
        subido_por: "marcos",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["idms"] });
      queryClient.invalidateQueries({ queryKey: ["m24", "idms-documents", projectId] });
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Error al subir");
    },
  });

  const flatFolders = React.useMemo(() => {
    const out: { id: string; label: string }[] = [];
    function walk(nodes: IdmsFolderNode[], depth: number) {
      nodes.forEach((n) => {
        out.push({
          id: n.id,
          label: `${"  ".repeat(depth)}${n.name}${n.standard_code ? ` (K.${n.standard_code})` : ""}`,
        });
        if (n.children) walk(n.children, depth + 1);
      });
    }
    walk(folders, 0);
    return out;
  }, [folders]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Subir documento</DialogTitle>
          <DialogDescription>
            Carga un nuevo documento al gestor documental IDMS del proyecto.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label htmlFor="file">Archivo</Label>
            <Input
              id="file"
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={upload.isPending}
            />
            {file ? (
              <p className="mt-1 text-xs text-fulkro-ink-500">
                {file.name} · {(file.size / 1024).toFixed(1)} KB · {file.type || "binario"}
              </p>
            ) : null}
          </div>

          <div>
            <Label htmlFor="folder">Carpeta destino</Label>
            <Select value={folderId} onValueChange={setFolderId}>
              <SelectTrigger id="folder">
                <SelectValue placeholder="Selecciona carpeta (opcional)" />
              </SelectTrigger>
              <SelectContent>
                {flatFolders.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="clasificacion">Clasificación</Label>
            <Select value={clasificacion} onValueChange={setClasificacion}>
              <SelectTrigger id="clasificacion">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CLASIFICACIONES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="tags">Medidas ENS (separadas por comas)</Label>
            <Textarea
              id="tags"
              value={tagsRaw}
              onChange={(e) => setTagsRaw(e.target.value)}
              placeholder="op.acc.1, op.exp.5, mp.com.4"
              rows={2}
              disabled={upload.isPending}
            />
            <p className="mt-1 text-xs text-fulkro-ink-500">
              Códigos Anexo II opcionales · taxonomía oficial RD 311/2022
            </p>
          </div>

          {error ? (
            <Alert variant="danger">
              <AlertTitle>Error al subir</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={upload.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={() => upload.mutate()}
            disabled={!file || upload.isPending}
          >
            {upload.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Subiendo…
              </>
            ) : (
              <>
                <Upload size={14} />
                Subir documento
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
