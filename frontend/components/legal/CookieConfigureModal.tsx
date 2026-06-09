"use client";

/**
 * CookieConfigureModal · granular consent per category (atom 9.bis.1 PARTE B).
 *
 * Guía AEPD 2020 mandate: cookies necesarias ON fixed (sin toggle); cookies
 * funcionales y analíticas opt-in con descripción + listado expandible.
 */
import { ChevronDown, ChevronUp, X } from "lucide-react";
import { useEffect, useState } from "react";

import { COOKIE_INVENTORY, type CookieCategoryId } from "@/lib/cookies/inventory";

interface CookieConfigureModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (decisions: {
    functional: boolean;
    analytics: boolean;
    marketing: boolean;
  }) => Promise<void> | void;
  submitting: boolean;
}

export function CookieConfigureModal({
  open,
  onClose,
  onSave,
  submitting,
}: CookieConfigureModalProps) {
  const [functional, setFunctional] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [expanded, setExpanded] = useState<Set<CookieCategoryId>>(new Set());

  useEffect(() => {
    if (!open) {
      setExpanded(new Set());
    }
  }, [open]);

  if (!open) return null;

  const toggleExpand = (id: CookieCategoryId) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="cookie-configure-title"
      className="fixed inset-0 z-[60] flex items-end justify-center bg-black/40 px-4 pb-4 pt-16 backdrop-blur-sm sm:items-center"
    >
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <header className="flex items-center justify-between border-b border-fulkro-ink-200 px-6 py-4">
          <h2
            id="cookie-configure-title"
            className="text-lg font-semibold text-fulkro-ink-900"
          >
            Configurar cookies
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-md p-1 text-fulkro-ink-600 hover:bg-fulkro-ink-100 hover:text-fulkro-ink-900"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <p className="mb-5 text-sm text-fulkro-ink-700">
            Decide qué tipos de cookies quieres permitir. Tu elección se
            guarda durante 24 meses y la puedes modificar en cualquier
            momento desde el enlace «Cookies» del pie de página.
          </p>

          <ul className="space-y-3">
            {COOKIE_INVENTORY.map((category) => {
              const isExpanded = expanded.has(category.id);
              const isOn =
                category.fixed_on ||
                (category.id === "functional" && functional) ||
                (category.id === "analytics" && analytics);
              return (
                <li
                  key={category.id}
                  className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50"
                >
                  <div className="flex items-start justify-between gap-4 p-4">
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-fulkro-ink-900">
                        {category.label}
                        {category.fixed_on ? (
                          <span className="ml-2 rounded bg-fulkro-ink-200 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-fulkro-ink-700">
                            Siempre activas
                          </span>
                        ) : null}
                      </h3>
                      <p className="mt-1 text-sm text-fulkro-ink-700">
                        {category.description_es}
                      </p>
                      <button
                        type="button"
                        onClick={() => toggleExpand(category.id)}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-fulkro-ink-700 hover:text-fulkro-ink-900"
                      >
                        {isExpanded ? "Ocultar" : "Ver"} cookies de esta categoría
                        {isExpanded ? (
                          <ChevronUp className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                    <ToggleSwitch
                      checked={isOn}
                      disabled={category.fixed_on}
                      onChange={(v) => {
                        if (category.id === "functional") setFunctional(v);
                        if (category.id === "analytics") setAnalytics(v);
                      }}
                      ariaLabel={category.label}
                    />
                  </div>
                  {isExpanded ? (
                    <table className="w-full text-xs">
                      <thead className="bg-white">
                        <tr className="text-left text-fulkro-ink-600">
                          <th className="px-4 py-2 font-medium">Cookie</th>
                          <th className="px-4 py-2 font-medium">Proveedor</th>
                          <th className="px-4 py-2 font-medium">Duración</th>
                          <th className="px-4 py-2 font-medium">Propósito</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-fulkro-ink-200 bg-white text-fulkro-ink-800">
                        {category.cookies.map((c) => (
                          <tr key={c.name}>
                            <td className="px-4 py-2 font-mono">{c.name}</td>
                            <td className="px-4 py-2">{c.provider}</td>
                            <td className="px-4 py-2">{c.duration}</td>
                            <td className="px-4 py-2">{c.purpose_es}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>

        <footer className="flex flex-col gap-2 border-t border-fulkro-ink-200 bg-white px-6 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-md border border-fulkro-ink-300 bg-white px-4 py-2 text-sm font-semibold text-fulkro-ink-900 hover:bg-fulkro-ink-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() =>
              onSave({ functional, analytics, marketing: false })
            }
            disabled={submitting}
            className="rounded-md border border-fulkro-ink-300 bg-white px-4 py-2 text-sm font-semibold text-fulkro-ink-900 hover:bg-fulkro-ink-50 disabled:opacity-50"
          >
            Guardar preferencias
          </button>
          <button
            type="button"
            onClick={() =>
              onSave({ functional: true, analytics: true, marketing: false })
            }
            disabled={submitting}
            className="rounded-md bg-fulkro-ink-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black disabled:opacity-50"
          >
            Aceptar todo
          </button>
        </footer>
      </div>
    </div>
  );
}

function ToggleSwitch({
  checked,
  disabled,
  onChange,
  ariaLabel,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
  ariaLabel: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-none items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700/40 ${
        checked
          ? "bg-fulkro-ink-900"
          : "bg-fulkro-ink-300 hover:bg-fulkro-ink-400"
      } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}
