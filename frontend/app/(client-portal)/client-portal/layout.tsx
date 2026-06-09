import type { Metadata } from "next";
import type { ReactNode } from "react";

import { ClientPortalChrome } from "@/components/layout/ClientPortalChrome";

/**
 * Layout client-portal — chrome consistente con admin (CONSISTENCY-001)
 * pero simplificado para el cliente (FASE 10.A).
 *
 * Este layout es Server Component (mantiene export metadata). La
 * lógica de chrome path-aware vive en ClientPortalChrome ("use client")
 * que detecta paths públicos (login, forgot, reset) y NO renderiza
 * Sidebar/Header — login queda como split logo+form puro.
 *
 * Aplica fix 10.A audit Marcos: cero superpuestos cross-system.
 *
 * Ver ADR-013 (separación 3 portales), ADR-018 (regresión 3.C),
 * CONSISTENCY-001 (chrome unificado).
 */

export const metadata: Metadata = {
  title: "Portal Cliente · FULKRO",
  // Metadata SEO · texto plano sin acrónimos para evitar confusión en
  // browser tab/social previews. El cliente verá ENS expandido en el
  // contenido visible de cada página · TooltipENS sobre la abreviatura.
  description:
    "Acceso seguro al proyecto de implantación del Esquema Nacional de Seguridad y retainer del cliente.",
  robots: { index: false, follow: false },
};

export default function ClientPortalLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <ClientPortalChrome>{children}</ClientPortalChrome>;
}
