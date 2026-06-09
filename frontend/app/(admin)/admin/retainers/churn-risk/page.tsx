/**
 * Legacy redirect · Sesión 3B-2B.3 Phase X.4d (architectural cleanup).
 *
 * `/admin/retainers/churn-risk` (was 84 LOC standalone ChurnRiskList page)
 * migrated to widget in /admin/dashboard. Compact top-3 critical+high view
 * with "Ver todos en Finanzas" drill-down.
 *
 * Rationale: cross-cliente retainers at risk is a glanceable signal · NOT
 * deserving of dedicated page navigation in admin nav. Widget pattern keeps
 * visibility at dashboard level + detailed table available via /admin/finance.
 *
 * Bookmarks preserved · server-side redirect immediate.
 */
import { redirect } from "next/navigation";

export default function LegacyChurnRiskRedirect() {
  redirect("/admin/dashboard");
}
