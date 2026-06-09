"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

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
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/api";
import {
  updateDepartment,
  type Department,
} from "@/lib/api/departments";

import { DepartmentContactsList } from "./DepartmentContactsList";

type Props = {
  projectId: string;
  department: Department | null;
  onClose: () => void;
  onSaved: () => void;
};

export function DepartmentEditModal({
  projectId,
  department,
  onClose,
  onSaved,
}: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (department) {
      setName(department.name);
      setDescription(department.description ?? "");
    }
  }, [department]);

  const submit = async () => {
    if (!department) return;
    if (!name.trim()) {
      toast.error("Nombre obligatorio");
      return;
    }
    setSubmitting(true);
    try {
      await updateDepartment(projectId, department.id, {
        name: name.trim(),
        description: description.trim() || null,
      });
      toast.success("Área actualizada");
      onSaved();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error actualizando área";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={department !== null}
      onOpenChange={(next) => {
        if (!next && !submitting) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar área {department?.code}</DialogTitle>
          <DialogDescription>
            El código no se puede cambiar (se usa como referencia estable).
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <Label htmlFor="dept_edit_name">Nombre *</Label>
            <Input
              id="dept_edit_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
            />
          </div>
          <div>
            <Label htmlFor="dept_edit_desc">Descripción</Label>
            <Textarea
              id="dept_edit_desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          {department ? (
            <div className="flex flex-col gap-2">
              <Label>Empleados asignados</Label>
              <DepartmentContactsList
                projectId={projectId}
                departmentId={department.id}
              />
              <p className="text-xs text-[color:var(--fulkro-muted)]">
                Para asignar empleados, ve a la pestaña Empleados y usa el
                selector de área en cada fila.
              </p>
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button onClick={() => void submit()} disabled={submitting}>
            {submitting ? "Guardando…" : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
