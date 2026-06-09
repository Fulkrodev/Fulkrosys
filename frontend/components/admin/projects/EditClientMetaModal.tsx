"use client";

/**
 * EditClientMetaModal · sub-atom Sesión 3B-1 Phase A.2.
 *
 * Inline edit modal for client metadata visible en selector cards:
 *   - nombre (company name · shown as primary card title)
 *   - sector (filter chip · informational)
 *
 * Reuses existing backend endpoint PATCH /api/v1/clients/{id}
 * (`admin-clients/api.ts` updateClient).
 *
 * Cliente piloto MEDIA assumption: 1 client ≈ 1 project · editing client
 * metadata effectively edits the visible project entry in selector.
 *
 * Multi-project per cliente Future-1.E.2.bis.multi-project: scope would
 * expand to project-level metadata edit (separate PATCH endpoint NEW).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil } from "lucide-react";
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
import {
  updateClient,
  type ClientUpdate,
} from "@/lib/admin-clients/api";

interface EditClientMetaModalProps {
  clientId: string;
  currentName: string;
  currentSector?: string | null;
  /** Optional trigger className override. */
  triggerClassName?: string;
}

export function EditClientMetaModal({
  clientId,
  currentName,
  currentSector,
  triggerClassName,
}: EditClientMetaModalProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [nombre, setNombre] = React.useState(currentName);
  const [sector, setSector] = React.useState(currentSector ?? "");

  // Reset form on open · sync with current values
  React.useEffect(() => {
    if (open) {
      setNombre(currentName);
      setSector(currentSector ?? "");
    }
  }, [open, currentName, currentSector]);

  const mutation = useMutation({
    mutationFn: async (payload: ClientUpdate) => updateClient(clientId, payload),
    onSuccess: () => {
      toast.success("Datos del cliente actualizados");
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setOpen(false);
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "No se pudo actualizar";
      toast.error(`Error al actualizar · ${msg}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) {
      toast.error("El nombre no puede estar vacío");
      return;
    }
    const payload: ClientUpdate = {};
    if (nombre.trim() !== currentName) payload.nombre = nombre.trim();
    if ((sector || null) !== (currentSector ?? null)) {
      payload.sector = sector.trim() || null;
    }
    if (Object.keys(payload).length === 0) {
      toast.info("Sin cambios que guardar");
      setOpen(false);
      return;
    }
    mutation.mutate(payload);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`Editar ${currentName}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          className={
            triggerClassName ??
            "inline-flex items-center gap-1 rounded-md border border-fulkro-ink-300 bg-white px-2 py-1 text-xs font-medium text-fulkro-ink-700 hover:bg-fulkro-ink-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-info focus-visible:ring-offset-2"
          }
          data-testid={`edit-client-trigger-${clientId}`}
        >
          <Pencil size={12} />
          Editar
        </button>
      </DialogTrigger>

      <DialogContent
        onClick={(e) => e.stopPropagation()}
        data-testid={`edit-client-modal-${clientId}`}
      >
        <DialogHeader>
          <DialogTitle>Editar datos del cliente</DialogTitle>
          <DialogDescription>
            Cambios en nombre y sector se reflejan en el listado y en el portal del cliente.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label htmlFor={`edit-nombre-${clientId}`}>Nombre del cliente</Label>
            <Input
              id={`edit-nombre-${clientId}`}
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              required
              maxLength={200}
              data-testid={`edit-client-name-${clientId}`}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={`edit-sector-${clientId}`}>
              Sector <span className="text-xs text-fulkro-ink-500">(opcional)</span>
            </Label>
            <Input
              id={`edit-sector-${clientId}`}
              type="text"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              placeholder="sanidad · finanzas · aapp · educacion · …"
              maxLength={100}
              data-testid={`edit-client-sector-${clientId}`}
            />
          </div>

          <DialogFooter className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setOpen(false)}
              disabled={mutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={mutation.isPending}
              data-testid={`edit-client-submit-${clientId}`}
            >
              {mutation.isPending ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Guardando…
                </>
              ) : (
                "Guardar cambios"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
