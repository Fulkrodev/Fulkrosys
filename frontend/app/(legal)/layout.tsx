import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { CookieConsentBanner } from "@/components/legal/CookieConsentBanner";
import { FooterCookiesLink } from "@/components/legal/FooterCookiesLink";

/**
 * Layout for FULKRO public legal & trust pages (atom 9.bis.5).
 *
 * Used by /trust, /sub-processors (and later /privacy, /cookies, /terms,
 * /imprint in atom 9.bis.1). Wide professional layout suited to
 * marketing/compliance content — distinct from (public)/layout.tsx
 * which is hardcoded narrow (max-w-lg) for signing pages.
 */
export default function LegalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-white text-fulkro-ink-900">
      <header className="border-b border-fulkro-ink-300/60 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="inline-flex">
            <Logo variant="light" size="md" priority />
          </Link>
          <nav className="flex items-center gap-6 text-sm text-fulkro-ink-700">
            <Link href="/trust" className="hover:text-fulkro-ink-900">
              Trust Center
            </Link>
            <Link href="/sub-processors" className="hover:text-fulkro-ink-900">
              Sub-procesadores
            </Link>
            <a
              href="mailto:dpo@fulkro.es"
              className="hover:text-fulkro-ink-900"
            >
              Contactar DPO
            </a>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-6 py-12">{children}</div>
      </main>
      <footer className="border-t border-fulkro-ink-300/60 bg-fulkro-ink-50">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-6 py-6 text-xs text-fulkro-ink-600 sm:flex-row sm:items-center">
          <div>
            FULKRO · Marcos Mata García · Madrid, España ·
            <a
              href="mailto:dpo@fulkro.es"
              className="ml-1 underline hover:text-fulkro-ink-900"
            >
              dpo@fulkro.es
            </a>
          </div>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-fulkro-ink-900">
              Privacidad
            </Link>
            <Link
              href="/derechos-rgpd"
              className="hover:text-fulkro-ink-900"
            >
              Derechos RGPD
            </Link>
            <Link href="/cookies" className="hover:text-fulkro-ink-900">
              Cookies
            </Link>
            <FooterCookiesLink
              label="Preferencias cookies"
              className="hover:text-fulkro-ink-900"
            />
            <Link href="/terms" className="hover:text-fulkro-ink-900">
              Términos
            </Link>
            <Link href="/imprint" className="hover:text-fulkro-ink-900">
              Aviso legal
            </Link>
          </div>
        </div>
      </footer>
      <CookieConsentBanner />
    </div>
  );
}
