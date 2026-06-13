"use client";

/**
 * ProjectContactCreateModal · sub-atom 1.C.F.1.
 *
 * Modal compacto de creacion contact project-scoped · reuse schemas m30
 * y endpoint POST /api/v1/projects/{id}/contacts. Distinct del wizard
 * client-scoped existing (ContactCreateWizard 3-step). Aqui 1-step para
 * empleados rapidos (sin portal_access · sin signatory toggle por defecto).
 */
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { ApiError } from "@/lib/api";
import { createProjectContact } from "@/lib/api/project-contacts";
import {
  ROLE_CATEGORIES,
  ROLE_CATEGORY_LABELS,
  type RoleCategory,
} from "@/lib/admin-contacts/schemas";

type Props = {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
  defaultHasPortalAccess?: boolean;
};

export function ProjectContactCreateModal({
  projectId,
  open,
  onOpenChange,
  onCreated,
  defaultHasPortalAccess = false,
}: Props) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [roleCategory, setRoleCategory] = useState<RoleCategory>("operaciones");
  const [submitting, setSubmitting] = useState(false);

  const reset = () => {
    setFullName("");
    setEmail("");
    setPhone("");
    setRoleTitle("");
    setRoleCategory("operaciones");
  };

  const handleClose = (next: boolean) => {
    if (!next && !submitting) reset();
    onOpenChange(next);
  };

  const submit = async () => {
    if (!fullName.trim() || !email.trim() || !roleTitle.trim()) {
      toast.error("Nombre, email y cargo obligatorios");
      return;
    }
    setSubmitting(true);
    try {
      await createProjectContact(projectId, {
        full_name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        role_title: roleTitle.trim(),
        role_category: roleCategory,
        has_portal_access: defaultHasPortalAccess,
      });
      toast.success("Contacto creado");
      onCreated();
      handleClose(false);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error creando contacto";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {defaultHasPortalAccess ? "Nuevo usuario portal" : "Nuevo empleado"}
          </DialogTitle>
          <DialogDescription>
            Contacto scoped al proyecto. {defaultHasPortalAccess
              ? "Usa el panel superior para usuario portal con ClientUser activo."
              : "Empleado interno · sin acceso al portal cliente."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <Label htmlFor="pc_full_name">Nombre completo *</Label>
            <Input
              id="pc_full_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="pc_email">Email *</Label>
              <Input
                id="pc_email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="pc_phone">Teléfono</Label>
              <Input
                id="pc_phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <Label htmlFor="pc_role_title">Cargo *</Label>
              <Input
                id="pc_role_title"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                placeholder="Ej. Técnico de sistemas"
              />
            </div>
            <div>
              <Label htmlFor="pc_role_category">Categoría *</Label>
              <Select
                value={roleCategory}
                onValueChange={(v) => setRoleCategory(v as RoleCategory)}
              >
                <SelectTrigger id="pc_role_category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {ROLE_CATEGORY_LABELS[c]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
