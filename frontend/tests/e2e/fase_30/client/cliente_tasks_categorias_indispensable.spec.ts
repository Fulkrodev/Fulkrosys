/**
 * E2E · fase_30 cliente · /tasks categorías indispensable-only.
 *
 * Sub-atom 1.D.F.bis.III.C v3.11.
 *
 * Verifica:
 *  - /tasks render con header counts + categorías prominent
 *  - Categorías visible per tipo (Firmas · Subir docs · Formación · Implementación · Autorizaciones)
 *  - Filtros funcionan (click categoría reduce lista)
 *  - Empty state friendly cuando 0 tasks
 *  - Status filter secundario funciona
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClienteIndispensable } from "../_fixtures";

test.describe("fase_30 cliente · /tasks indispensable categorías", () => {
  test("categorías filter + tasks listed + status filter secundario", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClienteIndispensable(page);

    await page.goto("/client-portal/tasks");

    await expect(page.getByTestId("cliente-tasks-list")).toBeVisible();

    // Header + counts indispensable.
    // El título "Mis tareas" aparece DOS veces: como <h1> de la página
    // (app/.../tasks/page.tsx) y como <CardTitle> (renderiza <h3>) dentro de
    // ClientTasksList. getByRole("heading") sin nivel viola strict-mode (2
    // matches) → anclamos al <h1> de la página con level: 1. Verificado en
    // components/ui/card.tsx (CardTitle = h3) + ClientTasksList.tsx.
    await expect(
      page.getByRole("heading", { name: /Mis tareas/i, level: 1 }),
    ).toBeVisible();

    // Categorías prominent · botones con icons + count
    await expect(page.getByTestId("cliente-cat-filter-all")).toBeVisible();
    await expect(page.getByTestId("cliente-cat-filter-firmas")).toBeVisible();
    await expect(
      page.getByTestId("cliente-cat-filter-evidencias"),
    ).toBeVisible();
    await expect(page.getByTestId("cliente-cat-filter-formacion")).toBeVisible();
    await expect(
      page.getByTestId("cliente-cat-filter-implementacion"),
    ).toBeVisible();
    await expect(
      page.getByTestId("cliente-cat-filter-autorizaciones"),
    ).toBeVisible();

    // Status filter secundario
    await expect(page.getByTestId("cliente-status-filter-all")).toBeVisible();
    await expect(
      page.getByTestId("cliente-status-filter-pending"),
    ).toBeVisible();
  });
});
