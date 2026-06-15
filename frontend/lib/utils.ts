import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(input: string | number | Date, locale = "es-ES"): string {
  const date = new Date(input);
  // §2.7: fecha inválida/undefined → "—" en vez de "Invalid Date" o throw.
  if (Number.isNaN(date.getTime())) return "—";
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
  if (Number.isNaN(date.getTime())) return "—";
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

/**
 * §4.5 audit-2026-06-15 · normaliza el `detail` de un error de API a un mensaje
 * legible. FastAPI en un 422 AUTOMÁTICO devuelve `detail` como LISTA de objetos
 * `[{loc,msg,type},...]`; `String(detail)` daba "[object Object]" al cliente.
 * Maneja string (422 explícito), array (422 automático → une los `msg`) y fallback.
 */
export function detailToMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const d = (payload as { detail: unknown }).detail;
    if (typeof d === "string" && d.trim() !== "") return d;
    if (Array.isArray(d)) {
      const msgs = d
        .map((e) =>
          e && typeof e === "object" && "msg" in e
            ? String((e as { msg: unknown }).msg)
            : null,
        )
        .filter((m): m is string => Boolean(m));
      if (msgs.length) return msgs.join(" · ");
    }
  }
  return fallback;
}
