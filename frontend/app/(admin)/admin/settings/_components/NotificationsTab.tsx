"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import JsonView from "@uiw/react-json-view";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { ApiError } from "@/lib/api";
import {
  notificationsSchema,
  type NotificationsSettings,
  type AdminSettingsResponse,
} from "@/lib/admin-settings/schemas";

type Props = {
  notifications: NotificationsSettings;
  onUpdate: (
    payload: NotificationsSettings,
  ) => Promise<AdminSettingsResponse>;
};

export function NotificationsTab({ notifications, onUpdate }: Props) {
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [jsonText, setJsonText] = useState(() =>
    JSON.stringify(
      notifications.magic_link_per_purpose_overrides ?? {},
      null,
      2,
    ),
  );

  const form = useForm<NotificationsSettings>({
    resolver: zodResolver(notificationsSchema),
    defaultValues: {
      client_messages_forward_enabled:
        notifications.client_messages_forward_enabled ?? true,
      client_messages_forward_to:
        notifications.client_messages_forward_to ?? null,
      smtp_custom: notifications.smtp_custom ?? null,
      digest_enabled: notifications.digest_enabled ?? false,
      digest_time_local: notifications.digest_time_local ?? "08:00",
      magic_link_default_sender:
        notifications.magic_link_default_sender ?? null,
      marcos_whatsapp_number:
        notifications.marcos_whatsapp_number ?? null,
      magic_link_per_purpose_overrides:
        notifications.magic_link_per_purpose_overrides ?? null,
    },
  });

  const onSubmit = async (data: NotificationsSettings) => {
    let overrides: NotificationsSettings["magic_link_per_purpose_overrides"] =
      null;
    if (jsonText.trim() && jsonText.trim() !== "{}") {
      try {
        overrides = JSON.parse(jsonText);
        setJsonError(null);
      } catch (err) {
        setJsonError("JSON inválido: " + (err as Error).message);
        toast.error("JSON de overrides inválido");
        return;
      }
    }

    try {
      await onUpdate({
        ...data,
        magic_link_per_purpose_overrides: overrides,
      });
      toast.success("Notificaciones actualizadas");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al guardar notificaciones",
      );
    }
  };

  let parsedJsonForView: object = {};
  try {
    const parsed = JSON.parse(jsonText);
    if (parsed && typeof parsed === "object") {
      parsedJsonForView = parsed;
    }
  } catch {
    parsedJsonForView = {};
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notificaciones</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex items-center justify-between gap-4 rounded border border-fulkro-ink-300/40 p-4">
            <div className="flex flex-col gap-1">
              <Label htmlFor="client_messages_forward_enabled">
                Forward mensajes cliente
              </Label>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Reenvía mensajes de clientes a tu email
              </p>
            </div>
            <Switch
              id="client_messages_forward_enabled"
              checked={form.watch("client_messages_forward_enabled")}
              onCheckedChange={(v) =>
                form.setValue("client_messages_forward_enabled", v, {
                  shouldValidate: true,
                })
              }
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="client_messages_forward_to">
              Email destino forward
            </Label>
            <Input
              id="client_messages_forward_to"
              type="email"
              {...form.register("client_messages_forward_to")}
              placeholder="marcosmata@fulkro.es"
            />
            {form.formState.errors.client_messages_forward_to && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.client_messages_forward_to.message}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between gap-4 rounded border border-fulkro-ink-300/40 p-4">
            <div className="flex flex-col gap-1">
              <Label htmlFor="digest_enabled">Resumen diario</Label>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Email diario con resumen de actividad
              </p>
            </div>
            <Switch
              id="digest_enabled"
              checked={form.watch("digest_enabled") ?? false}
              onCheckedChange={(v) =>
                form.setValue("digest_enabled", v, { shouldValidate: true })
              }
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="digest_time_local">
              Hora envío resumen (HH:MM)
            </Label>
            <Input
              id="digest_time_local"
              type="time"
              {...form.register("digest_time_local")}
            />
            {form.formState.errors.digest_time_local && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.digest_time_local.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="magic_link_default_sender">
              Email remitente magic links
            </Label>
            <Input
              id="magic_link_default_sender"
              type="email"
              {...form.register("magic_link_default_sender")}
              placeholder="noreply@fulkro.es"
            />
            {form.formState.errors.magic_link_default_sender && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.magic_link_default_sender.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            {/* #26 · WhatsApp de Marcos editable (destino de notificaciones
                inbound del chat) · antes solo configurable por env. */}
            <Label htmlFor="marcos_whatsapp_number">
              WhatsApp de Marcos (notificaciones inbound)
            </Label>
            <Input
              id="marcos_whatsapp_number"
              type="tel"
              {...form.register("marcos_whatsapp_number")}
              placeholder="+34637165328"
            />
            {form.formState.errors.marcos_whatsapp_number && (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.marcos_whatsapp_number.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label>Overrides por purpose (JSON avanzado)</Label>
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              Configuración avanzada por tipo de magic link. Edita el JSON
              con cuidado.
            </p>

            <div className="rounded border border-fulkro-ink-300/40 bg-fulkro-ink-50/30 p-3">
              <JsonView
                value={parsedJsonForView}
                collapsed={false}
                displayDataTypes={false}
              />
            </div>

            <textarea
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                setJsonError(null);
              }}
              rows={8}
              className="w-full rounded border border-[color:var(--fulkro-surface-glass-border)] px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-fulkro-primary-500"
              spellCheck={false}
            />
            {jsonError && (
              <p className="text-xs text-fulkro-danger">{jsonError}</p>
            )}
          </div>

          <Button
            type="submit"
            disabled={form.formState.isSubmitting}
            className="self-start"
          >
            {form.formState.isSubmitting
              ? "Guardando..."
              : "Guardar notificaciones"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
