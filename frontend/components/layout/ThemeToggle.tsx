"use client";

import { Monitor, Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", icon: Sun, label: "Claro" },
  { value: "dark", icon: Moon, label: "Oscuro" },
  { value: "system", icon: Monitor, label: "Sistema" },
] as const;

/** Tri-state theme switcher (light · dark · system).
 *
 * TODO-BRAND-DARK-001: dark mode aplazado a FASE 2 (S11 design system shadcn/ui
 * con tokens [data-theme="dark"] coherentes). Hasta entonces los botones se
 * renderizan disabled con tooltip "Próximamente — disponible en FASE 2".
 * El componente se mantiene en código para reactivación rápida.
 */
export function ThemeToggle() {
  return (
    <div
      role="group"
      aria-label="Cambiar tema (próximamente)"
      title="Próximamente"
      className="inline-flex items-center rounded-md border border-fulkro-ink-300/60 bg-white p-0.5 opacity-50 cursor-not-allowed"
    >
      {OPTIONS.map((o) => {
        const Icon = o.icon;
        return (
          <button
            key={o.value}
            type="button"
            disabled
            aria-label={`Tema ${o.label.toLowerCase()} (próximamente)`}
            aria-disabled
            title="Próximamente"
            className={cn(
              "inline-flex h-7 w-7 items-center justify-center rounded transition-colors pointer-events-none",
              "text-fulkro-ink-500",
            )}
          >
            <Icon size={12} />
          </button>
        );
      })}
    </div>
  );
}
