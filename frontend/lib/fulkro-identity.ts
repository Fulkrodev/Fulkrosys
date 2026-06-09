/**
 * Fulkro identity · single source of truth frontend.
 *
 * Sesión 3B-4 Ejecutable 7.6 (2026-05-27).
 *
 * DOCTRINE INVIOLABLE: Marcos Mata · autónomo Madrid · consultor ENS.
 * Fulkro identity propagation cross-system (Footer · branding · links).
 *
 * Outcome-as-a-Service framing: cliente VE info Fulkro consultora claramente ·
 * trust building. "Fulkro shown not sold" doctrine.
 */

export const FULKRO_IDENTITY = {
  phone: "+34 637 165 328",
  phoneTel: "+34637165328",
  web: "www.fulkro.es",
  webUrl: "https://www.fulkro.es",
  email: "marcosmata@fulkro.es",
  taglineInternal: "Rigor · velocidad · proactividad",
  // Color canónico del distintivo de conformidad ENS · Pantone Orange 021C
  // (CCN-STIC 809) · único para todas las categorías. Distinto del violeta UI.
  distintivoColorPantoneOrange021C: "#FE5000",
  authorName: "Marcos Mata",
  authorRole: "Consultor de Fulkro",
  footerText: "Fulkro · +34 637 165 328 · www.fulkro.es · marcosmata@fulkro.es",
} as const;

export type FulkroIdentity = typeof FULKRO_IDENTITY;
