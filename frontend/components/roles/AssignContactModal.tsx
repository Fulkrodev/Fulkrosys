"use client";

/**
 * AssignContactModal · 2 tabs (buscar existing / crear nuevo).
 *
 * Constraint v3 frontend validation: si has_portal_access=true switch ·
 * pre-save check existing contacts → alert + disabled si ya existe portal user.
 * Backend M30 EXTENDED partial UNIQUE garantiza integridad · 409 handling.
 *
 * Si rol ya asignado · alert + confirmation reasignación overwrite.
 */
import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Loader2, ShieldCheck, UserSearch } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
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
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";
import {
  useRoleTopology,
  validateConstraintV3,
} from "@/hooks/useRoleTopology";
import {
  ROLE_LABELS,
  type ProjectContact,
  type RoleAssignment,
} from "@/lib/admin-roles/api";

const createSchema = z.object({
  full_name: z.string().min(2, "Nombre requerido (mín. 2)").max(255),
  email: z.string().email("Email inválido"),
  phone: z.string().max(50).optional().or(z.literal("")),
  linkedin_url: z.string().max(500).optional().or(z.literal("")),
  role_title: z.string().min(2, "Cargo requerido").max(150),
  has_portal_access: z.boolean(),
  notes_marcos: z.string().max(2000).optional().or(z.literal("")),
});

type CreateFormData = z.infer<typeof createSchema>;

interface AssignContactModalProps {
  projectId: string;
  assignment: RoleAssignment | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts[0]?.[0] ?? "?").toUpperCase() + (parts[1]?.[0] ?? "").toUpperCase();
}

export function AssignContactModal({
  projectId,
  assignment,
  open,
  onOpenChange,
}: AssignContactModalProps) {
  const rt = useRoleTopology(projectId);
  const [tab, setTab] = React.useState<"existing" | "new">("existing");
  const [search, setSearch] = React.useState("");
  const [selected, setSelected] = React.useState<ProjectContact | null>(null);

  const form = useForm<CreateFormData>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      full_name: "",
      email: "",
      phone: "",
      linkedin_url: "",
      role_title: "",
      has_portal_access: false,
      notes_marcos: "",
    },
  });

  React.useEffect(() => {
    if (!open) {
      setSelected(null);
      setSearch("");
      setTab("existing");
      form.reset();
    }
  }, [open, form]);

  const allContacts = rt.contacts.data?.contacts ?? [];
  const portalAccessExisting = validateConstraintV3(allContacts);

  const filtered = React.useMemo(() => {
    if (!search) return allContacts;
    const q = search.toLowerCase();
    return allContacts.filter(
      (c) =>
        c.full_name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.role_title.toLowerCase().includes(q),
    );
  }, [allContacts, search]);

  const meta = assignment ? ROLE_LABELS[assignment.role_code] : null;
  const isReassign = Boolean(assignment?.contact);

  const onAssignExisting = async () => {
    if (!assignment || !selected) return;
    try {
      await rt.assignRole.mutateAsync({
        roleCode: assignment.role_code,
        payload: { contact_id: selected.id },
      });
      toast.success(
        `${selected.full_name} asignado a ${meta?.short ?? assignment.role_code}`,
      );
      onOpenChange(false);
    } catch {
      toast.error("Error al asignar rol");
    }
  };

  const onCreateAndAssign = async (values: CreateFormData) => {
    if (!assignment) return;
    try {
      const newContact = await rt.createContact.mutateAsync({
        full_name: values.full_name,
        email: values.email,
        phone: values.phone || null,
        linkedin_url: values.linkedin_url || null,
        role_title: values.role_title,
        role_category: "otros",
        has_portal_access: values.has_portal_access,
        notes_marcos: values.notes_marcos || null,
      });
      await rt.assignRole.mutateAsync({
        roleCode: assignment.role_code,
        payload: { contact_id: newContact.id },
      });
      toast.success(
        `${newContact.full_name} creado y asignado a ${meta?.short ?? assignment.role_code}`,
      );
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error";
      if (msg.includes("Constraint v3") || msg.toLowerCase().includes("conflict")) {
        toast.error(
          "Constraint v3: ya hay un contacto con cuenta portal en este proyecto.",
        );
      } else {
        toast.error("Error al crear contacto");
      }
    }
  };

  if (!assignment || !meta) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex flex-wrap items-center gap-2 text-[color:var(--fulkro-title)]">
            Asignar {meta.short}{" "}
            <Badge variant="outline">{meta.label}</Badge>
          </DialogTitle>
          <DialogDescription>
            {meta.description}
          </DialogDescription>
        </DialogHeader>

        {isReassign ? (
          <div className="rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 p-3 text-xs text-fulkro-warning">
            <p className="flex items-center gap-1.5 font-bold">
              <AlertTriangle size={12} strokeWidth={2.4} />
              Reasignación
            </p>
            <p className="mt-1 text-fulkro-ink-700">
              Este rol ya está asignado a{" "}
              <span className="font-bold">{assignment.contact?.full_name}</span>
              . Confirmar sobrescribirá la asignación actual.
            </p>
          </div>
        ) : null}

        <Tabs value={tab} onValueChange={(v) => setTab(v as "existing" | "new")}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="existing">
              Buscar contacto existente
            </TabsTrigger>
            <TabsTrigger value="new">Crear contacto nuevo</TabsTrigger>
          </TabsList>

          <TabsContent value="existing" className="flex flex-col gap-3">
            <div className="relative">
              <UserSearch
                size={14}
                strokeWidth={2.4}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fulkro-ink-600"
              />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre, email o cargo…"
                className="pl-8"
              />
            </div>
            <div className="max-h-[280px] overflow-y-auto rounded-md border border-fulkro-ink-200">
              {rt.contacts.isLoading ? (
                <p className="py-6 text-center text-sm text-fulkro-ink-600">
                  Cargando contactos…
                </p>
              ) : filtered.length === 0 ? (
                <p className="py-6 text-center text-sm text-fulkro-ink-600">
                  Sin contactos. Crea uno nuevo en la pestaña siguiente.
                </p>
              ) : (
                <ul className="flex flex-col">
                  {filtered.map((contact) => {
                    const isSelected = selected?.id === contact.id;
                    const isCurrent =
                      assignment.contact_id === contact.id;
                    return (
                      <li key={contact.id}>
                        <button
                          type="button"
                          onClick={() => setSelected(contact)}
                          className={cn(
                            "flex w-full items-center gap-3 border-b border-fulkro-ink-100 p-3 text-left transition-colors last:border-b-0",
                            isSelected
                              ? "bg-fulkro-primary-700/10"
                              : "bg-white hover:bg-fulkro-ink-50",
                          )}
                        >
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-fulkro-ink-200 text-xs font-bold text-fulkro-ink-700">
                            {initials(contact.full_name)}
                          </div>
                          <div className="flex flex-1 flex-col gap-0.5">
                            <span className="text-sm font-medium text-[color:var(--fulkro-title)]">
                              {contact.full_name}
                              {isCurrent ? (
                                <Badge variant="info" className="ml-2 text-[10px]">
                                  Asignado actualmente
                                </Badge>
                              ) : null}
                            </span>
                            <span className="text-xs text-fulkro-ink-500">
                              {contact.role_title} · {contact.email}
                            </span>
                          </div>
                          {contact.has_portal_access ? (
                            <Badge variant="info" className="text-[10px]">
                              <ShieldCheck
                                size={10}
                                strokeWidth={2.4}
                                className="mr-1"
                              />
                              Portal
                            </Badge>
                          ) : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancelar
              </Button>
              <Button
                variant="primary"
                disabled={!selected || rt.assignRole.isPending}
                onClick={() => void onAssignExisting()}
              >
                {rt.assignRole.isPending ? (
                  <Loader2
                    size={14}
                    className="animate-spin"
                    strokeWidth={2.4}
                  />
                ) : null}
                {isReassign
                  ? "Reasignar (sobrescribe)"
                  : `Asignar a ${meta.short}`}
              </Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="new">
            <form
              onSubmit={form.handleSubmit(onCreateAndAssign)}
              className="flex flex-col gap-3"
            >
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="contact-name">Nombre completo</Label>
                  <Input id="contact-name" {...form.register("full_name")} />
                  {form.formState.errors.full_name ? (
                    <p className="text-xs text-fulkro-danger">
                      {form.formState.errors.full_name.message}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="contact-email">Email</Label>
                  <Input
                    id="contact-email"
                    type="email"
                    {...form.register("email")}
                  />
                  {form.formState.errors.email ? (
                    <p className="text-xs text-fulkro-danger">
                      {form.formState.errors.email.message}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="contact-phone">Teléfono (opcional)</Label>
                  <Input id="contact-phone" {...form.register("phone")} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="contact-cargo">Cargo</Label>
                  <Input
                    id="contact-cargo"
                    {...form.register("role_title")}
                    placeholder="CISO · CTO · Sponsor…"
                  />
                  {form.formState.errors.role_title ? (
                    <p className="text-xs text-fulkro-danger">
                      {form.formState.errors.role_title.message}
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="contact-linkedin">LinkedIn (opcional)</Label>
                <Input
                  id="contact-linkedin"
                  {...form.register("linkedin_url")}
                  placeholder="https://linkedin.com/in/…"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="contact-notes">Notas (opcional)</Label>
                <Textarea
                  id="contact-notes"
                  rows={2}
                  {...form.register("notes_marcos")}
                />
              </div>

              {/* Constraint v3 portal switch */}
              <div className="flex items-start gap-3 rounded-md border border-fulkro-ink-200 p-3">
                <Switch
                  checked={form.watch("has_portal_access")}
                  onCheckedChange={(v) =>
                    form.setValue("has_portal_access", v)
                  }
                  disabled={Boolean(portalAccessExisting)}
                  id="portal-access"
                />
                <div className="flex flex-1 flex-col gap-1">
                  <Label
                    htmlFor="portal-access"
                    className="cursor-pointer text-sm font-bold text-[color:var(--fulkro-title)]"
                  >
                    Crear cuenta portal cliente{" "}
                    <TooltipENS
                      text="ADR-013 v3 single-user-RW: solo 1 contacto del proyecto puede tener cuenta de portal cliente. Constraint enforced en BD (partial UNIQUE) + service-layer 409."
                      iconSize={12}
                    />
                  </Label>
                  {portalAccessExisting ? (
                    <p className="text-xs text-fulkro-warning">
                      <AlertTriangle
                        size={11}
                        strokeWidth={2.4}
                        className="mr-1 inline"
                      />
                      Ya hay un contacto con cuenta portal:{" "}
                      <span className="font-bold">
                        {portalAccessExisting.full_name}
                      </span>
                      . Solo 1 por proyecto.
                    </p>
                  ) : (
                    <p className="text-xs text-fulkro-ink-500">
                      Solo 1 contacto/proyecto puede tener cuenta. Recibirá
                      magic link para activar.
                    </p>
                  )}
                </div>
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  disabled={
                    rt.createContact.isPending || rt.assignRole.isPending
                  }
                >
                  {rt.createContact.isPending || rt.assignRole.isPending ? (
                    <Loader2
                      size={14}
                      className="animate-spin"
                      strokeWidth={2.4}
                    />
                  ) : null}
                  Crear y asignar
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
