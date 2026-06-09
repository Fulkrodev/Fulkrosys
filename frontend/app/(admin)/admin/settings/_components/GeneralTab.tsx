"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { ApiError } from "@/lib/api";
import {
  generalSchema,
  type GeneralSettings,
  type AdminSettingsResponse,
} from "@/lib/admin-settings/schemas";

type Props = {
  general: GeneralSettings;
  onUpdate: (payload: GeneralSettings) => Promise<AdminSettingsResponse>;
};

const TIMEZONES = [
  "Europe/Madrid",
  "Europe/Lisbon",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/London",
  "Europe/Rome",
  "Europe/Amsterdam",
  "Atlantic/Canary",
  "UTC",
];

const LOCALES = [
  { value: "es-ES", label: "Español (España)" },
  { value: "en-US", label: "English (United States)" },
  { value: "en-GB", label: "English (United Kingdom)" },
  { value: "pt-PT", label: "Português (Portugal)" },
  { value: "fr-FR", label: "Français (France)" },
];

const DATE_FORMATS = [
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY (28/04/2026)" },
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY (04/28/2026)" },
  { value: "YYYY-MM-DD", label: "YYYY-MM-DD (2026-04-28)" },
];

export function GeneralTab({ general, onUpdate }: Props) {
  const form = useForm<GeneralSettings>({
    resolver: zodResolver(generalSchema),
    defaultValues: {
      timezone: general.timezone ?? "Europe/Madrid",
      locale: general.locale ?? "es-ES",
      date_format: general.date_format ?? "DD/MM/YYYY",
    },
  });

  const onSubmit = async (data: GeneralSettings) => {
    try {
      await onUpdate(data);
      toast.success("Configuración general actualizada");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar configuración general",
      );
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>General</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col gap-2">
            <Label>Zona horaria</Label>
            <Select
              value={form.watch("timezone")}
              onValueChange={(value) =>
                form.setValue("timezone", value, { shouldValidate: true })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONES.map((tz) => (
                  <SelectItem key={tz} value={tz}>
                    {tz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              IANA timezone identifier. Por defecto: Europe/Madrid
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Label>Idioma</Label>
            <Select
              value={form.watch("locale")}
              onValueChange={(value) =>
                form.setValue("locale", value, { shouldValidate: true })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LOCALES.map((loc) => (
                  <SelectItem key={loc.value} value={loc.value}>
                    {loc.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.locale && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.locale.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label>Formato de fecha</Label>
            <Select
              value={form.watch("date_format")}
              onValueChange={(value) =>
                form.setValue("date_format", value, { shouldValidate: true })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DATE_FORMATS.map((fmt) => (
                  <SelectItem key={fmt.value} value={fmt.value}>
                    {fmt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="self-start"
          >
            {form.formState.isSubmitting ? "Guardando..." : "Guardar general"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
