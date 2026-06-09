"use client";

/**
 * ClientFooter · MB-9 atom 9.2 Q4.B.
 *
 * Renders cliente footer_text (if configured) + FULKRO disclaimer always.
 * Uses ClientBrandingProvider context for cliente-specific text.
 */
import { useClientBranding } from "@/lib/branding/ClientBrandingProvider";


export function ClientFooter() {
  const { branding } = useClientBranding();
  const footerText = branding?.footer_text;

  return (
    <footer
      className="mt-12 border-t border-fulkro-surface-glass-border bg-fulkro-surface-glass px-4 py-4 text-center text-xs text-[color:var(--fulkro-muted)]"
      data-testid="client-portal-footer"
    >
      {footerText && (
        <p className="mb-1 font-medium text-[color:var(--fulkro-body)]">
          {footerText}
        </p>
      )}
      <p>
        Portal asistido por <strong>FULKRO</strong> · consultoría ENS ·{" "}
        <a
          href="https://fulkro.es"
          className="text-[color:var(--fulkro-accent)] hover:underline"
          target="_blank"
          rel="noopener noreferrer"
        >
          fulkro.es
        </a>
        {" · "}
        <a
          href="/client-portal/transparency"
          className="text-[color:var(--fulkro-accent)] hover:underline"
          data-testid="footer-transparency-link"
        >
          Transparencia IA
        </a>
      </p>
    </footer>
  );
}
