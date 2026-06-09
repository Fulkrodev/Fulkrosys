"use client";

/**
 * BrandingForm · MB-9 atom 9.2 Q6.B.
 *
 * Admin Marcos edits per-cliente brand: primary/secondary colors + footer_text.
 * Logo upload reuse existing /api/v1/clients/{id}/logo endpoint pattern
 * (out of scope for this atom · documented as follow-up).
 */
import { Loader2, Palette, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type BrandingView,
  adminDeleteLogo,
  adminGetBranding,
  adminPatchBranding,
} from "@/lib/branding/api";


interface Props {
  clientId: string;
}


const FOOTER_MAX = 500;


export function BrandingForm({ clientId }: Props) {
  const [branding, setBranding] = useState<BrandingView | null>(null);
  const [primary, setPrimary] = useState("");
  const [secondary, setSecondary] = useState("");
  const [footer, setFooter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const b = await adminGetBranding(clientId);
      setBranding(b);
      setPrimary(b.primary_color ?? "");
      setSecondary(b.secondary_color ?? "");
      setFooter(b.footer_text ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando branding");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, [clientId]);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await adminPatchBranding(clientId, {
        primary_color: primary.trim() || undefined,
        secondary_color: secondary.trim() || undefined,
        footer_text: footer.trim() || undefined,
        unset_primary: !primary.trim() && Boolean(branding?.primary_color),
        unset_secondary: !secondary.trim() && Boolean(branding?.secondary_color),
        unset_footer: !footer.trim() && Boolean(branding?.footer_text),
      });
      setBranding(updated);
      setSuccess(true);
      window.setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error guardando branding");
    } finally {
      setSaving(false);
    }
  };

  const onDeleteLogo = async () => {
    if (!branding?.has_logo) return;
    setSaving(true);
    try {
      const updated = await adminDeleteLogo(clientId);
      setBranding(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error borrando logo");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="grid place-items-center py-8 text-[color:var(--fulkro-muted)]">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  return (
    <form onSubmit={onSave} className="space-y-5" data-testid="branding-form">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-5 w-5" /> Colores corporativos
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-bold">Color primario (hex #RRGGBB)</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={primary}
                  onChange={(e) => setPrimary(e.target.value)}
                  placeholder="#1366d6"
                  pattern="^#[0-9A-Fa-f]{6}$"
                  className="flex-1 rounded-md border px-3 py-2 font-mono text-sm"
                  data-testid="branding-primary-color"
                />
                {primary.match(/^#[0-9A-Fa-f]{6}$/) && (
                  <span
                    className="h-9 w-9 rounded border"
                    style={{ background: primary }}
                    aria-label={`Vista previa ${primary}`}
                  />
                )}
              </div>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-bold">Color secundario (hex #RRGGBB)</span>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={secondary}
                  onChange={(e) => setSecondary(e.target.value)}
                  placeholder="#34a853"
                  pattern="^#[0-9A-Fa-f]{6}$"
                  className="flex-1 rounded-md border px-3 py-2 font-mono text-sm"
                  data-testid="branding-secondary-color"
                />
                {secondary.match(/^#[0-9A-Fa-f]{6}$/) && (
                  <span
                    className="h-9 w-9 rounded border"
                    style={{ background: secondary }}
                    aria-label={`Vista previa ${secondary}`}
                  />
                )}
              </div>
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Footer in-portal personalizado</CardTitle>
        </CardHeader>
        <CardContent>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-bold">Texto del pie (máx {FOOTER_MAX} caracteres)</span>
            <textarea
              value={footer}
              onChange={(e) => setFooter(e.target.value.slice(0, FOOTER_MAX))}
              rows={3}
              placeholder="Tu organización · contacto@cliente.com · datos legales"
              className="rounded-md border px-3 py-2 text-sm"
              data-testid="branding-footer-text"
            />
            <span className="self-end text-xs text-[color:var(--fulkro-muted)]">
              {footer.length} / {FOOTER_MAX}
            </span>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Logo</CardTitle>
        </CardHeader>
        <CardContent>
          {branding?.has_logo ? (
            <div className="flex items-center gap-3 text-sm">
              <span className="font-medium text-[color:var(--fulkro-body)]">
                Logo configurado · {branding.logo_mime_type ?? "imagen"}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onDeleteLogo}
                disabled={saving}
              >
                <Trash2 className="h-4 w-4" /> Eliminar logo
              </Button>
            </div>
          ) : (
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              Sin logo · subida vía endpoint /clients/{clientId}/logo (existing pattern).
            </p>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-rose-300/40 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-md border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm font-semibold text-emerald-700">
          Branding guardado correctamente.
        </div>
      )}

      <div className="flex justify-end">
        <Button type="submit" variant="primary" size="md" disabled={saving}>
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          <Save className="h-4 w-4" /> Guardar branding
        </Button>
      </div>
    </form>
  );
}
