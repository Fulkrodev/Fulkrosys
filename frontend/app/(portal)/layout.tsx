import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Portal seguro",
  description:
    "Acceso por enlace firmado. Esta página es confidencial y vinculada a un proyecto específico.",
  robots: { index: false, follow: false },
};

/**
 * Layout del grupo (portal) · PASSTHROUGH (#20).
 *
 * Cada portal token-gated renderiza su PROPIO chrome:
 * - auditor-portal → AuditorPortalChrome (header marca cliente + sidebar + footer)
 * - pentester · remediación · verify-auth · error → PublicPortalShell (chrome neutro)
 *
 * Antes este layout añadía un header+footer neutro que se APILABA sobre el
 * chrome propio del portal auditor → doble header / triple footer (junto con el
 * FulkroFooter global del root). Pasarlo a passthrough elimina la duplicación;
 * el FulkroFooter global se suprime en estas rutas vía GlobalFulkroFooter.
 */
export default function PortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
