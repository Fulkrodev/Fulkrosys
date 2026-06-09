"use client";

/**
 * Pricing tab · fuente única editable de precios base ENS (FIX P4-1).
 *
 * Lee/edita pricing_config vía /api/v1/admin/settings/pricing. Al guardar, los
 * nuevos precios se reflejan en cotizaciones, facturas y propuestas.
 */
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  getPricing,
  updatePricing,
  type PricingConfigItem,
} from "@/lib/admin-settings/api";

const ORDER = ["BASICA", "MEDIA", "ALTA"] as const;
const LABELS: Record<string, string> = {
  BASICA: "Básica",
  MEDIA: "Media",
  ALTA: "Alta",
};

export function PricingTab() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getPricing();
      setValues(
        Object.fromEntries(
          data.map((r) => [r.categoria, String(r.precio_proyecto)]),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar precios");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payload: Record<string, number> = {};
      for (const cat of ORDER) {
        const n = Number(values[cat]);
        if (!Number.isNaN(n) && n > 0) payload[cat] = n;
      }
      const data = await updatePricing(payload);
      setValues(
        Object.fromEntries(
          data.map((r: PricingConfigItem) => [
            r.categoria,
            String(r.precio_proyecto),
          ]),
        ),
      );
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <p className="text-sm text-[color:var(--fulkro-muted)]">
        Cargando precios…
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border bg-white p-6">
      <div>
        <h2 className="text-lg font-semibold text-[color:var(--fulkro-title)]">
          Precios base ENS (implantación)
        </h2>
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Fuente única editable. Al guardar, los nuevos precios se reflejan en
          cotizaciones, facturas y propuestas. Reinicia el backend para
          propagarlos a todos los workers.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      )}
      {saved && (
        <p className="text-sm text-green-700">Precios guardados correctamente.</p>
      )}

      <div className="flex flex-col gap-3">
        {ORDER.map((cat) => (
          <label key={cat} className="flex items-center gap-3">
            <span className="w-24 font-medium">{LABELS[cat]}</span>
            <input
              type="number"
              min={0}
              step={100}
              className="w-44 rounded border px-3 py-2"
              value={values[cat] ?? ""}
              onChange={(e) =>
                setValues((v) => ({ ...v, [cat]: e.target.value }))
              }
              aria-label={`Precio ${LABELS[cat]}`}
            />
            <span className="text-sm text-[color:var(--fulkro-muted)]">€</span>
          </label>
        ))}
      </div>

      <Button
        type="button"
        onClick={() => void save()}
        disabled={saving}
        className="self-start"
        data-testid="pricing-save"
      >
        {saving ? "Guardando…" : "Guardar precios"}
      </Button>
    </div>
  );
}
