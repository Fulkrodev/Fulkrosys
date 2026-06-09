/**
 * E2E · Test 2 fase_22 · admin · R30 defensive enrich tip tutor visible.
 *
 * Sub-atom 1.D.B.2 v3.11 · CRÍTICO sostener R30.
 *
 * Verifica:
 *   - LLM response viola R30 ("Como ya sabes...") · backend enriquece con
 *     "Tip tutor" footer (NO full stub fallback · admin tolera)
 *   - Frontend renderiza enriched response (LLM badge sostiene)
 *   - Footer "Tip tutor" + "primer principios" visible · cliente puede
 *     pedir profundización
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockCopilotoAdminChatLLM,
  mockCronologicaForCopilotAdmin,
  PROJECT_DDD_ID,
} from "../_fixtures";

test.describe("fase_22 admin · R30 defensive enrich tip tutor", () => {
  test("LLM violation → enrich tip tutor footer visible · LLM mode sostiene", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockCronologicaForCopilotAdmin(page);
    await mockCopilotoAdminChatLLM(page);

    // FIX ruta UI evolucionada: el CopilotoAdminSidebar vive en /workflow
    // (ProjectCronologicaView), NO en /workspace (ahora WorkspacePanel).
    await page.goto(`/admin/projects/${PROJECT_DDD_ID}/workflow`);

    // QuickAction "explica_paso" trigger · mock fixture returns enriched response
    await page.getByRole("button", { name: /Explícame este paso/i }).click();

    // History entry LLM (is_stub=false · enriched) visible
    await expect(
      page.getByTestId("copiloto-admin-entry-llm").first(),
    ).toBeVisible({ timeout: 5000 });

    // Original LLM violation text preserved
    await expect(page.getByText(/Como ya sabes el DdA/i)).toBeVisible();

    // Tip tutor footer enriched visible · R30 sostener. UI drift: "primer
    // principios" aparece también en el footer estático del sidebar ("Modo
    // tutor cronológico · asume cero ENS · explica desde primer principios") →
    // scope al entry LLM (que contiene el tip de la respuesta enriquecida).
    const llmEntry = page.getByTestId("copiloto-admin-entry-llm").first();
    await expect(llmEntry.getByText(/Tip tutor/i)).toBeVisible();
    await expect(llmEntry.getByText(/primer principios/i)).toBeVisible();

    // Mode badge upgraded LLM (NO fallback stub)
    await expect(
      page.getByTestId("copiloto-admin-mode-badge"),
    ).toHaveText(/LLM/i);
  });
});
