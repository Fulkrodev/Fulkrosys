"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { toast } from "sonner";

/**
 * fulkroToast — wrapper sobre Sonner con variants brand y defaults UX.
 *
 * Uso típico:
 *   import { fulkroToast } from "@/lib/toast";
 *   fulkroToast.success("Cambio guardado");
 *   fulkroToast.error("No se pudo guardar", { description: err.message });
 *   fulkroToast.promise(saveFn(), {
 *     loading: "Guardando…",
 *     success: "Guardado correctamente",
 *     error: "Error al guardar",
 *   });
 *
 * Decisiones de diseño:
 * - Iconos brand fulkro (success/danger/warning/info) en lugar de los
 *   grises por defecto de Sonner — coherencia con la paleta.
 * - Errores duración 6s default (vs 4s otros) — UX para dar tiempo a leer.
 * - promise() expuesto para flujos async (login, save, delete).
 * - dismiss() expuesto para cierre manual.
 *
 * El componente <Toaster /> de Sonner ya está montado en app/providers.tsx;
 * NO requiere setup adicional.
 */

interface ToastOptions {
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const fulkroToast = {
  success: (message: string, opts?: ToastOptions) =>
    toast.success(message, {
      ...opts,
      icon: React.createElement(CheckCircle2, {
        className: "h-4 w-4 text-fulkro-success",
      }),
    }),

  error: (message: string, opts?: ToastOptions) =>
    toast.error(message, {
      duration: opts?.duration ?? 6000,
      ...opts,
      icon: React.createElement(XCircle, {
        className: "h-4 w-4 text-fulkro-danger",
      }),
    }),

  warning: (message: string, opts?: ToastOptions) =>
    toast.warning(message, {
      ...opts,
      icon: React.createElement(AlertTriangle, {
        className: "h-4 w-4 text-fulkro-warning",
      }),
    }),

  info: (message: string, opts?: ToastOptions) =>
    toast.info(message, {
      ...opts,
      icon: React.createElement(Info, {
        className: "h-4 w-4 text-fulkro-info",
      }),
    }),

  promise: <T,>(
    promise: Promise<T>,
    messages: { loading: string; success: string; error: string },
  ) => toast.promise(promise, messages),

  dismiss: () => toast.dismiss(),
};
