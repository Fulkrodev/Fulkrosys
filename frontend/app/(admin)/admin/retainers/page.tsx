/**
 * Legacy redirect · Sesión 3B-2B.3 Phase X.3 (architectural cleanup).
 *
 * `/admin/retainers` (cross-cliente RetainerOpsCenter lista) consolidates
 * into project-scoped retainer view. Per R23 strict: retainer is per-project
 * concern · `/admin/projects/[id]/retainer` (RetainerProjectDashboard) is
 * canonical.
 *
 * Marcos navigates from /admin/projects selector → choose project → retainer
 * tab. NO global cross-cliente retainer dashboard needed in MVP (1:1 cliente
 * project mapping · per-project visibility suficient).
 *
 * Future-1.E.multi-project-retainer-aggregator: if N>1 retainers per Marcos
 * org demand cross-cliente aggregated view (revenue · churn · capacity),
 * re-introduce as widget in /admin/dashboard or /admin/finance instead.
 */
import { redirect } from "next/navigation";

export default function LegacyRetainersListRedirect() {
  redirect("/admin/projects");
}
