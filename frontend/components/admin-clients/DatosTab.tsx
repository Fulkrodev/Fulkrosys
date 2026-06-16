"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { ApiError } from "@/lib/api";
import { updateClient } from "@/lib/admin-clients/api";
import type { ClientDetail } from "@/lib/admin-clients/schemas";

const datosSchema = z.object({
  nombre: z.string().min(1, "Razón social requerida").max(255),
  sector: z.string().max(100).optional().or(z.literal("")),
  provincia: z.string().max(100).optional().or(z.literal("")),
  numero_empleados: z
    .union([
      z.number().int().min(0),
      z.literal("").transform(() => null),
      z.null(),
    ])
    .optional(),
  contacto_email: z.string().email("Email inválido").or(z.literal("")),
  contacto_telefono: z.string().max(50).optional().or(z.literal("")),
  lead_source: z.string().max(100).optional().or(z.literal("")),
});

type DatosFormData = z.infer<typeof datosSchema>;

export function DatosTab({
  detail,
  onUpdated,
}: {
  detail: ClientDetail;
  onUpdated: () => Promise<void>;
}) {
  const form = useForm<DatosFormData>({
    resolver: zodResolver(datosSchema),
    defaultValues: {
      nombre: detail.nombre,
      sector: detail.sector ?? "",
      provincia: detail.provincia ?? "",
      numero_empleados: detail.numero_empleados ?? null,
      contacto_email: detail.contacto_email ?? "",
      contacto_telefono: detail.contacto_telefono ?? "",
      lead_source: detail.lead_source ?? "",
    },
  });

  const onSubmit = async (data: DatosFormData) => {
    try {
      await updateClient(detail.id, {
        nombre: data.nombre,
        sector: data.sector || null,
        provincia: data.provincia || null,
        numero_empleados:
          typeof data.numero_empleados === "number"
            ? data.numero_empleados
            : null,
        contacto_email: data.contacto_email || null,
        contacto_telefono: data.contacto_telefono || null,
        lead_source: data.lead_source || null,
      });
      toast.success("Datos cliente actualizados");
      await onUpdated();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar",
      );
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Datos cliente</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          <div className="flex flex-col gap-2 sm:col-span-2">
            <Label htmlFor="nombre">Razón social</Label>
            <Input id="nombre" {...form.register("nombre")} />
            {form.formState.errors.nombre && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.nombre.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label>NIF / CIF (read-only)</Label>
            <Input
              value={detail.cif}
              readOnly
              className="bg-fulkro-ink-50/30 font-mono"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label>Fecha alta (read-only)</Label>
            <Input
              value={new Date(detail.created_at).toLocaleDateString("es-ES")}
              readOnly
              className="bg-fulkro-ink-50/30"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="sector">Sector</Label>
            <Input
              id="sector"
              {...form.register("sector")}
              placeholder="publico / privado / sanidad ..."
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="provincia">Provincia</Label>
            <Input id="provincia" {...form.register("provincia")} />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="numero_empleados">Nº empleados</Label>
            <Input
              id="numero_empleados"
              type="number"
              min={0}
              {...form.register("numero_empleados", {
                setValueAs: (v) => (v === "" ? null : Number(v)),
              })}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="lead_source">Lead source</Label>
            <Input id="lead_source" {...form.register("lead_source")} />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="contacto_email">Email contacto</Label>
            <Input
              id="contacto_email"
              type="email"
              {...form.register("contacto_email")}
            />
            {form.formState.errors.contacto_email && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.contacto_email.message}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="contacto_telefono">Teléfono contacto</Label>
            <Input
              id="contacto_telefono"
              {...form.register("contacto_telefono")}
            />
          </div>

          <div className="sm:col-span-2">
            <Button
              type="submit"
              disabled={form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? "Guardando..." : "Guardar cambios"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
