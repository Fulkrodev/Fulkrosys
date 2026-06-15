"use client";

/**
 * #28 · Página ÚNICA de notificaciones del cliente.
 *
 * Fusiona los dos formularios que antes vivían separados en rutas distintas:
 *  - Canales + horario + resumen (PreferencesForm · MB-16.5 / ADR-039
 *    NotificationOrchestrator · email + portal SSE + ventana de silencio).
 *  - Qué avisos quieres + WhatsApp (NotificationPreferencesForm · CLUSTER 5 ·
 *    opt-outs por evento + opt-in WhatsApp · email obligatorio).
 *
 * Son complementarios (canales/horario vs qué-eventos), por eso se presentan
 * como dos secciones de una sola página. /account/notifications redirige aquí.
 * Entrada única: hub de Ajustes (#27). R29 friendly · cards sólidas (nada
 * translúcido).
 */
import { Bell } from "lucide-react";
import { useEffect, useState } from "react";

import { NotificationPreferencesForm } from "@/components/client-portal/NotificationPreferencesForm";
import { PageContainer } from "@/components/layout/PageContainer";
import { PreferencesForm } from "@/components/notifications/PreferencesForm";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getMyNotificationPreferences,
  updateMyNotificationPreferences,
} from "@/lib/notifications/api";
import type { NotificationPreference } from "@/lib/notifications/schemas";

export default function ClientNotificationSettingsPage() {
  const [preference, setPreference] = useState<NotificationPreference | null>(
    null,
  );
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMyNotificationPreferences()
      .then((p) => {
        if (!cancelled) setPreference(p);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "No se pudieron cargar las preferencias",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PageContainer variant="reading">
      <div className="space-y-6" data-testid="client-notifications-unified">
        <div className="flex items-center gap-3">
          <Bell className="h-6 w-6 text-fulkro-primary-500" aria-hidden="true" />
          <div>
            <h1 className="text-2xl font-bold text-fulkro-ink-900">Tus avisos</h1>
            <p className="text-sm text-fulkro-ink-500">
              Cómo y cuándo te avisamos, y qué avisos quieres recibir. Sin prisa
              por tu parte · cambia lo que necesites cuando lo necesites.
            </p>
          </div>
        </div>

        {/* Sección 1 · canales + horario + resumen */}
        <Card className="bg-white" data-testid="notifications-prefs-card">
          <CardHeader>
            <CardTitle>Canales y horario</CardTitle>
            <CardDescription>
              Email y avisos en el portal · tu ventana de silencio.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadError ? (
              <div
                role="alert"
                className="rounded-md bg-fulkro-danger-50 px-3 py-2 text-sm text-fulkro-danger-700"
                data-testid="prefs-load-error"
              >
                {loadError}
              </div>
            ) : preference === null ? (
              <div className="space-y-3" data-testid="prefs-loading">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <PreferencesForm
                preference={preference}
                onSave={async (update) => {
                  const updated = await updateMyNotificationPreferences(update);
                  setPreference(updated);
                  return updated;
                }}
              />
            )}
          </CardContent>
        </Card>

        {/* Sección 2 · qué avisos quieres + WhatsApp (self-loading) */}
        <NotificationPreferencesForm />
      </div>
    </PageContainer>
  );
}
