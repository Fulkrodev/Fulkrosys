"use client";

import { usePathname } from "next/navigation";

import { FulkroFooter } from "@/components/layout/FulkroFooter";

/**
 * GlobalFulkroFooter · #20.
 *
 * Renderiza el FulkroFooter de marca (identidad consultora) SÓLO fuera de los
 * portales públicos token-gated del grupo (portal). Esos portales son neutros
 * por diseño y ya renderizan su propio footer (AuditorPortalChrome para el
 * auditor · PublicPortalShell para pentester/remediación/verify-auth); añadir
 * el footer global encima producía un tercer footer apilado.
 */
const PUBLIC_PORTAL_PREFIXES = [
  "/auditor-portal",
  "/pentester-portal",
  "/remediation",
  "/verify-auth",
];

export function GlobalFulkroFooter() {
  const pathname = usePathname();
  const isPublicPortal = PUBLIC_PORTAL_PREFIXES.some(
    (prefix) => pathname === prefix || pathname?.startsWith(`${prefix}/`),
  );
  if (isPublicPortal) return null;
  return <FulkroFooter />;
}
