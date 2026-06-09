/**
 * Legacy redirect · Sesión 3B-2B.3 Phase X.3 (architectural cleanup).
 *
 * `/admin/clients/[id]/branding` consolidates into project-scoped
 * `/admin/projects/[id]/personalizacion` (304 LOC existing). Per R23 strict:
 * branding lives at project scope (cliente entity ≈ project entity 1:1 MVP).
 *
 * Step X.4b will rewire `/admin/clients/[id]` to be a router that resolves
 * cliente.id → project.id and redirects · this branding route then chains to
 * `/admin/projects/{resolvedProjectId}/personalizacion`. For the MVP we
 * redirect to /admin/projects?from=branding-legacy so the selector helps
 * Marcos pick the right project explicitly.
 *
 * Future-X: when backend exposes project_id per cliente in cliente list, this
 * redirect can become surgical (1 hop · client-id → project-id → personalizacion).
 */
import { redirect } from "next/navigation";

export default function LegacyClientBrandingRedirect() {
  // Per directive Step X.3: branding migrates to /admin/projects/[id]/personalizacion.
  // Without project_id lookup at redirect-time, route Marcos through the
  // projects selector (he picks the right one explicitly).
  redirect("/admin/projects");
}
