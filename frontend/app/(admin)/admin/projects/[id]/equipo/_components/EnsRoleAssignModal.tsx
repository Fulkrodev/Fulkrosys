"use client";

/**
 * EnsRoleAssignModal · sub-atom 1.C.F.4 v3.10.
 *
 * Modal admin para asignar un contact a un rol ENS_REQUIRED. Lista contacts
 * del proyecto + opción "Sin asignar" (vacate). Usa la matriz m30 existente:
 * 1 contact por rol · 1 rol por contact.
 *
 * Reusa endpoint PATCH/DELETE /admin/projects/{pid}/ens-required-roles/{role}.
 * NO valida segregación CCN-STIC 801 desde UI (delegado backend roles_ens.py
 * topology pre-firma · scope distinto).
 */
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/api";
import {
  assignContactToEnsRole,
  ENS_ROLE_DESCRIPTIONS_FRONTEND,
  ENS_ROLE_LABELS_FRONTEND,
  listProjectContacts,
  vacateEnsRole,
  type ProjectContact,
} from "@/lib/api/project-contacts";

const VACATE_VALUE = "__vacate__";

type Props = {
  projectId: string;
  role: string | null;
  currentContactId: string | null;
  onClose: () => void;
  onSaved: () => void;
};

export function EnsRoleAssignModal({
  projectId,
  role,
  currentContactId,
  onClose,
  onSaved,
}: Props) {
  const [contacts, setContacts] = useState<ProjectContact[]>([]);
  const [selectedContactId, setSelectedContactId] = useState<string>(
    currentContactId ?? VACATE_VALUE,
  );
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const open = role !== null;

  useEffect(() => {
    if (!open) return;
    setSelectedContactId(currentContactId ?? VACATE_VALUE);
    setNotes("");
    setLoading(true);
    listProjectContacts(projectId)
      .then((res) => setContacts(res.contacts.filter((c) => c.is_active)))
      .catch((err) => {
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando contactos";
        toast.error(msg);
      })
      .finally(() => setLoading(false));
  }, [open, projectId, currentContactId]);

  const submit = async () => {
    if (!role) return;
    setSubmitting(true);
    try {
      if (selectedContactId === VACATE_VALUE) {
        await vacateEnsRole(projectId, role);
        toast.success("Rol vacante");
      } else {
        await assignContactToEnsRole(
          projectId,
          role,
          selectedContactId,
          notes.trim() || null,
        );
        toast.success("Rol asignado");
      }
      onSaved();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error guardando asignación";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !submitting) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Asignar rol ENS{role ? ` · ${ENS_ROLE_LABELS_FRONTEND[role] ?? role}` : ""}
          </DialogTitle>
          <DialogDescription>
            {role
              ? ENS_ROLE_DESCRIPTIONS_FRONTEND[role] ?? "Rol RD 311/2022."
              : ""}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <Label htmlFor="ens_role_contact">Contacto</Label>
            <Select
              value={selectedContactId}
              onValueChange={setSelectedContactId}
              disabled={submitting || loading}
            >
              <SelectTrigger id="ens_role_contact">
                <SelectValue placeholder="Seleccionar contacto…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={VACATE_VALUE}>
                  <span className="text-fulkro-ink-500">
                    Sin asignar (vacate)
                  </span>
                </SelectItem>
                {contacts.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.full_name} · {c.role_title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedContactId !== VACATE_VALUE ? (
            <div>
              <Label htmlFor="ens_role_notes">Notas (opcional)</Label>
              <Textarea
                id="ens_role_notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Justificación / contexto del nombramiento"
                maxLength={2000}
              />
            </div>
          ) : null}

          {selectedContactId !== VACATE_VALUE && currentContactId ? (
            <p className="rounded-md border border-fulkro-warning/30 bg-fulkro-warning/10 px-3 py-2 text-xs text-fulkro-ink-700">
              Este rol ya tiene un contacto asignado. La nueva asignación
              reemplazará la actual (m30 mantiene 1 contact por rol).
            </p>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={() => void submit()} disabled={submitting || loading}>
            {submitting ? "Guardando…" : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
