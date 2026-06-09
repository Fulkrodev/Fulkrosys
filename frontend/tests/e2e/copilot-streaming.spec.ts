import * as path from "path";

import { expect, test, type Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_PATH = process.env.COPILOT_E2E_PROJECT_PATH ?? "/admin/dashboard";
const CAPTURE_DIR = process.env.COPILOT_E2E_CAPTURE_DIR;

async function snapshot(page: Page, name: string): Promise<void> {
  if (!CAPTURE_DIR) return;
  await page.screenshot({
    path: path.join(CAPTURE_DIR, `s11_fase11_${name}.png`),
    fullPage: false,
  });
}

async function openPanel(page: Page): Promise<void> {
  const sheetTitle = page.getByRole("heading", { name: /Copiloto FULKRO/i });
  if (await sheetTitle.isVisible().catch(() => false)) return;
  await page.keyboard.press("Meta+J");
  if (!(await sheetTitle.isVisible().catch(() => false))) {
    await page.keyboard.press("Control+J");
  }
  await expect(sheetTitle).toBeVisible({ timeout: 5_000 });
}

async function closePanel(page: Page): Promise<void> {
  const sheetTitle = page.getByRole("heading", { name: /Copiloto FULKRO/i });
  if (!(await sheetTitle.isVisible().catch(() => false))) return;
  await page.keyboard.press("Meta+J");
  if (await sheetTitle.isVisible().catch(() => false)) {
    await page.keyboard.press("Control+J");
  }
  await expect(sheetTitle).toBeHidden({ timeout: 5_000 });
}

test.describe("Copilot streaming · panel global ⌘J", () => {
  test.slow();

  // SKIP: el panel global ⌘J + quick actions SÍ funcionan (cubierto por el test
  // "Quick action button auto-envía…" que pasa verde). Este test, además de
  // abrir el panel, depende de STREAMING LLM REAL: envía "qué exige el RD
  // 311/2022 sobre op.acc.6" y espera respuesta LLM en streaming + citation
  // popover con chunk_id desde el corpus RAG. El harness E2E va con API key
  // vacía (mock-by-default · ver memoria suite-seal-llm-hang) → no hay streaming
  // ni citas reales. Recuperable solo con FULKRO_RUN_LLM_TESTS=1 + corpus RAG
  // sembrado. Candidata a borrar/gate-por-env tras contraste (Marcos).
  test.skip("⌘J abre el panel · pregunta · streaming · citation popover", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await page.goto(PROJECT_PATH);
    await page.waitForLoadState("domcontentloaded");
    await snapshot(page, "01_dashboard_panel_closed");

    await openPanel(page);
    await snapshot(page, "02_panel_open_quick_actions");

    const composer = page.getByRole("textbox", {
      name: /pregunta|consulta|copiloto/i,
    });
    await composer.fill("qué exige el RD 311/2022 sobre op.acc.6");
    await composer.press("Enter");

    await expect(page.locator("text=/RD 311.*2022/i").first()).toBeVisible({
      timeout: 30_000,
    });

    const citationBadge = page
      .getByRole("button")
      .filter({ hasText: /\[?RD 311.*2022.*op\.acc\.6\]?/i })
      .first();
    await expect(citationBadge).toBeVisible({ timeout: 30_000 });

    await citationBadge.click();
    await expect(page.locator("text=/chunk_id/i")).toBeVisible({
      timeout: 5_000,
    });
    await snapshot(page, "03_citation_popover_open");

    // Cerrar popover (Escape) y luego panel via botón "Cerrar" del Sheet.
    // ⌘J ignora intencionalmente typing targets (textarea) por diseño,
    // así que dependemos del botón cuando el focus está dentro del composer.
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: /^Cerrar$/i }).first().click();
    const sheetTitle = page.getByRole("heading", { name: /Copiloto FULKRO/i });
    await expect(sheetTitle).toBeHidden({ timeout: 5_000 });
  });

  test("Quick action button auto-envía la query sugerida", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await page.goto(PROJECT_PATH);
    await openPanel(page);

    const action = page
      .getByRole("button")
      .filter({ hasText: /Resumen del proyecto activo|¿Qué toca hoy\?|Estado DdA/i })
      .first();
    await expect(action).toBeVisible({ timeout: 5_000 });
    await action.click();

    await expect(page.locator("text=/proyecto|copiloto/i").first()).toBeVisible({
      timeout: 30_000,
    });
  });

  // Skip por defecto: el threshold 0.45 sobre cosine raw del e5-large
  // multilingual no se dispara con queries reales (incluso off-topic
  // dan ≥0.6 por vocabulario regulatorio común). El branch corpus_gap
  // del system prompt + el badge frontend están cubiertos por:
  //   - 3 tests backend mock en test_copilot_corpus_fallback.py
  //   - 1 test backend real-LLM marcado @pytest.mark.llm (forzando
  //     confidence vía monkeypatch sobre hybrid_search)
  // Para activar este E2E, exportar COPILOT_E2E_FORCE_CORPUS_GAP=1
  // (requiere endpoint dev o seed con corpus reducido).
  test("Corpus gap query muestra badge warning", async ({
    context,
    page,
  }) => {
    test.skip(
      process.env.COPILOT_E2E_FORCE_CORPUS_GAP !== "1",
      "Requiere COPILOT_E2E_FORCE_CORPUS_GAP=1 + seed con corpus reducido. " +
        "El threshold 0.45 sobre cosine raw del e5 multilingual no se " +
        "dispara con queries reales en corpus completo.",
    );

    await loginAsMarcos(context);
    await page.goto(PROJECT_PATH);
    await openPanel(page);

    const composer = page.getByRole("textbox", {
      name: /pregunta|consulta|copiloto/i,
    });
    await composer.fill(
      "procedimiento exacto certificación IoT industrial GB/T 22239-2019 China nivel 3",
    );
    await composer.press("Enter");

    await expect(
      page.locator("text=/Fuente no disponible aún en corpus FULKRO/i"),
    ).toBeVisible({ timeout: 60_000 });
    await snapshot(page, "04_corpus_gap_badge");
  });
});
