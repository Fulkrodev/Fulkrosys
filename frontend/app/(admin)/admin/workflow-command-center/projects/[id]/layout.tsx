/**
 * Layout per-cliente · 3-col grid · sub-atom 1.C.D.B.3 v3.8.
 *
 * Layout responsive:
 *   - Desktop: 75% workflow + 25% copiloto sidebar (sticky right)
 *   - Tablet: stack vertical · sidebar collapsible (próximamente)
 *   - Mobile: sidebar bottom-sheet expandible
 *
 * ProjectTabs admin existing INTOCABLE (OPS-045 sostenido fuerte ·
 * deferred refactor 1.D.B.0).
 */
import type { ReactNode } from "react";

export default function WorkflowCommandCenterProjectLayout({
  children,
}: {
  children: ReactNode;
}) {
  // Layout responsive · sidebar copiloto se renderiza dentro del page (commit
  // 2 ProjectCronologicaView orquesta) · este layout sólo aplica container
  // max-width responsive · no breaks 1.C.D.B.1 dashboard.
  return <>{children}</>;
}
