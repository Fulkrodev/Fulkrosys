"use client";

/**
 * CreateProjectModal · sub-atom 1.E.2.bis Phase A.
 *
 * Modal greenfield para crear proyecto desde selector landing
 * (/admin/projects). Reusa endpoints existing:
 *   - GET /api/v1/clients · cliente combobox
 *   - POST /api/v1/clients/{client_id}/projects · create
 *
 * Post-success: setActiveProject(new) + redirect a project dashboard.
 *
 * Categorización ENS: 4 options (BASICA · MEDIA · ALTA · sin definir).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, X } from "lucide-react";
import { useRouter } from "next/navigation";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useClients } from "@/hooks/useClients";
import {
  createClientProject,
  type ProjectCreateBody,
} from "@/lib/admin-clients/api";
import { ROUTES } from "@/lib/constants";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";
import type { EnsCategory } from "@/lib/stores/active-project-store";

type CategoryOption = EnsCategory | "";

export function CreateProjectModal() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const setActiveProject = useActiveProjectStore((s) => s.setActiveProject);
  const { data: clients = [], isLoading: clientsLoading } = useClients();

  const [open, setOpen] = React.useState(false);
  const [clientId, setClientId] = React.useState("");
  const [nombre, setNombre] = React.useState("");
  const [category, setCategory] = React.useState<CategoryOption>("");

  const reset = React.useCallback(() => {
    setClientId("");
    setNombre("");
    setCategory("");
  }, []);

  const mutation = useMutation({
    mutationFn: async () => {
      const body: ProjectCreateBody = {
        nombre: nombre.trim(),
        categoria_objetivo: category === "" ? null : category,
      };
      return createClientProject(clientId, body);
    },
    onSuccess: async (project) => {
      const client = clients.find((c) => c.id === clientId);
      setActiveProject({
        id: project.id,
        name: project.nombre,
        clientId: project.client_id,
        clientName: client?.nombre ?? "",
        ensCategory: (project.categoria_objetivo as EnsCategory | null) ?? null,
        status: project.lifecycle_state ?? project.fase ?? "draft",
        lastAccessedAt: Date.now(),
      });
      await queryClient.invalidateQueries({ queryKey: ["clients"] });
      toast.success(`Proyecto "${project.nombre}" creado`);
      setOpen(false);
      reset();
      router.push(`${ROUTES.projects}/${project.id}`);
    },
    onError: (err: Error) => {
      toast.error(`No se pudo crear el proyecto: ${err.message}`);
    },
  });

  const canSubmit =
    !!clientId && nombre.trim().length >= 1 && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    mutation.mutate();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button
          variant="primary"
          size="md"
          data-testid="create-project-trigger"
        >
          <Plus size={14} />
          Nuevo proyecto
        </Button>
      </DialogTrigger>
      <DialogContent
        className="sm:max-w-md"
        data-testid="create-project-modal"
      >
        <DialogHeader>
          <DialogTitle>Crear proyecto nuevo</DialogTitle>
          <DialogDescription>
            Selecciona el cliente y los datos básicos del proyecto. La
            categoría ENS se puede ajustar después en Personalización.
            {" "}Para un cliente que <strong>todavía no existe</strong>, usa
            «Alta de cliente nuevo»: ese asistente crea cliente y proyecto
            juntos, con su análisis de riesgos inicial.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4"
          data-testid="create-project-form"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cp-client">Cliente</Label>
            <Select
              value={clientId}
              onValueChange={setClientId}
              disabled={clientsLoading || mutation.isPending}
            >
              <SelectTrigger
                id="cp-client"
                data-testid="create-project-client-select"
              >
                <SelectValue placeholder="Selecciona cliente…" />
              </SelectTrigger>
              <SelectContent>
                {clients.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.nombre}
                    {c.cif ? ` · ${c.cif}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cp-name">Nombre del proyecto</Label>
            <Input
              id="cp-name"
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="ENS Implantación · Cliente X"
              disabled={mutation.isPending}
              data-testid="create-project-name-input"
              maxLength={255}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="cp-category">Categoría ENS (opcional)</Label>
            <Select
              value={category}
              onValueChange={(v) => setCategory(v as CategoryOption)}
              disabled={mutation.isPending}
            >
              <SelectTrigger
                id="cp-category"
                data-testid="create-project-category-select"
              >
                <SelectValue placeholder="Definir después" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BASICA">BÁSICA</SelectItem>
                <SelectItem value="MEDIA">MEDIA</SelectItem>
                <SelectItem value="ALTA">ALTA</SelectItem>
              </SelectContent>
            </Select>
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
              type="submit"
              variant="primary"
              disabled={!canSubmit}
              data-testid="create-project-submit"
            >
              {mutation.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Plus size={13} />
              )}
              Crear
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
