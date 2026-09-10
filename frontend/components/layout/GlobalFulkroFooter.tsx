"use client";

import { usePathname } from "next/navigation";

import { FulkroFooter } from "@/components/layout/FulkroFooter";

/**
 * GlobalFulkroFooter · #20.
 *
 * Renderiza el FulkroFooter de marca (identidad consultora + enlaces legales)
 * en todas las páginas MENOS en dos sitios:
 *
 *   1. Los portales públicos con acceso por token, que son neutros por diseño y
 *      ya traen su propio pie (AuditorPortalChrome para el auditor ·
 *      PublicPortalShell para pentester/remediación/verify-auth). Añadir el
 *      global encima producía un tercer pie apilado.
 *   2. El grupo (legal), cuyo layout ya tiene su propio pie con exactamente los
 *      mismos enlaces legales. Desde que el pie global los lleva (BLOQUE I6),
 *      renderizar los dos dejaba la misma lista de ocho enlaces dos veces
 *      seguidas en la misma pantalla.
 */
const PUBLIC_PORTAL_PREFIXES = [
  "/auditor-portal",
  "/pentester-portal",
  "/remediation",
  "/verify-auth",
];

// Las ocho rutas de frontend/app/(legal)/. Si se añade una página al grupo, va
// aquí Y en ENLACES_LEGALES de FulkroFooter.
const LEGAL_PREFIXES = [
  "/privacy",
  "/derechos-rgpd",
  "/cookies",
  "/terms",
  "/imprint",
  "/trust",
  "/sub-processors",
  "/dpa-template",
];

export function GlobalFulkroFooter() {
  const pathname = usePathname();
  const traeSuPropioPie = [...PUBLIC_PORTAL_PREFIXES, ...LEGAL_PREFIXES].some(
    (prefix) => pathname === prefix || pathname?.startsWith(`${prefix}/`),
  );
  if (traeSuPropioPie) return null;
  return <FulkroFooter />;
}
