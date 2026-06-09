"use client";

/**
 * NotificationPreferencesForm · cliente notification preferences UI
 * (CLUSTER 5 Phase 5E delta).
 *
 * Cliente toggles WhatsApp opt-in (granular sobre m31 OTP opt-in) +
 * per-event opt-outs (chat replies · phase changes · evidence expiring).
 * Email mandatory (legal/binding · grayed-out toggle disabled).
 *
 * R29 cliente friendly · "Sin presión por tu parte" · NO admin lingo ·
 * "Avísame cuando..." copy.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  NotificationPreferences,
  notificationPreferencesApi,
} from "@/lib/api/notification-preferences";

const EVENT_OPT_OUT_OPTIONS: Array<{ key: string; label: string }> = [
  {
    key: "chat_admin_reply",
    label: "Avisarme cuando Marcos responda en el chat",
  },
  {
    key: "phase_changed",
    label: "Avisarme cuando pasemos de fase del proyecto",
  },
  {
    key: "evidence_expiring",
    label: "Avisarme cuando una evidencia esté por caducar",
  },
  {
    key: "audit_due",
    label: "Avisarme cuando se acerque una auditoría",
  },
  {
    key: "milestone_billed",
    label: "Avisarme cuando haya un hito facturado",
  },
];

export function NotificationPreferencesForm() {
  const queryClient = useQueryClient();
  const { data: prefs, isLoading } = useQuery<NotificationPreferences>({
    queryKey: ["client-notification-preferences"],
    queryFn: () => notificationPreferencesApi.get(),
  });

  const [whatsappEnabled, setWhatsappEnabled] = useState(false);
  const [optOuts, setOptOuts] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (prefs) {
      setWhatsappEnabled(prefs.whatsapp_enabled);
      setOptOuts(prefs.event_opt_outs ?? {});
    }
  }, [prefs]);

  const updateMutation = useMutation({
    mutationFn: () =>
      notificationPreferencesApi.update({
        whatsapp_enabled: whatsappEnabled,
        event_opt_outs: optOuts,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["client-notification-preferences"],
      });
    },
  });

  if (isLoading || !prefs) {
    return (
      <Card>
        <CardContent
          className="flex items-center gap-2 p-6 text-sm text-muted-foreground"
          data-testid="prefs-loading"
        >
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando ajustes…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="prefs-form-active">
      <Card>
        <CardHeader>
          <CardTitle>Canales de aviso</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ToggleRow
            label="Email"
            description="Avisos importantes y resúmenes · obligatorio para temas legales y firmas"
            checked={prefs.email_enabled}
            disabled
            testId="prefs-email-toggle"
          />
          <ToggleRow
            label="Avisos dentro del portal"
            description="Inbox interno con tus mensajes y tareas"
            checked={prefs.portal_sse_enabled}
            disabled
            testId="prefs-portal-toggle"
          />
          <ToggleRow
            label="WhatsApp"
            description="Sin presión · te avisamos sólo cuando Marcos te escribe o hay algo urgente"
            checked={whatsappEnabled}
            onChange={setWhatsappEnabled}
            testId="prefs-whatsapp-toggle"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>¿Qué te avisamos?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Marca lo que quieras silenciar · sin presión por tu parte.
          </p>
          {EVENT_OPT_OUT_OPTIONS.map((opt) => (
            <ToggleRow
              key={opt.key}
              label={opt.label}
              description=""
              checked={!optOuts[opt.key]}
              onChange={(next) =>
                setOptOuts((prev) => ({ ...prev, [opt.key]: !next }))
              }
              testId={`prefs-event-${opt.key}`}
            />
          ))}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={() => updateMutation.mutate()}
          disabled={updateMutation.isPending}
          data-testid="prefs-save"
        >
          {updateMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : null}
          Guardar preferencias
        </Button>
      </div>
    </div>
  );
}

interface ToggleRowProps {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange?: (next: boolean) => void;
  testId?: string;
}

function ToggleRow({
  label,
  description,
  checked,
  disabled,
  onChange,
  testId,
}: ToggleRowProps) {
  return (
    <label
      className="flex items-start gap-3 cursor-pointer"
      data-testid={testId}
    >
      <input
        type="checkbox"
        className="mt-1 h-4 w-4"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.checked)}
        aria-label={label}
      />
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description ? (
          <p className="text-xs text-muted-foreground">{description}</p>
        ) : null}
      </div>
    </label>
  );
}
