/**
 * Helper mockProjectShell · stubea los endpoints del LAYOUT admin
 * project-scoped (`/admin/projects/[id]/layout.tsx`) para specs que navegan
 * directo a una página project-scoped con un projectId SINTÉTICO (no existente
 * en la BD de test).
 *
 * Por qué es necesario:
 *   El layout monta `<ActiveProjectSync projectId={id} />`. Cuando el
 *   activeProject sembrado (loginAsMarcos siembra el proyecto del test-client)
 *   NO coincide con el `id` de la URL, ActiveProjectSync hace
 *   `GET /api/v1/projects/{id}/header`. Si ese fetch falla (404 porque el id es
 *   sintético), ActiveProjectSync ejecuta `router.replace("/admin/projects")`
 *   → la página se va al SELECTOR antes de montar su contenido → los
 *   `getByTestId` de la spec hacen timeout 30s.
 *
 *   Además `ProjectHeader` + `ProjectTabs` (ProjectFeaturesProvider) consumen
 *   `/header` y `/feature-flags`. Stubearlos evita el redirect y deja la página
 *   renderizar su panel real (cuyos endpoints sí mockea cada fixture focal).
 *
 * Source of truth de los endpoints:
 *   - `components/layout/ActiveProjectSync.tsx` (GET /projects/{id}/header)
 *   - `components/project/ProjectHeader.tsx`    (GET /projects/{id}/header)
 *   - `lib/contexts/ProjectFeaturesContext.tsx` (GET /projects/{id}/feature-flags)
 */
import type { Page } from "@playwright/test";

import type { EnsCategory } from "@/lib/feature-flags.types";

interface MockProjectShellOpts {
  projectId: string;
  category?: EnsCategory;
  clientName?: string;
  clientId?: string;
}

/**
 * Mockea header + feature-flags del layout admin project-scoped.
 * Llamar ANTES de `page.goto(...)` en specs project-scoped con projectId
 * sintético. Las rutas son anchoradas por projectId para no chocar con otros
 * mocks de la misma spec.
 */
export async function mockProjectShell(
  page: Page,
  opts: MockProjectShellOpts,
): Promise<void> {
  const {
    projectId,
    category = "MEDIA",
    clientName = "Cliente Piloto Test",
    clientId = "c0000000-0000-4000-8000-000000000000",
  } = opts;

  const headerBody = {
    project: {
      id: projectId,
      nombre: "Proyecto ENS Test",
      fase: "implantacion",
      categoria_objetivo: category,
      lifecycle_state: "active",
      fecha_kickoff: "2026-03-01",
      fecha_objetivo_certificacion: "2026-12-31",
      certified_at: null,
    },
    cliente: {
      id: clientId,
      nombre: clientName,
      cif: "B12345678",
      sector: "tecnologia",
      provincia: "Madrid",
    },
    rseg_contact: null,
    ciso_contact: null,
    conformity: {
      route_status: "active",
      route_type: "certificacion_enac",
      expiration_date: null,
      submissions_count: 0,
      renewals_count: 0,
      material_changes_count: 0,
    },
  };

  await page.route(
    new RegExp(`/api/v1/projects/${projectId}/header$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(headerBody),
      });
    },
  );

  await page.route(
    new RegExp(`/api/v1/projects/${projectId}/feature-flags`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          categoria: category,
          archetype: null,
          employee_count: null,
          features: {},
        }),
      });
    },
  );
}
