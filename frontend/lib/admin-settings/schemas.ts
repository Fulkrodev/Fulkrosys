/**
 * Zod schemas espejo de backend Pydantic AdminSettings.
 *
 * Source-of-truth contract: backend/app/admin_settings/schemas.py.
 * Drift mitigation: tests E2E (4.B.5) validan response shape vs estos
 * schemas. Si backend cambia, tests fallan visible.
 */
import { z } from "zod";

// ---------------------------------------------------------
// Branding
// ---------------------------------------------------------

export const brandingSchema = z
  .object({
    logo_url: z.string().max(500).optional().nullable(),
    primary_color: z
      .string()
      .regex(/^#[0-9A-Fa-f]{6}$/, "Color hex format #RRGGBB")
      .optional()
      .nullable(),
    secondary_color: z
      .string()
      .regex(/^#[0-9A-Fa-f]{6}$/, "Color hex format #RRGGBB")
      .optional()
      .nullable(),
    footer_text: z.string().max(500).optional().nullable(),
  })
  .strict();

export type BrandingSettings = z.infer<typeof brandingSchema>;

// ---------------------------------------------------------
// Magic Link Per Purpose Override
// ---------------------------------------------------------

export const magicLinkPurposeOverrideSchema = z
  .object({
    enabled: z.boolean().default(true),
    default_recipient_email: z.string().email().optional().nullable(),
    cc_emails: z.array(z.string().email()).optional().nullable(),
    template_id: z.string().optional().nullable(),
  })
  .strict();

export type MagicLinkPurposeOverride = z.infer<
  typeof magicLinkPurposeOverrideSchema
>;

// ---------------------------------------------------------
// Notifications
// ---------------------------------------------------------

export const notificationsSchema = z
  .object({
    client_messages_forward_enabled: z.boolean().default(true),
    client_messages_forward_to: z.string().email().optional().nullable(),
    smtp_custom: z.record(z.unknown()).optional().nullable(),
    digest_enabled: z.boolean().optional().default(false),
    digest_time_local: z
      .string()
      .regex(/^([01]\d|2[0-3]):[0-5]\d$/, "Format HH:MM")
      .default("08:00"),
    magic_link_default_sender: z.string().email().optional().nullable(),
    // #26 · WhatsApp de Marcos (E.164) editable desde el panel (antes solo env).
    marcos_whatsapp_number: z
      .string()
      .regex(/^\+?[1-9]\d{6,14}$/, "Número E.164, ej. +34637165328")
      .optional()
      .nullable(),
    magic_link_per_purpose_overrides: z
      .record(magicLinkPurposeOverrideSchema)
      .optional()
      .nullable(),
  })
  .strict();

export type NotificationsSettings = z.infer<typeof notificationsSchema>;

// ---------------------------------------------------------
// SMTP (plan v4.2 tarea 4.20 literal: 4 fields editables)
// ---------------------------------------------------------

export const smtpSchema = z
  .object({
    host: z.string().max(255).optional().nullable(),
    port: z.number().int().min(1).max(65535).optional().nullable(),
    username: z.string().max(255).optional().nullable(),
    password: z.string().max(500).optional().nullable(),
  })
  .strict();

export type SmtpSettings = z.infer<typeof smtpSchema>;

// ---------------------------------------------------------
// General
// ---------------------------------------------------------

export const generalSchema = z
  .object({
    timezone: z.string().default("Europe/Madrid"),
    locale: z
      .string()
      .regex(/^[a-z]{2}-[A-Z]{2}$/, "Format ll-CC")
      .default("es-ES"),
    date_format: z.string().default("DD/MM/YYYY"),
  })
  .strict();

export type GeneralSettings = z.infer<typeof generalSchema>;

// ---------------------------------------------------------
// Analytics Prefs
// ---------------------------------------------------------

export const analyticsPrefsSchema = z
  .object({
    show_corpus_metric: z.boolean().default(true),
  })
  .strict();

export type AnalyticsPrefs = z.infer<typeof analyticsPrefsSchema>;

// ---------------------------------------------------------
// Fiscal (identidad fiscal del emisor/consultor · punto #44)
// ---------------------------------------------------------

export const fiscalSchema = z
  .object({
    nif: z.string().max(20).optional().nullable(),
    nombre_fiscal: z.string().max(200).optional().nullable(),
    nombre_comercial: z.string().max(200).optional().nullable(),
    tipo_persona: z.enum(["F", "J"]).default("F"),
    domicilio_via: z.string().max(250).optional().nullable(),
    domicilio_cp: z.string().max(10).optional().nullable(),
    domicilio_municipio: z.string().max(120).optional().nullable(),
    domicilio_provincia: z.string().max(120).optional().nullable(),
    domicilio_pais: z.string().max(80).default("España"),
    iva_pct: z.number().min(0).max(100).default(21),
    sujeto_irpf: z.boolean().default(true),
    irpf_pct: z.number().min(0).max(100).default(15),
    iban: z.string().max(34).optional().nullable(),
    bank_holder: z.string().max(200).optional().nullable(),
    bank_institution: z.string().max(120).optional().nullable(),
    bank_bic: z.string().max(11).optional().nullable(),
  })
  .strict();

export type FiscalSettings = z.infer<typeof fiscalSchema>;

// ---------------------------------------------------------
// AdminSettings Response (full)
// ---------------------------------------------------------

export const adminSettingsResponseSchema = z.object({
  id: z.string().uuid(),
  branding: brandingSchema,
  notifications: notificationsSchema,
  smtp: smtpSchema,
  general: generalSchema,
  analytics_prefs: analyticsPrefsSchema,
  fiscal: fiscalSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime().nullable(),
});

export type AdminSettingsResponse = z.infer<typeof adminSettingsResponseSchema>;

// ---------------------------------------------------------
// About (read-only stats)
// ---------------------------------------------------------

export const adminSettingsAboutSchema = z.object({
  version: z.string(),
  commit_hash: z.string(),
  uptime_days: z.number(),
  active_clients_count: z.number(),
  corpus_sources_count: z.number(),
  corpus_sources_target: z.number(),
  corpus_chunks_total: z.number(),
  corpus_last_updated: z.string().datetime().nullable(),
  corpus_completion_pct: z.number(),
  // S24: suite_passing / test_loc_ratio_avg eliminados (vanity metrics fabricadas).
});

export type AdminSettingsAbout = z.infer<typeof adminSettingsAboutSchema>;

// ---------------------------------------------------------
// SMTP Test (commit fb68d16)
// ---------------------------------------------------------

export const smtpTestRequestSchema = z
  .object({
    use_admin_settings: z.boolean().default(true),
    override_host: z.string().max(255).optional().nullable(),
    override_port: z.number().int().min(1).max(65535).optional().nullable(),
    override_username: z.string().max(255).optional().nullable(),
    override_password: z.string().max(500).optional().nullable(),
  })
  .strict();

export type SmtpTestRequest = z.infer<typeof smtpTestRequestSchema>;

export const smtpTestResponseSchema = z.object({
  ok: z.boolean(),
  sent_to: z.string(),
  backend_used: z.string(),
  error: z.string().optional().nullable(),
});

export type SmtpTestResponse = z.infer<typeof smtpTestResponseSchema>;
