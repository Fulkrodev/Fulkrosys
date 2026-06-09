/**
 * FolderCreateModal · 1.C.G.A v3.10 · admin create custom subfolder.
 *
 * Reuse endpoint existing POST /api/v1/idms/projects/{id}/idms/folders.
 * Parent selector limita a 15 carpetas estándar (NO custom under custom · simplicidad).
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Loader2 } from "lucide-react";
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
import { idmsApi, type IdmsFolderNode } from "@/lib/api/idms";

interface FolderCreateModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  folders: IdmsFolderNode[];
}

export function FolderCreateModal({
  projectId,
  open,
  onOpenChange,
  folders,
}: FolderCreateModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = React.useState("");
  const [parentFolderId, setParentFolderId] = React.useState<string>("");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setName("");
      setParentFolderId("");
      setError(null);
    }
  }, [open]);

  const createMutation = useMutation({
    mutationFn: () =>
      idmsApi.createFolder(projectId, {
        name: name.trim(),
        parent_folder_id: parentFolderId || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["idms", "folder-tree", projectId] });
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Error al crear carpeta");
    },
  });

  const standardParents = folders.filter((f) => f.is_standard);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderPlus size={16} />
            Crear subcarpeta
          </DialogTitle>
          <DialogDescription>
            Crea subcarpeta dentro de una de las 15 estándar K.0..K.6+retainer.
            Las 15 estándar son canónicas · NO se modifican.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label htmlFor="folder-name">Nombre</Label>
            <Input
              id="folder-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Anexos Q1 2026"
              disabled={createMutation.isPending}
            />
          </div>

          <div>
            <Label htmlFor="parent-folder">Carpeta padre</Label>
            <Select value={parentFolderId} onValueChange={setParentFolderId}>
              <SelectTrigger id="parent-folder">
                <SelectValue placeholder="Selecciona padre (estándar)" />
              </SelectTrigger>
              <SelectContent>
                {standardParents.map((f) => (
                  <SelectItem key={f.id} value={f.id}>
                    {f.name}
                    {f.standard_code ? ` (K.${f.standard_code})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error ? (
            <Alert variant="danger">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={createMutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={
              !name.trim() || !parentFolderId || createMutation.isPending
            }
          >
            {createMutation.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Creando…
              </>
            ) : (
              <>
                <FolderPlus size={14} />
                Crear
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
