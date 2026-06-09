/**
 * FULKRO cookie inventory (atom 9.bis.1 PARTE B).
 *
 * Source of truth for the public Cookies Policy + CookieConfigureModal.
 * Updated whenever a new cookie is introduced — keeping this list in
 * sync with reality is a legal obligation under Guía AEPD 2020.
 */
export type CookieCategoryId = "necessary" | "functional" | "analytics";

export interface CookieDescriptor {
  name: string;
  provider: string;
  duration: string;
  purpose_es: string;
  type: "first-party" | "third-party";
}

export interface CookieCategory {
  id: CookieCategoryId;
  label: string;
  description_es: string;
  fixed_on: boolean;
  cookies: CookieDescriptor[];
}

export const COOKIE_INVENTORY: CookieCategory[] = [
  {
    id: "necessary",
    label: "Necesarias",
    description_es:
      "Permiten el funcionamiento básico de la plataforma (autenticación, protección CSRF, sesión). No requieren consentimiento y no pueden desactivarse.",
    fixed_on: true,
    cookies: [
      {
        name: "fulkro_session",
        provider: "FULKRO",
        duration: "Sesión (12 horas)",
        purpose_es: "Mantiene la sesión autenticada del usuario.",
        type: "first-party",
      },
      {
        name: "fulkro_csrf",
        provider: "FULKRO",
        duration: "Sesión",
        purpose_es:
          "Protección CSRF (triple-binding ADR-019) para acciones que modifican datos.",
        type: "first-party",
      },
    ],
  },
  {
    id: "functional",
    label: "Funcionales",
    description_es:
      "Memorizan tus preferencias de uso (idioma, tema visual) para personalizar la experiencia.",
    fixed_on: false,
    cookies: [
      {
        name: "fulkro_theme",
        provider: "FULKRO",
        duration: "1 año",
        purpose_es: "Preferencia de tema visual (claro/oscuro).",
        type: "first-party",
      },
      {
        name: "fulkro_lang",
        provider: "FULKRO",
        duration: "1 año",
        purpose_es: "Idioma seleccionado (ES/EN).",
        type: "first-party",
      },
    ],
  },
  {
    id: "analytics",
    label: "Analíticas",
    description_es:
      "Métricas agregadas y pseudonimizadas del uso de la plataforma para mejora del producto. Servidor auto-hospedado en la UE; no compartimos datos con terceros publicitarios.",
    fixed_on: false,
    cookies: [
      {
        name: "ph_<distinct_id>",
        provider: "PostHog (auto-hospedado · UE)",
        duration: "1 año",
        purpose_es:
          "Identificador anónimo de visitante para analítica agregada (post-MB-13).",
        type: "first-party",
      },
    ],
  },
];
