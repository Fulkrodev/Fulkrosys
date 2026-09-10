/**
 * FulkroFooter · compartido en admin · cliente · páginas públicas.
 *
 * Sesión 3B-4 Ejecutable 7.6 Phase 7.6.2 (2026-05-27) · identidad consultora.
 * BLOQUE I6 (2026-09-11) · enlaces legales.
 *
 * "Fulkro shown not sold" · el cliente VE la información de la consultora.
 * WCAG 2.2 AA · etiquetas accesibles · responsive · HTML semántico.
 *
 * ─── POR QUÉ ESTÁN AQUÍ LOS ENLACES LEGALES ───────────────────────────────
 *
 * Lo encontró el recorrido automático del bloque E, no una revisión a mano:
 * de las ocho páginas legales, SIETE no las enlazaba nadie desde fuera del
 * grupo legal. El único enlace entrante en todo el código era el de `/cookies`
 * desde el banner de consentimiento. Las páginas existían, estaban escritas y
 * respondían 200 — sólo que la única forma de llegar a ellas era teclear la URL.
 *
 * Eso importa aquí más que en otro sitio. El RGPD (art. 13) no pide que la
 * información al interesado exista: pide que se le FACILITE, y el considerando
 * 58 exige que sea "fácilmente accesible". Una plataforma de cumplimiento con la
 * política de privacidad inalcanzable es exactamente el defecto que vende
 * arreglar. Y el ejercicio de derechos (`/derechos-rgpd`) es peor todavía: es un
 * derecho que no se puede ejercer si no hay por dónde pinchar.
 *
 * Este pie está en el layout raíz, así que los enlaces salen en todas las
 * páginas menos en los cuatro portales públicos con su propia identidad neutra
 * (ver GlobalFulkroFooter) y en el propio grupo legal, que ya trae los suyos.
 */
import Link from "next/link";
import { Mail, Phone, Globe } from "lucide-react";

import { FooterCookiesLink } from "@/components/legal/FooterCookiesLink";
import { FULKRO_IDENTITY } from "@/lib/fulkro-identity";

/**
 * Las ocho páginas del grupo (legal), en el orden en que le sirven a alguien
 * que busca algo: primero lo que el RGPD obliga a facilitar, después lo
 * contractual, y al final lo que interesa a quien evalúa al proveedor.
 *
 * Si se añade una página a `frontend/app/(legal)/`, va aquí. `make recorrer-todo`
 * la contará como huérfana si no.
 */
const ENLACES_LEGALES: ReadonlyArray<{ href: string; texto: string }> = [
  { href: "/privacy", texto: "Privacidad" },
  { href: "/derechos-rgpd", texto: "Tus derechos RGPD" },
  { href: "/cookies", texto: "Cookies" },
  { href: "/terms", texto: "Términos" },
  { href: "/imprint", texto: "Aviso legal" },
  { href: "/trust", texto: "Trust Center" },
  { href: "/sub-processors", texto: "Sub-procesadores" },
  { href: "/dpa-template", texto: "Contrato de encargo (DPA)" },
];

export function FulkroFooter() {
  return (
    <footer
      role="contentinfo"
      aria-label="Contacto de Fulkro e información legal"
      className="border-t border-fulkro-ink-200 bg-white py-3"
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

      <nav
        aria-label="Información legal y protección de datos"
        className="mx-auto mt-2 flex max-w-7xl flex-wrap items-center justify-center gap-x-3 gap-y-1 px-4 text-xs text-fulkro-ink-600"
      >
        {ENLACES_LEGALES.map((enlace, i) => (
          <span key={enlace.href} className="inline-flex items-center gap-3">
            {i > 0 && <span aria-hidden="true">·</span>}
            <Link
              href={enlace.href}
              className="underline hover:text-fulkro-primary-700"
            >
              {enlace.texto}
            </Link>
          </span>
        ))}
        <span aria-hidden="true">·</span>
        <FooterCookiesLink
          label="Preferencias de cookies"
          className="underline hover:text-fulkro-primary-700"
        />
      </nav>
    </footer>
  );
}
