/**
 * React hook AdminSettings: fetch + cache + revalidate post-PATCH.
 *
 * Pattern simple useState + useEffect (no react-query overhead para
 * 1 endpoint singleton). Revalidación manual via refetch o consumo
 * directo del response retornado por updateSection (que ya viene
 * con AdminSettings entero post-PATCH).
 */
"use client";
import * as React from "react";

import { ApiError } from "@/lib/api";

import {
  getAdminSettings,
  patchAdminSettingsSection,
} from "./api";
import type {
  AdminSettingsResponse,
  AnalyticsPrefs,
  BrandingSettings,
  FiscalSettings,
  GeneralSettings,
  NotificationsSettings,
  SmtpSettings,
} from "./schemas";

type SectionName =
  | "branding"
  | "notifications"
  | "smtp"
  | "general"
  | "analytics_prefs"
  | "fiscal";

type SectionPayload = {
  branding: BrandingSettings;
  notifications: NotificationsSettings;
  smtp: SmtpSettings;
  general: GeneralSettings;
  analytics_prefs: AnalyticsPrefs;
  fiscal: FiscalSettings;
};

export function useAdminSettings() {
  const [data, setData] = React.useState<AdminSettingsResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const refetch = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminSettings();
      setData(result);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error desconocido al cargar ajustes",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refetch();
  }, [refetch]);

  const updateSection = React.useCallback(
    async <S extends SectionName>(
      section: S,
      payload: SectionPayload[S],
    ): Promise<AdminSettingsResponse> => {
      const result = await patchAdminSettingsSection(section, payload);
      setData(result);
      return result;
    },
    [],
  );

  return {
    data,
    loading,
    error,
    refetch,
    updateSection,
  };
}
