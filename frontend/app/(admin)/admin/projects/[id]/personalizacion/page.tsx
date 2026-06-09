"use client";

/**
 * Admin Personalización per project · sub-atom 1.E.2.bis Phase D.
 *
 * Branding live preview · reuse admin_branding_api (M21) endpoints
 * existing. Cliente-level (per ADR-054 Phase 0 decision · piloto MEDIA
 * 1 cliente ≈ 1 proyecto típico · capability per-project Future demand-driven).
 *
 * Cambios afectan portal cliente (PortalLayout consume client branding).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Palette, Save, Trash2 } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type BrandingView,
  deleteClientLogo,
  getClientBranding,
  patchClientBranding,
} from "@/lib/api/personalizacion-admin";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

const HEX_RE = /^#[0-9A-Fa-f]{6}$/;
const DEFAULT_PRIMARY = "#0B5394";
const DEFAULT_SECONDARY = "#6CADDF";

export default function ProjectPersonalizacionPage() {
  const activeProject = useActiveProjectStore((s) => s.activeProject);
  const clientId = activeProject?.clientId ?? "";
  const queryClient = useQueryClient();

  const brandingQuery = useQuery({
    queryKey: ["client-branding", clientId],
    queryFn: () => getClientBranding(clientId),
    enabled: Boolean(clientId),
    staleTime: 60_000,
  });

  if (!clientId) {
    return (
      <Alert variant="info">
        <AlertTitle>Cargando proyecto…</AlertTitle>
        <AlertDescription>
          Esperando contexto del proyecto activo para mostrar
          personalización.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div
      className="flex flex-col gap-5"
      data-testid="project-personalizacion-page"
    >
      <header>
        <h2 className="text-xl font-semibold text-fulkro-primary-700">
          Personalización del portal cliente
        </h2>
        <p className="text-sm text-fulkro-ink-600">
          Configura cómo se ve el portal para{" "}
          <span className="font-semibold">{activeProject?.clientName}</span>:
          colores corporativos + texto del pie. Los cambios se aplican
          automáticamente cuando el cliente entra al portal.
        </p>
      </header>

      {brandingQuery.isLoading ? (
        <Card>
          <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
            <Loader2 size={14} className="animate-spin" /> cargando…
          </CardContent>
        </Card>
      ) : brandingQuery.isError ? (
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar la personalización</AlertTitle>
          <AlertDescription>
            {brandingQuery.error instanceof Error
              ? brandingQuery.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : brandingQuery.data ? (
        <BrandingForm
          initial={brandingQuery.data}
          clientId={clientId}
          onAfterSave={() =>
            queryClient.invalidateQueries({
              queryKey: ["client-branding", clientId],
            })
          }
        />
      ) : null}
    </div>
  );
}

function BrandingForm({
  initial,
  clientId,
  onAfterSave,
}: {
  initial: BrandingView;
  clientId: string;
  onAfterSave: () => void;
}) {
  const [primary, setPrimary] = React.useState(initial.primary_color ?? "");
  const [secondary, setSecondary] = React.useState(initial.secondary_color ?? "");
  const [footer, setFooter] = React.useState(initial.footer_text ?? "");

  const saveMut = useMutation({
    mutationFn: () =>
      patchClientBranding(clientId, {
        primary_color: primary || null,
        secondary_color: secondary || null,
        footer_text: footer || null,
        unset_primary: primary === "",
        unset_secondary: secondary === "",
        unset_footer: footer === "",
      }),
    onSuccess: () => {
      toast.success("Personalización guardada");
      onAfterSave();
    },
    onError: (err: Error) => toast.error(`Guardar falló: ${err.message}`),
  });

  const deleteLogoMut = useMutation({
    mutationFn: () => deleteClientLogo(clientId),
    onSuccess: () => {
      toast.success("Logo eliminado");
      onAfterSave();
    },
    onError: (err: Error) =>
      toast.error(`No se pudo eliminar logo: ${err.message}`),
  });

  const primaryValid = primary === "" || HEX_RE.test(primary);
  const secondaryValid = secondary === "" || HEX_RE.test(secondary);
  const footerValid = footer.length <= 500;
  const canSubmit =
    primaryValid && secondaryValid && footerValid && !saveMut.isPending;

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette size={14} /> Branding
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="primary-color">Color principal (HEX)</Label>
            <Input
              id="primary-color"
              type="text"
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
              placeholder={DEFAULT_PRIMARY}
              disabled={saveMut.isPending}
              aria-invalid={!primaryValid}
              data-testid="primary-color-input"
            />
            {!primaryValid ? (
              <p className="text-xs text-fulkro-danger">
                Debe ser hex #RRGGBB
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="secondary-color">Color secundario (HEX)</Label>
            <Input
              id="secondary-color"
              type="text"
              value={secondary}
              onChange={(e) => setSecondary(e.target.value)}
              placeholder={DEFAULT_SECONDARY}
              disabled={saveMut.isPending}
              aria-invalid={!secondaryValid}
              data-testid="secondary-color-input"
            />
            {!secondaryValid ? (
              <p className="text-xs text-fulkro-danger">
                Debe ser hex #RRGGBB
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="footer-text">Texto pie de portal</Label>
            <Input
              id="footer-text"
              type="text"
              value={footer}
              onChange={(e) => setFooter(e.target.value)}
              placeholder="© Cliente · 2026"
              disabled={saveMut.isPending}
              maxLength={500}
              data-testid="footer-text-input"
            />
            <p className="text-[10px] text-fulkro-ink-500">
              {footer.length} / 500
            </p>
          </div>

          <div className="flex flex-col gap-2 border-t border-fulkro-ink-100 pt-3">
            <Label className="text-xs uppercase tracking-wider text-fulkro-ink-500">
              Logo cliente
            </Label>
            {initial.has_logo ? (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-fulkro-ink-600">
                  Logo configurado · {initial.logo_mime_type ?? "imagen"}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => deleteLogoMut.mutate()}
                  disabled={deleteLogoMut.isPending}
                  data-testid="delete-logo-button"
                >
                  <Trash2 size={11} />
                  Eliminar
                </Button>
              </div>
            ) : (
              <p className="text-xs italic text-fulkro-ink-500">
                Sin logo · subir desde el panel del cliente
                (/admin/clients/{clientId.slice(0, 8)}…).
              </p>
            )}
          </div>

          <Button
            type="button"
            variant="primary"
            disabled={!canSubmit}
            onClick={() => saveMut.mutate()}
            data-testid="personalizacion-save"
          >
            {saveMut.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Save size={13} />
            )}
            Guardar cambios
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Vista previa</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="rounded-lg border border-fulkro-ink-200 bg-white p-4"
            data-testid="branding-preview"
          >
            <div
              className="mb-3 flex items-center gap-3 rounded-md px-4 py-3 text-white"
              style={{
                background:
                  (primaryValid && primary) || DEFAULT_PRIMARY,
              }}
            >
              <div
                className="h-3 w-3 rounded-full"
                style={{
                  background:
                    (secondaryValid && secondary) || DEFAULT_SECONDARY,
                }}
              />
              <span className="text-sm font-semibold">
                Portal {initial.client_id.slice(0, 8)}
              </span>
            </div>
            <div className="space-y-1.5 text-xs text-fulkro-ink-700">
              <p>Documentos firmados · Evidencias · Conformidad</p>
              <p className="text-fulkro-ink-500">
                Pie:{" "}
                <span className="italic">
                  {footer || "(sin texto definido)"}
                </span>
              </p>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-fulkro-ink-500">
            La vista previa muestra cómo verá el cliente la cabecera del
            portal. Los cambios se aplican al guardar.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
