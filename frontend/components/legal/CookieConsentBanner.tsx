"use client";

/**
 * CookieConsentBanner · Guía AEPD 2020 visual compliance (atom 9.bis.1 PARTE B).
 *
 * - Fixed bottom banner, z-50, full-width.
 * - 3 buttons SAME prominence: Rechazar todo · Configurar · Aceptar todo.
 * - NO ocultable hasta acción del usuario (banner persiste hasta consent).
 * - Persist via POST /api/v1/legal/cookies/consent.
 * - Audit log automático (IP + UA capturados server-side).
 *
 * Visibilidad:
 * - SE MUESTRA si no hay decisión cacheada localStorage (estado limpio).
 * - SE OCULTA tras click en cualquiera de los 3 botones.
 * - SE REABRE cuando FooterCookiesLink dispara via window event
 *   (``fulkro:open-cookie-banner``).
 */
import { Cookie, Settings2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  postConsent,
  readCachedConsent,
  writeCachedConsent,
  type CookieConsentState,
} from "@/lib/cookies/api";

import { CookieConfigureModal } from "./CookieConfigureModal";

const BANNER_EVENT = "fulkro:open-cookie-banner";

export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [configureOpen, setConfigureOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (readCachedConsent() === null) setVisible(true);
    const reopen = () => setVisible(true);
    window.addEventListener(BANNER_EVENT, reopen);
    return () => window.removeEventListener(BANNER_EVENT, reopen);
  }, []);

  async function persist(decisions: { functional: boolean; analytics: boolean; marketing: boolean }) {
    setSubmitting(true);
    try {
      const result = await postConsent(decisions);
      writeCachedConsent(result);
    } catch {
      // Fallback cached state · server retry next visit.
      writeCachedConsent({
        ...decisions,
        consent_timestamp: new Date().toISOString(),
        consent_renewal_due: null,
        authenticated: false,
      } as CookieConsentState);
    }
    setSubmitting(false);
    setVisible(false);
    setConfigureOpen(false);
  }

  const acceptAll = () => persist({ functional: true, analytics: true, marketing: false });
  const rejectAll = () => persist({ functional: false, analytics: false, marketing: false });

  if (!visible && !configureOpen) return null;

  return (
    <>
      {visible ? (
        <div
          role="dialog"
          aria-label="Aviso de cookies"
          className="fixed inset-x-0 bottom-0 z-50 border-t-4 border-fulkro-primary-700 bg-white shadow-2xl"
        >
          <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <Cookie className="mt-0.5 h-5 w-5 flex-none text-fulkro-ink-700" aria-hidden />
              <div className="text-sm text-fulkro-ink-800">
                <p className="font-medium text-fulkro-ink-900">
                  Utilizamos cookies en fulkro.es
                </p>
                <p className="mt-1 leading-relaxed text-fulkro-ink-700">
                  Usamos cookies <strong>necesarias</strong> para que la plataforma
                  funcione y, con tu permiso explícito, cookies{" "}
                  <strong>funcionales</strong> y <strong>analíticas</strong>{" "}
                  para mejorar el servicio. Puedes aceptar, rechazar o
                  configurar tus preferencias.{" "}
                  <Link
                    href="/cookies"
                    className="underline hover:text-fulkro-ink-900"
                  >
                    Más información
                  </Link>
                  .
                </p>
              </div>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-none">
              <button
                type="button"
                onClick={rejectAll}
                disabled={submitting}
                className="rounded-md border border-fulkro-ink-300 bg-white px-4 py-2 text-sm font-semibold text-fulkro-ink-900 hover:bg-fulkro-ink-50 focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700/40 disabled:opacity-50"
              >
                Rechazar todo
              </button>
              <button
                type="button"
                onClick={() => setConfigureOpen(true)}
                disabled={submitting}
                className="rounded-md border border-fulkro-ink-300 bg-white px-4 py-2 text-sm font-semibold text-fulkro-ink-900 hover:bg-fulkro-ink-50 focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700/40 disabled:opacity-50"
              >
                <Settings2 className="mr-1.5 -ml-0.5 inline h-4 w-4" aria-hidden />
                Configurar
              </button>
              <button
                type="button"
                onClick={acceptAll}
                disabled={submitting}
                className="rounded-md bg-fulkro-ink-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700/40 disabled:opacity-50"
              >
                Aceptar todo
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <CookieConfigureModal
        open={configureOpen}
        onClose={() => setConfigureOpen(false)}
        onSave={persist}
        submitting={submitting}
      />
    </>
  );
}

/** Programmatic trigger for FooterCookiesLink + AccountPrivacySection. */
export function openCookieBanner(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(BANNER_EVENT));
  }
}
