import * as React from "react";

/**
 * PublicPortalShell · chrome neutro para portales públicos token-gated
 * (pentester · remediación · verify-auth · error boundary del grupo (portal)).
 *
 * Extraído de (portal)/layout.tsx en #20: el layout del grupo pasa a ser
 * passthrough para no apilar header+footer sobre los portales que renderizan
 * su PROPIO chrome completo (p.ej. AuditorPortalChrome). Los portales que NO
 * tienen chrome propio (los de aquí) se envuelven con este shell.
 *
 * Sin marca del consultor más allá de la firma legal mínima · no indexado.
 */
export function PublicPortalShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-fulkro-ink-50 text-fulkro-ink-700">
      <header className="border-b border-fulkro-ink-300/60 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-semibold text-fulkro-primary-700">
            Portal seguro
          </p>
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Enlace firmado Ed25519 · acceso restringido · no indexado
          </p>
        </div>
      </header>
      <main
        id="main-content"
        className="mx-auto w-full max-w-5xl flex-1 px-3 py-6 sm:px-4 sm:py-8"
      >
        {children}
      </main>
      <footer className="border-t border-fulkro-ink-300/60 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3 text-[11px] text-fulkro-ink-500">
          <span>Marcos Mata García · Consultor ENS independiente</span>
          <span>RD 311/2022</span>
        </div>
      </footer>
    </div>
  );
}
