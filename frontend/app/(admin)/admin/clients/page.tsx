/**
 * Legacy redirect · Sesión 3B-2B.3 Phase X.3 (architectural cleanup).
 *
 * `/admin/clients` (cross-cliente lista) consolidates into `/admin/projects`
 * selector. Per R23 strict: admin entry point is project-scoped único
 * (cliente entity ≈ project entity 1:1 MVP).
 *
 * URL legacy preserved for bookmarks · server-side redirect immediate.
 *
 * Future-1.E.multi-project-per-cliente: when 2nd cliente onboarded with N>1
 * projects, this redirect may be revisited to surface cliente-level grouping.
 */
import { redirect } from "next/navigation";

export default function LegacyClientsListRedirect() {
  redirect("/admin/projects");
}
