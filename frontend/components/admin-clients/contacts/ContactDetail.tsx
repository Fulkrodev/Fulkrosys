"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/api";
import {
  activateContact,
  deactivateContact,
  deleteContact,
  getContact,
  getContactTimeline,
  updateContact,
} from "@/lib/admin-contacts/api";
import type {
  ClientContactOut,
  RoleCategory,
  TimelineEntryOut,
} from "@/lib/admin-contacts/schemas";
import {
  INTERACTION_TYPE_LABELS,
  ROLE_CATEGORIES,
  ROLE_CATEGORY_LABELS,
} from "@/lib/admin-contacts/schemas";

type Props = {
  clientId: string;
  contactId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged?: () => void;
};

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ContactDetail({
  clientId,
  contactId,
  open,
  onOpenChange,
  onChanged,
}: Props) {
  const [contact, setContact] = useState<ClientContactOut | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntryOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<Partial<ClientContactOut>>({});

  const loadAll = async (cid: string) => {
    setLoading(true);
    try {
      const [c, t] = await Promise.all([
        getContact(clientId, cid),
        getContactTimeline(clientId, cid, 50),
      ]);
      setContact(c);
      setForm({
        full_name: c.full_name,
        preferred_name: c.preferred_name,
        email: c.email,
        phone: c.phone,
        linkedin_url: c.linkedin_url,
        role_title: c.role_title,
        role_category: c.role_category,
        is_primary: c.is_primary,
        is_signatory: c.is_signatory,
        has_portal_access: c.has_portal_access,
        notes_marcos: c.notes_marcos,
      });
      setTimeline(t);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error cargando contacto";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open || !contactId) {
      setContact(null);
      setTimeline([]);
      setForm({});
      return;
    }
    void loadAll(contactId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, contactId, clientId]);

  const handleSave = async () => {
    if (!contact) return;
    setSaving(true);
    try {
      const updated = await updateContact(clientId, contact.id, {
        full_name: form.full_name ?? undefined,
        preferred_name: (form.preferred_name as string | null) ?? null,
        email: form.email ?? undefined,
        phone: (form.phone as string | null) ?? null,
        linkedin_url: (form.linkedin_url as string | null) ?? null,
        role_title: form.role_title ?? undefined,
        role_category: (form.role_category as RoleCategory) ?? undefined,
        is_primary: form.is_primary,
        is_signatory: form.is_signatory,
        has_portal_access: form.has_portal_access,
        notes_marcos: (form.notes_marcos as string | null) ?? null,
      });
      setContact(updated);
      toast.success("Contacto actualizado");
      onChanged?.();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error actualizando";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!contact) return;
    const reason = window.prompt(
      "Motivo de desactivación (mínimo 1 carácter):",
      "rotación",
    );
    if (!reason) return;
    try {
      const updated = await deactivateContact(
        clientId, contact.id, reason,
      );
      setContact(updated);
      toast.success("Contacto desactivado");
      onChanged?.();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error desactivando";
      toast.error(msg);
    }
  };

  const handleActivate = async () => {
    if (!contact) return;
    try {
      const updated = await activateContact(clientId, contact.id);
      setContact(updated);
      toast.success("Contacto reactivado");
      onChanged?.();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error activando";
      toast.error(msg);
    }
  };

  const handleDelete = async () => {
    if (!contact) return;
    if (
      !window.confirm(
        `Eliminar permanentemente "${contact.full_name}"?\n\n` +
          "Se borrará el contacto y TODAS sus interacciones (FK CASCADE).\n" +
          "Para conservar histórico usa Desactivar.",
      )
    ) {
      return;
    }
    try {
      await deleteContact(clientId, contact.id);
      toast.success("Contacto eliminado");
      onChanged?.();
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error eliminando";
      toast.error(msg);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full max-w-lg flex-col gap-0 overflow-y-auto bg-white sm:max-w-xl"
      >
        <SheetHeader className="space-y-2">
          <SheetTitle>
            {loading
              ? "Cargando…"
              : contact?.full_name ?? "Contacto"}
          </SheetTitle>
          <SheetDescription>
            {contact ? (
              <span className="flex flex-wrap items-center gap-2 text-xs">
                <span>{contact.role_title}</span>
                <Badge variant="outline">
                  {ROLE_CATEGORY_LABELS[
                    contact.role_category as RoleCategory
                  ] ?? contact.role_category}
                </Badge>
                {contact.is_primary ? <Badge>PRIMARY</Badge> : null}
                {contact.is_signatory ? (
                  <Badge variant="secondary">SIGNATORY</Badge>
                ) : null}
                {!contact.is_active ? (
                  <Badge variant="outline" className="text-fulkro-danger">
                    Inactivo
                  </Badge>
                ) : null}
              </span>
            ) : null}
          </SheetDescription>
        </SheetHeader>

        {loading ? (
          <div className="mt-6 space-y-3">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : !contact ? (
          <p className="mt-6 text-base font-medium text-[color:var(--fulkro-muted)]">
            Selecciona un contacto del listado.
          </p>
        ) : (
          <Tabs defaultValue="info" className="mt-4 flex-1">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="info">Información</TabsTrigger>
              <TabsTrigger value="timeline">
                Timeline ({contact.interactions_count})
              </TabsTrigger>
            </TabsList>

            {/* Tab Info */}
            <TabsContent value="info" className="mt-4 flex flex-col gap-3">
              <div>
                <Label htmlFor="d_full_name">Nombre completo</Label>
                <Input
                  id="d_full_name"
                  value={form.full_name ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, full_name: e.target.value }))
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="d_preferred">Nombre preferido</Label>
                  <Input
                    id="d_preferred"
                    value={form.preferred_name ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        preferred_name: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="d_role_title">Cargo</Label>
                  <Input
                    id="d_role_title"
                    value={form.role_title ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        role_title: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="d_email">Email</Label>
                <Input
                  id="d_email"
                  type="email"
                  value={form.email ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, email: e.target.value }))
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="d_phone">Teléfono</Label>
                  <Input
                    id="d_phone"
                    value={form.phone ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, phone: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="d_linkedin">LinkedIn</Label>
                  <Input
                    id="d_linkedin"
                    value={form.linkedin_url ?? ""}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        linkedin_url: e.target.value,
                      }))
                    }
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="d_role_category">Categoría</Label>
                <Select
                  value={(form.role_category as string) ?? "otros"}
                  onValueChange={(v) =>
                    setForm((f) => ({ ...f, role_category: v }))
                  }
                >
                  <SelectTrigger id="d_role_category">
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

              <div className="flex flex-col gap-2 rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 p-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.is_primary)}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        is_primary: e.target.checked,
                      }))
                    }
                  />
                  Contacto principal
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.is_signatory)}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        is_signatory: e.target.checked,
                      }))
                    }
                  />
                  Signatario contratos
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(form.has_portal_access)}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        has_portal_access: e.target.checked,
                      }))
                    }
                  />
                  Acceso portal cliente
                </label>
              </div>

              <div>
                <Label htmlFor="d_notes">Notas internas (Marcos)</Label>
                <Textarea
                  id="d_notes"
                  rows={4}
                  value={form.notes_marcos ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      notes_marcos: e.target.value,
                    }))
                  }
                />
              </div>

              {!contact.is_active && contact.inactive_reason ? (
                <p className="rounded-md bg-fulkro-warning/10 p-2 text-xs text-fulkro-warning">
                  Inactivo desde{" "}
                  {formatDateTime(contact.inactive_since)}: {" "}
                  {contact.inactive_reason}
                </p>
              ) : null}

              <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-fulkro-ink-100 pt-3">
                <Button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saving}
                >
                  {saving ? "Guardando…" : "Guardar cambios"}
                </Button>
                {contact.is_active ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void handleDeactivate()}
                  >
                    Desactivar
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void handleActivate()}
                  >
                    Reactivar
                  </Button>
                )}
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => void handleDelete()}
                >
                  Eliminar
                </Button>
              </div>
            </TabsContent>

            {/* Tab Timeline */}
            <TabsContent value="timeline" className="mt-4">
              {timeline.length === 0 ? (
                <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
                  Sin interacciones registradas.
                </p>
              ) : (
                <ol className="flex flex-col gap-3">
                  {timeline.map((t) => (
                    <li
                      key={t.id}
                      className="rounded-md border border-fulkro-ink-100 bg-white p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="outline">
                          {INTERACTION_TYPE_LABELS[
                            t.interaction_type as keyof typeof INTERACTION_TYPE_LABELS
                          ] ?? t.interaction_type}
                        </Badge>
                        <span className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                          {formatDateTime(t.occurred_at)}
                        </span>
                      </div>
                      {t.summary ? (
                        <p className="mt-2 text-base font-medium text-[color:var(--fulkro-body)]">
                          {t.summary}
                        </p>
                      ) : null}
                      {t.source_motor ? (
                        <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                          Origen: {t.source_motor}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ol>
              )}
            </TabsContent>
          </Tabs>
        )}
      </SheetContent>
    </Sheet>
  );
}
