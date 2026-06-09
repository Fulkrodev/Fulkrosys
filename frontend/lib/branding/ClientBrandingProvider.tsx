"use client";

/**
 * ClientBrandingProvider · MB-9 atom 9.2.
 *
 * Wraps cliente portal · fetches /client-portal/branding · injects CSS vars
 * --client-primary-color + --client-secondary-color into <html> for cascade.
 * Exposes brand metadata via React context for descendants (footer, hero).
 *
 * Graceful fallback: if endpoint fails or returns null fields, FULKRO
 * defaults apply (no CSS var override · existing var(--fulkro-accent) keeps).
 */
import { createContext, useContext, useEffect, useState } from "react";

import { type BrandingView, portalGetBranding } from "@/lib/branding/api";


interface BrandingContext {
  branding: BrandingView | null;
  loading: boolean;
  /**
   * Sesión 3B-2B.8 CLUSTER 4 Phase 4D · derived logo_url for cliente portal
   * UI components. Returns canonical endpoint /api/v1/client-portal/branding/logo
   * cuando has_logo=True · null cuando NO logo configured.
   *
   * Logo binary serve endpoint backend implements GET that streams file from
   * logo_path filesystem storage (RLS enforced per cliente session).
   */
  logoUrl: string | null;
}


const Ctx = createContext<BrandingContext>({
  branding: null, loading: true, logoUrl: null,
});


export function useClientBranding(): BrandingContext {
  return useContext(Ctx);
}


function deriveLogoUrl(branding: BrandingView | null): string | null {
  if (branding === null || !branding.has_logo) return null;
  return "/api/v1/client-portal/branding/logo";
}


export function ClientBrandingProvider({ children }: { children: React.ReactNode }) {
  const [branding, setBranding] = useState<BrandingView | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    portalGetBranding()
      .then((b) => {
        if (cancelled) return;
        setBranding(b);
        // Inject CSS vars on <html> for cascade across portal
        const root = document.documentElement;
        if (b.primary_color) {
          root.style.setProperty("--client-primary-color", b.primary_color);
        }
        if (b.secondary_color) {
          root.style.setProperty("--client-secondary-color", b.secondary_color);
        }
      })
      .catch(() => {
        if (!cancelled) setBranding(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      // Cleanup CSS vars on unmount (when leaving portal)
      try {
        document.documentElement.style.removeProperty("--client-primary-color");
        document.documentElement.style.removeProperty("--client-secondary-color");
      } catch {
        // SSR no-op
      }
    };
  }, []);

  return (
    <Ctx.Provider
      value={{ branding, loading, logoUrl: deriveLogoUrl(branding) }}
    >
      {children}
    </Ctx.Provider>
  );
}
