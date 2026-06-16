/**
 * MagicLinkGenerator · formulario admin para generar magic links nuevos.
 *
 * FASE 4.5 sub-bloque B.2 · POST /api/v1/magic-links/generate.
 *
 * Stack:
 *   - React Hook Form + Zod (validación client-side)
 *   - useGenerateMagicLink mutation (real backend · sin mocks)
 *   - shadcn/ui (Card / Input / Select / Textarea / Switch)
 *   - ContactQuickPicker M30 (SAN-B.MB-6.4 · FASE 9 cierre)
 *   - fulkroToast para feedback
 *
 * SAN-B.MB-6.4: ContactPicker integrado · selector contacto M30 autopopula
 * recipient_email + sent_to_contact_id (FK BD). Manual entry preserved
 * vía edición directa del input email después de selección.
 * El client_id es input UUID por ahora (futuro: combobox clientes activos).
 */
"use client";

import * as React from "react";
import { Copy, Loader2, Send } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { ContactQuickPicker } from "@/components/admin-clients/contacts/ContactQuickPicker";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

import {
  useGenerateAndSendMagicLink,
  useGenerateMagicLink,
} from "@/hooks/magic-link";
import { listContacts } from "@/lib/admin-contacts/api";
import {
  MAGIC_LINK_BACKEND_CATEGORIES,
  MAGIC_LINK_BACKEND_LABELS,
  MAGIC_LINK_BACKEND_PURPOSES,
  type GenerateAndSendMagicLinkResponse,
  type GenerateMagicLinkRequest,
  type MagicLinkBackendPurpose,
  type MagicLinkRecord,
} from "@/lib/magic-link-types";
import { fulkroToast } from "@/lib/toast";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const schema = z.object({
  project_id: z.string().regex(UUID_RE, "UUID requerido"),
  client_id: z.string().regex(UUID_RE, "UUID requerido"),
  purpose: z.enum(MAGIC_LINK_BACKEND_PURPOSES),
  recipient_email: z.string().email("Email no válido"),
  sent_to_contact_id: z.string().regex(UUID_RE).optional(),
  scope_json: z
    .string()
    .default("{}")
    .refine((v) => {
      try {
        const parsed = JSON.parse(v || "{}");
        return parsed && typeof parsed === "object" && !Array.isArray(parsed);
      } catch {
        return false;
      }
    }, "Debe ser un objeto JSON válido"),
  ttl_hours: z
    .union([z.string().length(0), z.coerce.number().int().positive()])
    .optional(),
  max_uses: z
    .union([z.string().length(0), z.coerce.number().int().positive()])
    .optional(),
  cc_emails: z.string().optional(),
  custom_subject: z.string().max(255).optional(),
  custom_body_intro: z.string().max(5000).optional(),
});

type FormValues = z.infer<typeof schema>;

const VISIBLE_CATEGORIES: ReadonlyArray<string> = Object.keys(
  MAGIC_LINK_BACKEND_CATEGORIES,
).filter((k) => k !== "Deprecated");

export function MagicLinkGenerator() {
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const [generated, setGenerated] = React.useState<MagicLinkRecord | null>(
    null,
  );
  const [sent, setSent] =
    React.useState<GenerateAndSendMagicLinkResponse | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { scope_json: "{}" },
  });

  const generate = useGenerateMagicLink();
  const generateAndSend = useGenerateAndSendMagicLink();

  function buildPayload(values: FormValues): GenerateMagicLinkRequest {
    const ccArray = values.cc_emails
      ? values.cc_emails
          .split(/[,;]/)
          .map((e) => e.trim())
          .filter(Boolean)
      : undefined;
    return {
      project_id: values.project_id,
      purpose: values.purpose,
      recipient_email: values.recipient_email,
      sent_to_contact_id: values.sent_to_contact_id || undefined,
      scope: JSON.parse(values.scope_json || "{}"),
      ttl_hours: typeof values.ttl_hours === "number" ? values.ttl_hours : undefined,
      max_uses: typeof values.max_uses === "number" ? values.max_uses : undefined,
      cc_emails: ccArray,
      custom_subject: values.custom_subject || undefined,
      custom_body_intro: values.custom_body_intro || undefined,
    };
  }

  async function onSubmit(values: FormValues) {
    try {
      const result = await generate.mutateAsync(buildPayload(values));
      setGenerated(result);
      setSent(null);
      // Honesto: /generate sólo crea el enlace · el envío real es el otro botón.
      fulkroToast.success("Enlace generado", {
        description: `Listo para ${values.recipient_email} · copia el enlace o usa "Generar y enviar".`,
      });
      form.reset({ scope_json: "{}" });
    } catch (err) {
      fulkroToast.error("No se pudo generar el enlace", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  async function onSubmitAndSend(values: FormValues) {
    try {
      const result = await generateAndSend.mutateAsync(buildPayload(values));
      setSent(result);
      setGenerated(null);
      if (result.email_sent) {
        fulkroToast.success("Enlace generado y enviado", {
          description: `Email enviado a ${result.recipient_email}.`,
        });
        form.reset({ scope_json: "{}" });
      } else {
        fulkroToast.warning("Enlace generado · email NO enviado", {
          description:
            result.email_error ??
            "Revisa la configuración de email (backend de envío).",
        });
      }
    } catch (err) {
      fulkroToast.error("No se pudo generar/enviar el enlace", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  function copyId() {
    if (!generated) return;
    void navigator.clipboard.writeText(generated.id);
    fulkroToast.success("ID copiado al portapapeles");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Generar enlace seguro</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="project_id">Proyecto (UUID)</Label>
              <Input
                id="project_id"
                placeholder="00000000-0000-0000-0000-000000000000"
                {...form.register("project_id")}
              />
              {form.formState.errors.project_id ? (
                <p className="text-xs text-destructive">
                  {form.formState.errors.project_id.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="client_id">Cliente (UUID)</Label>
              <Input
                id="client_id"
                placeholder="00000000-0000-0000-0000-000000000000"
                {...form.register("client_id")}
              />
              {form.formState.errors.client_id ? (
                <p className="text-xs text-destructive">
                  {form.formState.errors.client_id.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="purpose">Tipo de operación</Label>
            <Select
              onValueChange={(v) =>
                form.setValue("purpose", v as MagicLinkBackendPurpose, {
                  shouldValidate: true,
                })
              }
              value={form.watch("purpose")}
            >
              <SelectTrigger id="purpose">
                <SelectValue placeholder="Selecciona el tipo de enlace…" />
              </SelectTrigger>
              <SelectContent>
                {VISIBLE_CATEGORIES.map((cat) => (
                  <SelectGroup key={cat}>
                    <SelectLabel>{cat}</SelectLabel>
                    {MAGIC_LINK_BACKEND_CATEGORIES[cat].map((p) => (
                      <SelectItem key={p} value={p}>
                        {MAGIC_LINK_BACKEND_LABELS[p]}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.purpose ? (
              <p className="text-xs text-destructive">
                Selecciona un tipo de operación
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label>Contacto M30 (autopopula email + FK)</Label>
            <ContactQuickPicker
              clientId={form.watch("client_id") || ""}
              value={form.watch("sent_to_contact_id") || null}
              onChange={(contactId) => {
                form.setValue("sent_to_contact_id", contactId || undefined, {
                  shouldValidate: false,
                });
                if (!contactId) {
                  return;
                }
                // Autofill recipient_email desde Contact seleccionado
                const cid = form.getValues("client_id");
                if (!cid) return;
                listContacts(cid, { is_active: true })
                  .then((contacts) => {
                    const c = contacts.find((x) => x.id === contactId);
                    if (c) {
                      form.setValue("recipient_email", c.email, {
                        shouldValidate: true,
                      });
                    }
                  })
                  .catch(() => {
                    // silent · email manual fallback queda accesible
                  });
              }}
              placeholder="Selecciona contacto M30 (opcional)…"
              disabled={!form.watch("client_id")}
            />
            <Label htmlFor="recipient_email">Email destinatario</Label>
            <Input
              id="recipient_email"
              type="email"
              placeholder="contacto@cliente.com (autopopula al picar contacto)"
              {...form.register("recipient_email")}
            />
            {form.formState.errors.recipient_email ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.recipient_email.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="scope_json">Scope (JSON)</Label>
            <Textarea
              id="scope_json"
              rows={3}
              placeholder='{ "propuesta_codigo": "P-001-2026" }'
              className="font-mono text-xs"
              {...form.register("scope_json")}
            />
            {form.formState.errors.scope_json ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.scope_json.message}
              </p>
            ) : null}
          </div>

          <div className="flex items-center justify-between rounded-md border border-fulkro-ink-300/60 px-3 py-2">
            <Label htmlFor="advanced-toggle" className="cursor-pointer">
              Personalización avanzada
            </Label>
            <Switch
              id="advanced-toggle"
              checked={showAdvanced}
              onCheckedChange={setShowAdvanced}
            />
          </div>

          {showAdvanced ? (
            <div className="space-y-4 rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/30 p-4">
              <div className="space-y-1.5">
                <Label htmlFor="cc_emails">CC emails (separar por coma)</Label>
                <Input
                  id="cc_emails"
                  placeholder="legal@cliente.com, compras@cliente.com"
                  {...form.register("cc_emails")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="custom_subject">Subject custom</Label>
                <Input
                  id="custom_subject"
                  placeholder="(opcional · sobreescribe el default)"
                  {...form.register("custom_subject")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="custom_body_intro">Cuerpo personalizado</Label>
                <Textarea
                  id="custom_body_intro"
                  rows={3}
                  placeholder="(opcional · texto antes del template)"
                  {...form.register("custom_body_intro")}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="ttl_hours">TTL (horas) override</Label>
                  <Input
                    id="ttl_hours"
                    type="number"
                    min={1}
                    placeholder="Default per purpose"
                    {...form.register("ttl_hours")}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="max_uses">Max usos override</Label>
                  <Input
                    id="max_uses"
                    type="number"
                    min={1}
                    placeholder="Default per purpose"
                    {...form.register("max_uses")}
                  />
                </div>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              type="submit"
              size="lg"
              variant="outline"
              className="w-full"
              disabled={generate.isPending || generateAndSend.isPending}
            >
              {generate.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Copy size={14} />
              )}
              Generar (copiar enlace)
            </Button>
            <Button
              type="button"
              size="lg"
              className="w-full"
              disabled={generate.isPending || generateAndSend.isPending}
              onClick={form.handleSubmit(onSubmitAndSend)}
            >
              {generateAndSend.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              Generar y enviar por email
            </Button>
          </div>
        </form>

        {generated ? (
          <Alert variant="success" className="mt-6">
            <AlertTitle>Enlace generado</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
                ID: <span className="font-mono">{generated.id}</span>
              </p>
              <p className="text-xs">
                Caduca el {new Date(generated.expira_at).toLocaleString("es-ES")}{" "}
                · {generated.usos}/{generated.max_usos ?? 1} usos.
              </p>
              <Button variant="outline" size="sm" onClick={copyId} type="button">
                <Copy size={12} /> Copiar ID
              </Button>
              <p className="text-[11px] text-fulkro-ink-500">
                Registrado en client_interactions audit trail.
              </p>
            </AlertDescription>
          </Alert>
        ) : null}

        {sent ? (
          <Alert
            variant={sent.email_sent ? "success" : "danger"}
            className="mt-6"
            data-testid="ml-send-result"
          >
            <AlertTitle>
              {sent.email_sent
                ? "Enlace generado y enviado por email"
                : "Enlace generado · email NO enviado"}
            </AlertTitle>
            <AlertDescription className="space-y-2">
              <p className="text-xs">
                Destinatario:{" "}
                <span className="font-mono">{sent.recipient_email}</span>
              </p>
              {sent.email_sent ? (
                <p className="text-xs">
                  Backend de envío:{" "}
                  <span className="font-mono">{sent.email_backend}</span>
                  {sent.email_message_id
                    ? ` · id ${sent.email_message_id}`
                    : ""}
                </p>
              ) : (
                <p className="text-xs">
                  {sent.email_error ??
                    "No se pudo enviar · revisa la configuración de email."}
                </p>
              )}
              {sent.otp ? (
                <p className="text-xs font-medium text-fulkro-warning">
                  Código OTP: <span className="font-mono">{sent.otp}</span> ·
                  entrégalo al destinatario por un canal SEPARADO (SMS/teléfono).
                  No se ha incluido en el email del enlace.
                </p>
              ) : null}
              <p className="text-[11px] text-fulkro-ink-500">
                Caduca el{" "}
                {new Date(sent.expires_at).toLocaleString("es-ES")} · registrado
                en email_log + audit trail.
              </p>
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
