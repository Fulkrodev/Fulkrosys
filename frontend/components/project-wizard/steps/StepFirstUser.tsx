"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import type { Step5FirstUser } from "@/lib/api/project-diagnostico";

const schema = z.object({
  email: z.string().email("Email inválido"),
  full_name: z.string().min(1, "Nombre requerido").max(255),
  cargo: z.string().max(150).optional().or(z.literal("")),
  send_magic_link: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

interface StepFirstUserProps {
  initialValue: Step5FirstUser | null;
  onSubmit: (data: Step5FirstUser) => void;
  onBack: () => void;
}

export function StepFirstUser({
  initialValue,
  onSubmit,
  onBack,
}: StepFirstUserProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: initialValue?.email ?? "",
      full_name: initialValue?.full_name ?? "",
      cargo: initialValue?.cargo ?? "",
      send_magic_link: initialValue?.send_magic_link ?? false,
    },
  });

  const handleSubmit = (values: FormValues) => {
    onSubmit({
      email: values.email.trim().toLowerCase(),
      full_name: values.full_name.trim(),
      cargo: values.cargo?.trim() || null,
      send_magic_link: values.send_magic_link,
    });
  };

  return (
    <form
      onSubmit={form.handleSubmit(handleSubmit)}
      className="space-y-4"
      data-testid="step-first-user"
    >
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">
          Paso 5 · Primer usuario del portal cliente
        </h2>
        <p className="text-sm text-muted-foreground">
          Crearemos un usuario portal con acceso completo al proyecto.
          Si activas magic-link · enviaremos email con invitación seguro
          (válido 24h). Si no · obtendrás un password temporal para
          comunicarlo por canal seguro.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor="email">
            Email <span className="text-fulkro-warning">*</span>
          </Label>
          <Input
            id="email"
            type="email"
            placeholder="user@empresa.es"
            data-testid="field-user-email"
            {...form.register("email")}
          />
          {form.formState.errors.email && (
            <p className="text-xs text-fulkro-danger">
              {form.formState.errors.email.message}
            </p>
          )}
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="full_name">
            Nombre completo <span className="text-fulkro-warning">*</span>
          </Label>
          <Input
            id="full_name"
            placeholder="Nombre Apellidos"
            data-testid="field-user-fullname"
            {...form.register("full_name")}
          />
          {form.formState.errors.full_name && (
            <p className="text-xs text-fulkro-danger">
              {form.formState.errors.full_name.message}
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor="cargo">Cargo</Label>
        <Input
          id="cargo"
          placeholder="CEO · CISO · CTO · Compliance Officer · etc"
          data-testid="field-user-cargo"
          {...form.register("cargo")}
        />
      </div>

      <Alert variant="info">
        <AlertTitle>
          Magic-link · acceso sin password{" "}
          <TooltipENS text="Magic-link = link único firmado criptográficamente Ed25519 · válido 24h · single-use" />
        </AlertTitle>
        <AlertDescription>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              data-testid="field-magic-link"
              {...form.register("send_magic_link")}
              className="h-4 w-4 rounded border-fulkro-ink-300 text-fulkro-primary-700"
            />
            <span className="text-sm">
              Enviar magic-link al email · usuario accede directo sin password
              (recomendado · más seguro que comunicar password manualmente).
            </span>
          </label>
        </AlertDescription>
      </Alert>

      <div className="flex items-center justify-between gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          data-testid="step5-back"
        >
          <ChevronLeft size={14} className="mr-1" />
          Atrás
        </Button>
        <Button type="submit" data-testid="step5-next">
          Siguiente
          <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </form>
  );
}
