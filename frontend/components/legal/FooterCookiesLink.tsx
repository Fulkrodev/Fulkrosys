"use client";

/**
 * FooterCookiesLink · permanent footer trigger to re-open the cookie banner
 * (atom 9.bis.1 PARTE B). Rendered by (legal)/layout.tsx and ClientFooter.
 */
import { openCookieBanner } from "./CookieConsentBanner";

interface FooterCookiesLinkProps {
  className?: string;
  label?: string;
}

export function FooterCookiesLink({
  className,
  label = "Cookies",
}: FooterCookiesLinkProps) {
  return (
    <button
      type="button"
      onClick={openCookieBanner}
      className={
        className ??
        "text-xs text-fulkro-ink-600 underline-offset-2 hover:text-fulkro-ink-900 hover:underline"
      }
    >
      {label}
    </button>
  );
}
