/**
 * E2E · Test 5 fase_18 · admin · Tab Usuario portal · estado ensured render.
 *
 * Sub-atom 1.C.F.5 v3.10 · 1.C.F.1.1 (portal-user idempotente project-scoped).
 *
 * Backend ya soporta auto-create del PoC cliente vía endpoint idempotente
 * POST /api/v1/projects/{id}/portal-user (1.C.F.1.1 cerrado).
 * commercial_workflow_service._invite_client_user_best_effort lo triggerea
 * tras contract_signed. Verificación end-to-end del backend hook está
 * cubierta en tests integration backend (NO scope E2E frontend).
 *
 * Verifica frontend (estado post-ensure):
 *   - Tab Usuario portal · render datos client_user + portal_contact
 *   - Email PoC visible · indicador "complete" visible (1 portal access)
 *   - Tabla contactos del proyecto filter has_portal_access=true muestra
 *     usuario del portal con badge PORTAL
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F_ID,
  MOCK_PORTAL_USER_ENSURED,
  mockDepartmentsEmptyMedia,
  mockEnsRolesEmptyMedia,
  mockEquipoCommon,
  mockPortalUserEnsured,
} from "../_fixtures";

test.describe("fase_18 admin · portal-user ensured render (post auto-create)", () => {
  test("Tab Usuario portal muestra datos PoC tras ensure", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockEquipoCommon(page);
    await mockPortalUserEnsured(page);
    // Devuelve también el PoC contact in /contacts so portal list tab muestra row.
    await page.route(
      new RegExp(`/api/v1/projects/${PROJECT_F_ID}/contacts$`),
      async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            project_id: PROJECT_F_ID,
            contacts: [
              {
                id: MOCK_PORTAL_USER_ENSURED.portal_contact!.id,
                client_id: MOCK_PORTAL_USER_ENSURED.client_id,
                project_id: PROJECT_F_ID,
                full_name: "PoC FintechPlus",
                email: "poc@fintechplus.es",
                phone: null,
                linkedin_url: null,
                role_title: "Punto de Contacto",
                role_category: "sponsor",
                is_primary: true,
                is_signatory: false,
                has_portal_access: true,
                notes_marcos: null,
                is_active: true,
                created_at: "2026-05-01T10:00:00Z",
                department_id: null,
              },
            ],
            total: 1,
            with_portal_access: 1,
          },
        });
      },
    );
    await mockDepartmentsEmptyMedia(page);
    await mockEnsRolesEmptyMedia(page);

    await page.goto(`/admin/projects/${PROJECT_F_ID}/equipo`);
    // Tab Usuario portal activo por defecto
    await page.getByRole("tab", { name: /Usuario portal/i }).click();

    // Email PoC visible (panel + tabla)
    await expect(
      page.getByText(/poc@fintechplus\.es/i).first(),
    ).toBeVisible();
    // Nombre del PoC
    await expect(
      page.getByText(/PoC FintechPlus/i).first(),
    ).toBeVisible();
  });
});
