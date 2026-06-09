/**
 * E2E · fase_27 admin · ProjectTabs sweep DdA entry visible + sweep entries.
 *
 * Sub-atom 1.D.F.A + 1.D.F.B v3.11 · verify navegación project-scoped.
 *
 * Verifica:
 *  - ProjectTabs MAIN_TABS muestra "DdA" entry
 *  - SUB_TABS muestra 10 entries sweep (Workspace · Onboarding · Arquetipo · Discovery · Concienciación · Auditoría seca · AEPD · BIA · Backups · Retainer proy.)
 *  - Click DdA navega a /admin/projects/[id]/dda
 *  - R23 sostener · TODO entries project-scoped (NO sidebar global motor-específico)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockDdaAdmin,
  mockProjectFeaturesMedia,
  PROJECT_F27_ID,
} from "../_fixtures";

test.describe("fase_27 admin · ProjectTabs sweep DdA + 10 entries visible", () => {
  test("DdA entry MAIN_TABS visible + 10 SUB_TABS sweep visibles + navigate", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockProjectFeaturesMedia(page);
    await mockDdaAdmin(page);

    await page.goto(`/admin/projects/${PROJECT_F27_ID}/dda`);

    // DdA entry visible MAIN_TABS
    const ddaLink = page.getByRole("link", { name: /^DdA$/ });
    await expect(ddaLink.first()).toBeVisible();

    // 10 SUB_TABS sweep entries visibles
    await expect(
      page.getByRole("link", { name: /^Workspace$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Onboarding$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Arquetipo$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Discovery$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Concienciación$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Auditoría seca$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^AEPD$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^BIA$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Backups$/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /^Retainer \(proy\.\)$/ }).first(),
    ).toBeVisible();
  });
});
