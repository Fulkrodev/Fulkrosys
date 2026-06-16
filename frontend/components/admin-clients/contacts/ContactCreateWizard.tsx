"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Stepper } from "@/components/ui/stepper";
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/api";
import { createContact } from "@/lib/admin-contacts/api";
import {
  ROLE_CATEGORIES,
  ROLE_CATEGORY_LABELS,
} from "@/lib/admin-contacts/schemas";

const STEPS = [
  { id: "basics", label: "Datos básicos" },
  { id: "category", label: "Categorización" },
  { id: "notes", label: "Notas y confirmación" },
];

// === Schemas Zod por paso ===
const basicsSchema = z.object({
  full_name: z.string().min(1, "Nombre requerido").max(255),
  preferred_name: z.string().max(100).optional().or(z.literal("")),
  email: z.string().email("Email inválido"),
  phone: z.string().max(50).optional().or(z.literal("")),
  linkedin_url: z
    .string()
    .url("URL LinkedIn inválida")
    .optional()
    .or(z.literal("")),
  role_title: z.string().min(1, "Cargo requerido").max(150),
});

const categorySchema = z.object({
  role_category: z.enum(ROLE_CATEGORIES, {
    message: "Categoría requerida",
  }),
  is_primary: z.boolean().default(false),
  is_signatory: z.boolean().default(false),
  has_portal_access: z.boolean().default(false),
});

const notesSchema = z.object({
  notes_marcos: z.string().optional().or(z.literal("")),
});

type BasicsForm = z.infer<typeof basicsSchema>;
type CategoryForm = z.infer<typeof categorySchema>;
type NotesForm = z.infer<typeof notesSchema>;

type Props = {
  clientId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
};

export function ContactCreateWizard({
  clientId,
  open,
  onOpenChange,
  onCreated,
}: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const basicsForm = useForm<BasicsForm>({
    resolver: zodResolver(basicsSchema),
    defaultValues: {
      full_name: "",
      preferred_name: "",
      email: "",
      phone: "",
      linkedin_url: "",
      role_title: "",
    },
  });

  const categoryForm = useForm<CategoryForm>({
    resolver: zodResolver(categorySchema),
    defaultValues: {
      role_category: "otros",
      is_primary: false,
      is_signatory: false,
      has_portal_access: false,
    },
  });

  const notesForm = useForm<NotesForm>({
    resolver: zodResolver(notesSchema),
    defaultValues: { notes_marcos: "" },
  });

  const reset = () => {
    setStepIndex(0);
    basicsForm.reset();
    categoryForm.reset();
    notesForm.reset();
  };

  const closeAndReset = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const advance = async () => {
    if (stepIndex === 0) {
      const ok = await basicsForm.trigger();
      if (ok) setStepIndex(1);
    } else if (stepIndex === 1) {
      const ok = await categoryForm.trigger();
      if (ok) setStepIndex(2);
    }
  };

  const back = () => setStepIndex((i) => Math.max(0, i - 1));

  const submit = async () => {
    const basics = basicsForm.getValues();
    const category = categoryForm.getValues();
    const notes = notesForm.getValues();

    setSubmitting(true);
    try {
      await createContact(clientId, {
        full_name: basics.full_name,
        preferred_name: basics.preferred_name || null,
        email: basics.email,
        phone: basics.phone || null,
        linkedin_url: basics.linkedin_url || null,
        role_title: basics.role_title,
        role_category: category.role_category,
        is_primary: category.is_primary,
        is_signatory: category.is_signatory,
        has_portal_access: category.has_portal_access,
        notes_marcos: notes.notes_marcos || null,
      });
      toast.success("Contacto creado");
      onCreated?.();
      closeAndReset(false);
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

  const basics = basicsForm.watch();
  const category = categoryForm.watch();

  return (
    <Dialog open={open} onOpenChange={closeAndReset}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Nuevo contacto</DialogTitle>
          <DialogDescription>
            Catálogo agenda profesional cliente. No es un usuario del portal.
          </DialogDescription>
        </DialogHeader>

        <div className="my-4">
          <Stepper steps={STEPS} currentIndex={stepIndex} />
        </div>

        {/* Step 1: Datos básicos */}
        {stepIndex === 0 ? (
          <form className="flex flex-col gap-3">
            <div>
              <Label htmlFor="full_name">Nombre completo *</Label>
              <Input
                id="full_name"
                {...basicsForm.register("full_name")}
              />
              {basicsForm.formState.errors.full_name ? (
                <p className="mt-1 text-xs text-fulkro-danger">
                  {basicsForm.formState.errors.full_name.message}
                </p>
              ) : null}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="preferred_name">Nombre preferido</Label>
                <Input
                  id="preferred_name"
                  {...basicsForm.register("preferred_name")}
                />
              </div>
              <div>
                <Label htmlFor="role_title">Cargo *</Label>
                <Input
                  id="role_title"
                  {...basicsForm.register("role_title")}
                />
                {basicsForm.formState.errors.role_title ? (
                  <p className="mt-1 text-xs text-fulkro-danger">
                    {basicsForm.formState.errors.role_title.message}
                  </p>
                ) : null}
              </div>
            </div>

            <div>
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                {...basicsForm.register("email")}
              />
              {basicsForm.formState.errors.email ? (
                <p className="mt-1 text-xs text-fulkro-danger">
                  {basicsForm.formState.errors.email.message}
                </p>
              ) : null}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="phone">Teléfono</Label>
                <Input id="phone" {...basicsForm.register("phone")} />
              </div>
              <div>
                <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                <Input
                  id="linkedin_url"
                  {...basicsForm.register("linkedin_url")}
                />
                {basicsForm.formState.errors.linkedin_url ? (
                  <p className="mt-1 text-xs text-fulkro-danger">
                    {basicsForm.formState.errors.linkedin_url.message}
                  </p>
                ) : null}
              </div>
            </div>
          </form>
        ) : null}

        {/* Step 2: Categorización */}
        {stepIndex === 1 ? (
          <form className="flex flex-col gap-3">
            <div>
              <Label htmlFor="role_category">Categoría *</Label>
              <Select
                value={categoryForm.watch("role_category")}
                onValueChange={(v) =>
                  categoryForm.setValue(
                    "role_category",
                    v as CategoryForm["role_category"],
                  )
                }
              >
                <SelectTrigger id="role_category">
                  <SelectValue placeholder="Selecciona categoría" />
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

            <div className="flex flex-col gap-2">
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  {...categoryForm.register("is_primary")}
                />
                <span>
                  <strong>Contacto principal</strong>
                  <span className="ml-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                    (sólo uno por cliente — desmarcará otros si los hay)
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  {...categoryForm.register("is_signatory")}
                />
                <span>
                  <strong>Signatario</strong>
                  <span className="ml-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                    (puede firmar contratos C-001 — usado por M14)
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  {...categoryForm.register("has_portal_access")}
                />
                <span>
                  <strong>Acceso a portal cliente</strong>
                  <span className="ml-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                    (vinculación a ClientUser pendiente — sub-fase futura)
                  </span>
                </span>
              </label>
            </div>
          </form>
        ) : null}

        {/* Step 3: Notas + confirm */}
        {stepIndex === 2 ? (
          <form className="flex flex-col gap-3">
            <div>
              <Label htmlFor="notes_marcos">Notas internas (Marcos)</Label>
              <Textarea
                id="notes_marcos"
                rows={4}
                placeholder="Contexto, preferencias, observaciones para futuras interacciones..."
                {...notesForm.register("notes_marcos")}
              />
              <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                Las notas son privadas (sólo Marcos). Indexadas para búsqueda
                full-text.
              </p>
            </div>

            <div className="rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 p-3 text-sm">
              <p className="font-medium text-fulkro-ink-800">
                Resumen del contacto
              </p>
              <ul className="mt-2 space-y-1 text-fulkro-ink-700">
                <li>
                  <strong>{basics.full_name}</strong>{" "}
                  {basics.preferred_name ? `(${basics.preferred_name})` : ""}
                </li>
                <li>
                  {basics.role_title} ·{" "}
                  {ROLE_CATEGORY_LABELS[category.role_category]}
                </li>
                <li>{basics.email}</li>
                {category.is_primary ? <li>· Contacto principal</li> : null}
                {category.is_signatory ? <li>· Signatario</li> : null}
                {category.has_portal_access ? (
                  <li>· Acceso portal cliente</li>
                ) : null}
              </ul>
            </div>
          </form>
        ) : null}

        <div className="mt-4 flex items-center justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={back}
            disabled={stepIndex === 0 || submitting}
          >
            Atrás
          </Button>

          {stepIndex < STEPS.length - 1 ? (
            <Button type="button" onClick={() => void advance()}>
              Siguiente
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => void submit()}
              disabled={submitting}
            >
              {submitting ? "Creando…" : "Crear contacto"}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
