/**
 * FulkroFooter · shared cross 3 portales (admin · cliente · auditor).
 *
 * Sesión 3B-4 Ejecutable 7.6 Phase 7.6.2 (2026-05-27).
 *
 * "Fulkro shown not sold" doctrine · cliente VE info consultora trust building.
 * WCAG 2.2 AA · accessible aria-labels · responsive · semantic HTML.
 */
import Link from "next/link";
import { Mail, Phone, Globe } from "lucide-react";

import { FULKRO_IDENTITY } from "@/lib/fulkro-identity";

export function FulkroFooter() {
  return (
    <footer
      role="contentinfo"
      aria-label="Información de contacto Fulkro consultora"
      className="border-t border-fulkro-ink-200/40 bg-white/60 py-3"
      data-testid="fulkro-footer"
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-4 gap-y-1 px-4 text-xs text-fulkro-ink-600">
        <span className="font-medium text-fulkro-primary-700">
          Fulkro
        </span>
        <span aria-hidden="true">·</span>
        <Link
          href={`tel:${FULKRO_IDENTITY.phoneTel}`}
          className="inline-flex items-center gap-1 underline hover:text-fulkro-primary-700"
          aria-label={`Llamar a Fulkro al teléfono ${FULKRO_IDENTITY.phone}`}
        >
          <Phone className="h-3 w-3" strokeWidth={2.3} aria-hidden="true" />
          {FULKRO_IDENTITY.phone}
        </Link>
        <span aria-hidden="true">·</span>
        <Link
          href={FULKRO_IDENTITY.webUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 underline hover:text-fulkro-primary-700"
          aria-label={`Visitar web Fulkro ${FULKRO_IDENTITY.web} (abre en nueva pestaña)`}
        >
          <Globe className="h-3 w-3" strokeWidth={2.3} aria-hidden="true" />
          {FULKRO_IDENTITY.web}
        </Link>
        <span aria-hidden="true">·</span>
        <Link
          href={`mailto:${FULKRO_IDENTITY.email}`}
          className="inline-flex items-center gap-1 underline hover:text-fulkro-primary-700"
          aria-label={`Enviar email a ${FULKRO_IDENTITY.email}`}
        >
          <Mail className="h-3 w-3" strokeWidth={2.3} aria-hidden="true" />
          {FULKRO_IDENTITY.email}
        </Link>
      </div>
    </footer>
  );
}
