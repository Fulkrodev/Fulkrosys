"use client";

import { useState } from "react";
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
import { createDepartment } from "@/lib/api/departments";

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
};

export function DepartmentCreateModal({
  projectId,
  open,
  onOpenChange,
  onCreated,
}: Props) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reset = () => {
    setCode("");
    setName("");
    setDescription("");
  };

  const handleClose = (next: boolean) => {
    if (!next && !submitting) reset();
    onOpenChange(next);
  };

  const submit = async () => {
    if (!code.trim() || !name.trim()) {
      toast.error("Código y nombre obligatorios");
      return;
    }
    setSubmitting(true);
    try {
      await createDepartment(projectId, {
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
      });
      toast.success("Área creada");
      onCreated();
      handleClose(false);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error creando área";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nueva área</DialogTitle>
          <DialogDescription>
            Departamento/área del proyecto cliente. El código debe ser único
            dentro del proyecto (e.g. TI, COMPLIANCE, LEGAL).
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <Label htmlFor="dept_code">Código *</Label>
            <Input
              id="dept_code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="TI"
              maxLength={50}
            />
          </div>
          <div>
            <Label htmlFor="dept_name">Nombre *</Label>
            <Input
              id="dept_name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tecnologías de la Información"
              maxLength={200}
            />
          </div>
          <div>
            <Label htmlFor="dept_desc">Descripción</Label>
            <Textarea
              id="dept_desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Responsabilidades, alcance, observaciones…"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button onClick={() => void submit()} disabled={submitting}>
            {submitting ? "Creando…" : "Crear"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
