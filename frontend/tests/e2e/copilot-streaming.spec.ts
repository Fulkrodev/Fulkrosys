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

/**
 * ⌘J / Ctrl+J es un TOGGLE (useCopilotPanelShortcut acepta metaKey o ctrlKey).
 * La versión anterior pulsaba Meta+J y, si el Sheet aún no había pintado,
 * pulsaba también Control+J: cuando ambas llegaban al listener el panel se
 * abría y se volvía a cerrar (intermitente). Y si se pulsaba antes de hidratar,
 * ninguna tenía listener. Ahora: una sola pulsación por intento, reintentada
 * sólo mientras el panel siga cerrado (cubre la hidratación sin doble toggle).
 */
async function openPanel(page: Page): Promise<void> {
  const sheetTitle = page.getByRole("heading", { name: /Copiloto FULKRO/i });
  await expect(async () => {
    if (!(await sheetTitle.isVisible())) {
      await page.keyboard.press("Control+J");
    }
    await expect(sheetTitle).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 15_000 });
}

test.describe("Copilot streaming · panel global ⌘J", () => {
  test.slow();

  // El stream se mockea (el harness E2E va sin API key: nunca se llama al
  // modelo real). Lo que se prueba es el cableado UI completo del panel:
  // ⌘J → pregunta → deltas en streaming → evento `citation` → popover con el
  // chunk RAG (chunk_id + preview).
  test("⌘J abre el panel · pregunta · streaming · citation popover", async ({
    context,
    page,
  }) => {
    const CHUNK_ID = "c0ffee00-1111-4222-8333-444455556666";
    const QUESTION = "qué exige el RD 311/2022 sobre op.acc.6";
    const ANSWER =
      "El RD 311/2022 exige en op.acc.6 mecanismos de autenticación reforzada.";
    const sentQuestions: string[] = [];
    await page.route("**/api/v1/copilot/chat/stream", async (route) => {
      const body = route.request().postDataJSON() as { question?: string };
      sentQuestions.push(body.question ?? "");
      const frames = [
        {
          type: "start",
          chunks_used: 1,
          chunk_ids: [CHUNK_ID],
          measure_codes: ["op.acc.6"],
          confidence: 0.8,
          corpus_gap: false,
        },
        { type: "delta", text: "El RD 311/2022 exige en op.acc.6 " },
        { type: "delta", text: "mecanismos de autenticación reforzada." },
        {
          type: "citation",
          data: {
            raw: "[RD 311/2022 · op.acc.6]",
            norm: "rd311-op.acc.6",
            measure: "op.acc.6",
            chunk_id: CHUNK_ID,
            preview: "Mecanismo de autenticación (usuarios de la organización).",
          },
        },
        {
          type: "done",
          data: {
            answer: ANSWER,
            citations_found: ["[RD 311/2022 · op.acc.6]"],
            chunk_ids_used: [CHUNK_ID],
            chunks_used: [],
            not_in_corpus: false,
            low_grounding_confidence: false,
            confidence: 0.8,
            corpus_gap: false,
            model_used: "mock",
            interaction_log_id: null,
          },
        },
      ];
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join(""),
      });
    });

    await loginAsMarcos(context);
    await page.goto(PROJECT_PATH);
    await page.waitForLoadState("domcontentloaded");
    await snapshot(page, "01_dashboard_panel_closed");

    await openPanel(page);
    await snapshot(page, "02_panel_open_quick_actions");

    const composer = page.getByRole("textbox", {
      name: /pregunta|consulta|copiloto/i,
    });
    await composer.fill(QUESTION);
    await composer.press("Enter");

    const panel = page.getByRole("dialog");
    await expect(panel.getByText(ANSWER)).toBeVisible({ timeout: 10_000 });
    expect(sentQuestions).toEqual([QUESTION]);

    const citationBadge = panel.getByRole("button", {
      name: "Ver chunk RAG [RD 311/2022 · op.acc.6]",
    });
    await expect(citationBadge).toBeVisible();

    await citationBadge.click();
    await expect(page.getByText(`chunk_id: ${CHUNK_ID.slice(0, 8)}…`)).toBeVisible();
    await expect(
      page.getByText("Mecanismo de autenticación (usuarios de la organización)."),
    ).toBeVisible();
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
    // El stream del copiloto se mockea: el harness E2E va sin API key y este
    // test valida el cableado UI (quick action → envío → render), no el LLM.
    // Además garantiza que nunca se llama al modelo real.
    const MOCK_ANSWER = "Respuesta simulada del copiloto para la acción rápida.";
    const sentQuestions: string[] = [];
    await page.route("**/api/v1/copilot/chat/stream", async (route) => {
      const body = route.request().postDataJSON() as { question?: string };
      sentQuestions.push(body.question ?? "");
      const frames = [
        { type: "delta", text: MOCK_ANSWER },
        {
          type: "done",
          data: {
            answer: MOCK_ANSWER,
            citations_found: [],
            chunk_ids_used: [],
            chunks_used: [],
            not_in_corpus: false,
            low_grounding_confidence: false,
            confidence: 0.9,
            corpus_gap: false,
            model_used: "mock",
            interaction_log_id: null,
          },
        },
      ];
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join(""),
      });
    });

    // Las quick actions vienen del backend real: capturamos su prefill_query
    // para comprobar que el click envía exactamente esa consulta.
    const quickActionsResponse = page.waitForResponse((r) =>
      r.url().includes("/api/v1/copilot/quick-actions") && r.ok(),
    );

    await loginAsMarcos(context);
    await page.goto(PROJECT_PATH);
    await openPanel(page);

    const quickActions = (await (await quickActionsResponse).json()) as Array<{
      label: string;
      prefill_query: string;
    }>;
    expect(quickActions.length).toBeGreaterThan(0);
    const first = quickActions[0];

    const panel = page.getByRole("dialog");
    const action = panel
      .getByRole("list", { name: /Acciones sugeridas del copiloto/i })
      .getByRole("button", { name: first.label });
    await expect(action).toBeVisible({ timeout: 5_000 });
    await action.click();

    // Auto-envío: la consulta sugerida aparece como mensaje del usuario y llega
    // tal cual al endpoint de streaming, y la respuesta se pinta en el panel.
    // Burbuja de usuario = <p>; el composer también conserva el texto (setValue)
    // en su <textarea>, por eso se filtra por párrafo.
    await expect(
      panel.getByRole("paragraph").filter({ hasText: first.prefill_query }),
    ).toBeVisible();
    await expect(panel.getByText(MOCK_ANSWER)).toBeVisible({ timeout: 10_000 });
    expect(sentQuestions).toEqual([first.prefill_query.trim()]);
  });

  // La decisión corpus_gap (threshold sobre la confianza del retrieval) es del
  // backend y la cubren sus tests (test_copilot_corpus_fallback.py + el test
  // @pytest.mark.llm). Aquí se mockea el stream con `corpus_gap: true` y se
  // prueba lo que es del frontend: que ese flag pinta el aviso en la respuesta.
  test("Corpus gap query muestra badge warning", async ({
    context,
    page,
  }) => {
    const ANSWER = "No tengo fuente en el corpus para esa norma extranjera.";
    await page.route("**/api/v1/copilot/chat/stream", async (route) => {
      const frames = [
        { type: "delta", text: ANSWER },
        {
          type: "done",
          data: {
            answer: ANSWER,
            citations_found: [],
            chunk_ids_used: [],
            chunks_used: [],
            not_in_corpus: true,
            low_grounding_confidence: true,
            confidence: 0.2,
            corpus_gap: true,
            model_used: "mock",
            interaction_log_id: null,
          },
        },
      ];
      await route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: frames.map((f) => `data: ${JSON.stringify(f)}\n\n`).join(""),
      });
    });

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

    const panel = page.getByRole("dialog");
    await expect(panel.getByText(ANSWER)).toBeVisible({ timeout: 10_000 });
    await expect(
      panel.getByText(/Fuente no disponible aún en corpus FULKRO/i),
    ).toBeVisible();
    await snapshot(page, "04_corpus_gap_badge");
  });
});
