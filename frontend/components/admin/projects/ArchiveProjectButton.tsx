"use client";

/**
 * ArchiveProjectButton · sub-atom 1.E.2.bis Phase A.
 *
 * Soft delete (archive) project · ENAC traceability sostained.
 * Name-match confirmation evita archive accidental.
 *
 * Si project archivado == activeProject · clearActiveProject post-archive.
 * Refresh clients query · ProjectsPage re-renders sin proyecto archivado
 * en grid principal.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Archive, Loader2, X } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { archiveClientProject } from "@/lib/admin-clients/api";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

interface Props {
  projectId: string;
  projectName: string;
  clientId: string;
  /** Compact variant para project cards en grid · default outline button. */
  variant?: "compact" | "default";
}

export function ArchiveProjectButton({
  projectId,
  projectName,
  clientId,
  variant = "default",
}: Props) {
  const queryClient = useQueryClient();
  const activeProject = useActiveProjectStore((s) => s.activeProject);
  const clearActiveProject = useActiveProjectStore((s) => s.clearActiveProject);

  const [open, setOpen] = React.useState(false);
  const [confirmName, setConfirmName] = React.useState("");

  const mutation = useMutation({
    mutationFn: async () => archiveClientProject(clientId, projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["clients"] });
      if (activeProject?.id === projectId) {
        clearActiveProject();
      }
      toast.success(`Proyecto "${projectName}" archivado`);
      setOpen(false);
      setConfirmName("");
    },
    onError: (err: Error) => {
      toast.error(`No se pudo archivar: ${err.message}`);
    },
  });

  const nameMatches = confirmName.trim() === projectName.trim();

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setConfirmName("");
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size={variant === "compact" ? "sm" : "md"}
          aria-label={`Archivar proyecto ${projectName}`}
          onClick={(e) => e.stopPropagation()}
          data-testid={`archive-project-trigger-${projectId}`}
        >
          <Archive size={12} />
          {variant === "default" ? "Archivar" : ""}
        </Button>
      </DialogTrigger>
      <DialogContent
        className="sm:max-w-md"
        onClick={(e) => e.stopPropagation()}
        data-testid={`archive-project-modal-${projectId}`}
      >
        <DialogHeader>
          <DialogTitle>Archivar proyecto</DialogTitle>
          <DialogDescription>
            Vas a archivar el proyecto{" "}
            <span className="font-semibold">{projectName}</span>. Quedará
            registrado en el audit log y podrá restaurarse desde el panel
            de operaciones. Para confirmar, escribe el nombre exacto.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor={`confirm-${projectId}`} className="text-sm">
            Escribe el nombre del proyecto
          </Label>
          <Input
            id={`confirm-${projectId}`}
            type="text"
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            placeholder={projectName}
            disabled={mutation.isPending}
            data-testid={`archive-project-confirm-input-${projectId}`}
          />
        </div>
        <DialogFooter className="gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={mutation.isPending}
          >
            <X size={13} />
            Cancelar
          </Button>
          <Button
            type="button"
            variant="danger"
            disabled={!nameMatches || mutation.isPending}
            onClick={() => mutation.mutate()}
            data-testid={`archive-project-submit-${projectId}`}
          >
            {mutation.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Archive size={13} />
            )}
            Archivar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
