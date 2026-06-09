/**
 * /admin/projects/[id]/feature-flags · admin page para gestionar
 * feature_flag_overrides del proyecto (ADR-046 · MB-10 Atom 10.3.C · renamed post-audit B1.2 · was ADR-037 MB-10).
 *
 * Acceso: route group `(admin)` ya está gated por middleware (admin pool).
 * NO require_owner adicional client-side.
 *
 * Q1 cement: path `/feature-flags/` (matches backend naming ADR-046).
 * Q2 cement: NO entry en ProjectTabs · power-user URL-only access.
 * Q3 cement: título "Capabilities" + subtitle Spanish (ISMS M32 LOGICAL term).
 * Q4 cement: project-level scope (client-level defer forward).
 */
import { OverridesManagementPanel } from "@/components/admin/feature-flags/OverridesManagementPanel";

export const metadata = {
  title: "Capabilities · FULKRO",
};

export default function FeatureFlagsAdminPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">Capabilities</h1>
        <p className="text-sm text-muted-foreground">
          Gestión avanzada de feature flags overrides del proyecto. Los
          overrides aplicados aquí prevalecen sobre la evaluación automática
          basada en categoría ENS y arquetipo PYME hasta su expiración o
          revocación.
        </p>
      </header>
      <OverridesManagementPanel projectId={params.id} />
    </div>
  );
}
