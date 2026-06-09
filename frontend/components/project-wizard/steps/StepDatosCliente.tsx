"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronRight } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import type { Step1DatosCliente } from "@/lib/api/project-diagnostico";

const schema = z.object({
  razon_social: z.string().min(1, "Razón social requerida").max(255),
  cif: z
    .string()
    .min(1, "NIF/CIF requerido")
    .max(20)
    .regex(/^[A-Z0-9]+$/i, "Formato NIF/CIF inválido"),
  sector_industrial: z.string().max(100).optional().or(z.literal("")),
  domicilio_fiscal: z.string().max(255).optional().or(z.literal("")),
  web: z.string().max(255).optional().or(z.literal("")),
  contacto_email: z
    .string()
    .email("Email inválido")
    .optional()
    .or(z.literal("")),
  contacto_telefono: z.string().max(50).optional().or(z.literal("")),
  persona_contacto: z.string().max(255).optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

interface StepDatosClienteProps {
  initialValue: Step1DatosCliente | null;
  onSubmit: (data: Step1DatosCliente) => void;
}

export function StepDatosCliente({
  initialValue,
  onSubmit,
}: StepDatosClienteProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      razon_social: initialValue?.razon_social ?? "",
      cif: initialValue?.cif ?? "",
      sector_industrial: initialValue?.sector_industrial ?? "",
      domicilio_fiscal: initialValue?.domicilio_fiscal ?? "",
      web: initialValue?.web ?? "",
      contacto_email: initialValue?.contacto_email ?? "",
      contacto_telefono: initialValue?.contacto_telefono ?? "",
      persona_contacto: initialValue?.persona_contacto ?? "",
    },
  });

  const handleSubmit = (values: FormValues) => {
    onSubmit({
      razon_social: values.razon_social.trim(),
      cif: values.cif.trim().toUpperCase(),
      sector_industrial: values.sector_industrial || null,
      domicilio_fiscal: values.domicilio_fiscal || null,
      web: values.web || null,
      contacto_email: values.contacto_email || null,
      contacto_telefono: values.contacto_telefono || null,
      persona_contacto: values.persona_contacto || null,
    });
  };

  return (
    <form
      onSubmit={form.handleSubmit(handleSubmit)}
      className="space-y-4"
      data-testid="step-datos-cliente"
    >
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Paso 1 · Datos básicos del cliente</h2>
        <p className="text-sm text-muted-foreground">
          Identificación legal y contacto principal de la organización.
        </p>
      </div>

      <FieldGrid>
        <Field
          id="razon_social"
          label="Razón social"
          required
          error={form.formState.errors.razon_social?.message}
        >
          <Input
            id="razon_social"
            placeholder="Empresa SL"
            data-testid="field-razon-social"
            {...form.register("razon_social")}
          />
        </Field>
        <Field
          id="cif"
          label="NIF / CIF"
          required
          error={form.formState.errors.cif?.message}
        >
          <Input
            id="cif"
            placeholder="B12345678"
            data-testid="field-cif"
            {...form.register("cif")}
          />
        </Field>
      </FieldGrid>

      <FieldGrid>
        <Field id="sector_industrial" label="Sector industrial">
          <Input
            id="sector_industrial"
            placeholder="Sanidad / Educación / TIC / etc"
            data-testid="field-sector-industrial"
            {...form.register("sector_industrial")}
          />
        </Field>
        <Field id="web" label="Web corporativa">
          <Input
            id="web"
            placeholder="https://empresa.es"
            type="url"
            data-testid="field-web"
            {...form.register("web")}
          />
        </Field>
      </FieldGrid>

      <Field id="domicilio_fiscal" label="Domicilio fiscal">
        <Input
          id="domicilio_fiscal"
          placeholder="Calle Mayor 1, 28013 Madrid"
          data-testid="field-domicilio"
          {...form.register("domicilio_fiscal")}
        />
      </Field>

      <FieldGrid>
        <Field
          id="contacto_email"
          label="Email de contacto"
          error={form.formState.errors.contacto_email?.message}
        >
          <Input
            id="contacto_email"
            type="email"
            placeholder="info@empresa.es"
            data-testid="field-email"
            {...form.register("contacto_email")}
          />
        </Field>
        <Field id="contacto_telefono" label="Teléfono">
          <Input
            id="contacto_telefono"
            placeholder="+34 600 000 000"
            data-testid="field-telefono"
            {...form.register("contacto_telefono")}
          />
        </Field>
      </FieldGrid>

      <Field id="persona_contacto" label="Persona de contacto principal">
        <Input
          id="persona_contacto"
          placeholder="Nombre Apellidos"
          data-testid="field-persona"
          {...form.register("persona_contacto")}
        />
      </Field>

      <div className="flex items-center justify-between gap-2 pt-2">
        <p className="text-xs text-muted-foreground">
          Próximo paso: contexto <TooltipENS term="ENS" text="ENS = Esquema Nacional de Seguridad" />.
        </p>
        <Button type="submit" data-testid="step1-next">
          Siguiente
          <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </form>
  );
}

function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-3 sm:grid-cols-2">{children}</div>;
}

function Field({
  id,
  label,
  required,
  error,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id} className="flex items-center gap-1">
        <span>{label}</span>
        {required && <span className="text-fulkro-warning">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-fulkro-danger">{error}</p>}
    </div>
  );
}
