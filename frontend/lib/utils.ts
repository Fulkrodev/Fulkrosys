import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(input: string | number | Date, locale = "es-ES"): string {
  const date = new Date(input);
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatDay(input: string | number | Date, locale = "es-ES"): string {
  const date = new Date(input);
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(date);
}

/**
 * Whitelist de protocolos seguros para un `href` que proviene del backend o
 * de un scope no totalmente confiable. Bloquea `javascript:`, `data:`,
 * `vbscript:`, etc. Permite http(s) absolutos y rutas relativas.
 */
export function isSafeHref(url: unknown): boolean {
  if (typeof url !== "string") return false;
  const trimmed = url.trim();
  if (trimmed === "") return false;
  // Rutas relativas / fragmentos / query → seguras.
  if (
    trimmed.startsWith("/") ||
    trimmed.startsWith("#") ||
    trimmed.startsWith("?")
  ) {
    return true;
  }
  try {
    // Base estática: resuelve relativas sin depender de window (SSR-safe).
    const parsed = new URL(trimmed, "https://placeholder.invalid");
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}
