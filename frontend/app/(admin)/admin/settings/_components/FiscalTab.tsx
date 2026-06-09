"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

import { ApiError } from "@/lib/api";
import {
  fiscalSchema,
  type AdminSettingsResponse,
  type FiscalSettings,
} from "@/lib/admin-settings/schemas";

type Props = {
  fiscal: FiscalSettings;
  onUpdate: (payload: FiscalSettings) => Promise<AdminSettingsResponse>;
};

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      {children}
      {hint && (
        <p className="text-xs font-medium text-[color:var(--fulkro-muted)]">
          {hint}
        </p>
      )}
      {error && <p className="text-xs text-fulkro-danger">{error}</p>}
    </div>
  );
}

export function FiscalTab({ fiscal, onUpdate }: Props) {
  const form = useForm<FiscalSettings>({
    resolver: zodResolver(fiscalSchema),
    defaultValues: {
      nif: fiscal.nif ?? "",
      nombre_fiscal: fiscal.nombre_fiscal ?? "",
      nombre_comercial: fiscal.nombre_comercial ?? "",
      tipo_persona: fiscal.tipo_persona ?? "F",
      domicilio_via: fiscal.domicilio_via ?? "",
      domicilio_cp: fiscal.domicilio_cp ?? "",
      domicilio_municipio: fiscal.domicilio_municipio ?? "",
      domicilio_provincia: fiscal.domicilio_provincia ?? "",
      domicilio_pais: fiscal.domicilio_pais ?? "España",
      iva_pct: fiscal.iva_pct ?? 21,
      sujeto_irpf: fiscal.sujeto_irpf ?? true,
      irpf_pct: fiscal.irpf_pct ?? 15,
      iban: fiscal.iban ?? "",
      bank_holder: fiscal.bank_holder ?? "",
      bank_institution: fiscal.bank_institution ?? "",
      bank_bic: fiscal.bank_bic ?? "",
    },
  });

  const onSubmit = async (data: FiscalSettings) => {
    try {
      await onUpdate(data);
      toast.success("Datos fiscales actualizados");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar los datos fiscales",
      );
    }
  };

  const e = form.formState.errors;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Datos fiscales del consultor</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-8"
        >
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Fuente única de tu identidad fiscal: alimenta el NIF y el IBAN de las
            facturas, el QR Verifactu, los contratos y los DPA. Si dejas un campo
            vacío, los documentos degradan con elegancia (nunca imprimen un dato
            inventado).
          </p>

          <section className="flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-[color:var(--fulkro-title)]">
              Identidad
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="NIF / CIF" error={e.nif?.message} hint="Autónomo: NIF con letra.">
                <Input placeholder="77171140E" {...form.register("nif")} />
              </Field>
              <Field label="Tipo de persona">
                <Select
                  value={form.watch("tipo_persona")}
                  onValueChange={(v) =>
                    form.setValue("tipo_persona", v as "F" | "J", {
                      shouldValidate: true,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="F">Persona física (autónomo)</SelectItem>
                    <SelectItem value="J">Persona jurídica (sociedad)</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Nombre / razón fiscal" error={e.nombre_fiscal?.message}>
                <Input placeholder="Marcos Mata García" {...form.register("nombre_fiscal")} />
              </Field>
              <Field label="Nombre comercial" hint="Marca. Si vacío, se usa el fiscal.">
                <Input placeholder="FULKRO" {...form.register("nombre_comercial")} />
              </Field>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-[color:var(--fulkro-title)]">
              Domicilio fiscal
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Vía y número">
                <Input placeholder="Paseo de la Dirección, 46" {...form.register("domicilio_via")} />
              </Field>
              <Field label="Código postal">
                <Input placeholder="28039" {...form.register("domicilio_cp")} />
              </Field>
              <Field label="Municipio">
                <Input placeholder="Madrid" {...form.register("domicilio_municipio")} />
              </Field>
              <Field label="Provincia">
                <Input placeholder="Madrid" {...form.register("domicilio_provincia")} />
              </Field>
              <Field label="País">
                <Input placeholder="España" {...form.register("domicilio_pais")} />
              </Field>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-[color:var(--fulkro-title)]">
              Régimen impositivo
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="IVA (%)" error={e.iva_pct?.message}>
                <Input
                  type="number"
                  step="0.01"
                  {...form.register("iva_pct", { valueAsNumber: true })}
                />
              </Field>
              <Field label="Retención IRPF (%)" error={e.irpf_pct?.message} hint="Nuevo autónomo: 7% reducido los 3 primeros años.">
                <Input
                  type="number"
                  step="0.01"
                  {...form.register("irpf_pct", { valueAsNumber: true })}
                />
              </Field>
              <div className="flex items-center gap-3 sm:col-span-2">
                <Switch
                  checked={form.watch("sujeto_irpf")}
                  onCheckedChange={(c) => form.setValue("sujeto_irpf", c)}
                  id="sujeto_irpf"
                />
                <Label htmlFor="sujeto_irpf">
                  Sujeto a retención de IRPF (facturas a empresa/AAPP)
                </Label>
              </div>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h3 className="text-sm font-semibold text-[color:var(--fulkro-title)]">
              Datos bancarios
            </h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="IBAN" error={e.iban?.message}>
                <Input placeholder="ES34 1465 0260 6317 5549 5007" {...form.register("iban")} />
              </Field>
              <Field label="Titular">
                <Input placeholder="Marcos Mata García" {...form.register("bank_holder")} />
              </Field>
              <Field label="Entidad">
                <Input placeholder="Banco Santander" {...form.register("bank_institution")} />
              </Field>
              <Field label="BIC / SWIFT" hint="Opcional · solo SEPA internacional.">
                <Input placeholder="BSCHESMMXXX" {...form.register("bank_bic")} />
              </Field>
            </div>
          </section>

          <Button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="self-start"
          >
            {form.formState.isSubmitting ? "Guardando..." : "Guardar datos fiscales"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
