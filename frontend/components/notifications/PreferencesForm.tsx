"use client";

/**
 * Notification preferences form cliente (MB-16.5 ADR-039).
 *
 * Permite cliente configurar:
 * - email_enabled / portal_sse_enabled toggles
 * - dnd_start_local / dnd_end_local ventana DND tz-aware
 * - timezone IANA name (Europe/Madrid default)
 * - digest_mode (immediate MVP · hourly/daily diferidos)
 */
import { Bell, Clock, Mail, Save } from "lucide-react";
import { useState } from "react";

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
import { Switch } from "@/components/ui/switch";

import type {
  DigestMode,
  NotificationPreference,
  NotificationPreferenceUpdate,
} from "@/lib/notifications/schemas";
import { DIGEST_MODES } from "@/lib/notifications/schemas";

const TIMEZONE_OPTIONS = [
  "Europe/Madrid",
  "Europe/Lisbon",
  "Europe/London",
  "Europe/Paris",
  "America/Mexico_City",
  "America/New_York",
  "UTC",
];

interface PreferencesFormProps {
  preference: NotificationPreference;
  onSave: (
    update: NotificationPreferenceUpdate,
  ) => Promise<NotificationPreference>;
}

export function PreferencesForm({ preference, onSave }: PreferencesFormProps) {
  const [emailEnabled, setEmailEnabled] = useState(preference.email_enabled);
  const [sseEnabled, setSseEnabled] = useState(preference.portal_sse_enabled);
  const [dndStart, setDndStart] = useState(
    preference.dnd_start_local ?? "",
  );
  const [dndEnd, setDndEnd] = useState(preference.dnd_end_local ?? "");
  const [timezone, setTimezone] = useState(preference.timezone);
  const [digestMode, setDigestMode] = useState<DigestMode>(
    preference.digest_mode,
  );
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    const dndConfigured = dndStart.trim() !== "" || dndEnd.trim() !== "";
    if (
      dndConfigured &&
      (dndStart.trim() === "" || dndEnd.trim() === "")
    ) {
      setError(
        "Si configuras la ventana de silencio, define ambos: hora de inicio y hora de fin.",
      );
      setSaving(false);
      return;
    }

    try {
      await onSave({
        email_enabled: emailEnabled,
        portal_sse_enabled: sseEnabled,
        dnd_start_local: dndStart.trim() === "" ? null : dndStart.trim(),
        dnd_end_local: dndEnd.trim() === "" ? null : dndEnd.trim(),
        timezone,
        digest_mode: digestMode,
      });
      setSuccess(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudieron guardar las preferencias",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSave}
      className="space-y-6"
      data-testid="notifications-preferences-form"
    >
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-fulkro-ink-700">
          Canales de notificación
        </h3>
        <div className="flex items-start justify-between gap-4">
          <Label
            htmlFor="email_enabled"
            className="flex flex-col gap-1 cursor-pointer"
          >
            <span className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-fulkro-primary-500" />
              Email
            </span>
            <span className="text-xs text-fulkro-ink-500 font-normal">
              Recibirás un email para cada notificación importante.
            </span>
          </Label>
          <Switch
            id="email_enabled"
            checked={emailEnabled}
            onCheckedChange={setEmailEnabled}
            data-testid="toggle-email-enabled"
          />
        </div>
        <div className="flex items-start justify-between gap-4">
          <Label
            htmlFor="sse_enabled"
            className="flex flex-col gap-1 cursor-pointer"
          >
            <span className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-fulkro-primary-500" />
              Notificaciones en el portal (in-app)
            </span>
            <span className="text-xs text-fulkro-ink-500 font-normal">
              Verás un aviso instantáneo cuando estés conectado al portal.
            </span>
          </Label>
          <Switch
            id="sse_enabled"
            checked={sseEnabled}
            onCheckedChange={setSseEnabled}
            data-testid="toggle-sse-enabled"
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-fulkro-ink-700 flex items-center gap-2">
          <Clock className="h-4 w-4 text-fulkro-primary-500" />
          Ventana de silencio (No molestar)
        </h3>
        <p className="text-xs text-fulkro-ink-500">
          Durante este horario no recibirás emails. Usa formato 24h
          (ej. 22:00 → 08:00). Deja ambos campos vacíos para desactivar.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1">
            <Label htmlFor="dnd_start">Inicio (HH:MM)</Label>
            <Input
              id="dnd_start"
              type="time"
              value={dndStart}
              onChange={(e) => setDndStart(e.target.value)}
              placeholder="22:00"
              data-testid="input-dnd-start"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="dnd_end">Fin (HH:MM)</Label>
            <Input
              id="dnd_end"
              type="time"
              value={dndEnd}
              onChange={(e) => setDndEnd(e.target.value)}
              placeholder="08:00"
              data-testid="input-dnd-end"
            />
          </div>
        </div>
        <div className="space-y-1">
          <Label htmlFor="timezone">Zona horaria</Label>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger
              id="timezone"
              data-testid="select-timezone"
              className="w-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONE_OPTIONS.map((tz) => (
                <SelectItem key={tz} value={tz}>
                  {tz}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-fulkro-ink-700">
          Frecuencia
        </h3>
        <div className="space-y-1">
          <Label htmlFor="digest_mode">Modo</Label>
          <Select
            value={digestMode}
            onValueChange={(v) => setDigestMode(v as DigestMode)}
          >
            <SelectTrigger
              id="digest_mode"
              data-testid="select-digest-mode"
              className="w-full"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DIGEST_MODES.map((mode) => (
                <SelectItem
                  key={mode}
                  value={mode}
                  disabled={mode !== "immediate"}
                >
                  {mode === "immediate"
                    ? "Inmediata (cada notificación al instante)"
                    : mode === "hourly"
                      ? "Resumen horario · próximamente"
                      : "Resumen diario · próximamente"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-fulkro-ink-500">
            Por ahora solo está disponible el modo inmediato. Los resúmenes
            agrupados llegarán en una próxima versión.
          </p>
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-md bg-fulkro-danger-50 px-3 py-2 text-sm text-fulkro-danger-700"
          data-testid="prefs-error"
        >
          {error}
        </div>
      ) : null}
      {success ? (
        <div
          role="status"
          className="rounded-md bg-fulkro-success-50 px-3 py-2 text-sm text-fulkro-success-700"
          data-testid="prefs-success"
        >
          Preferencias guardadas correctamente.
        </div>
      ) : null}

      <Button
        type="submit"
        disabled={saving}
        data-testid="btn-save-prefs"
        className="w-full sm:w-auto"
      >
        <Save className="mr-2 h-4 w-4" />
        {saving ? "Guardando..." : "Guardar preferencias"}
      </Button>
    </form>
  );
}
