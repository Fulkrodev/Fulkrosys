/**
 * Fixtures compartidos · fase_21 sub-atom 1.D.B.1 v3.11 · Copiloto cliente LLM real.
 *
 * Cubre swap-in stub → LLM real cliente:
 *   - chat render con respuesta LLM (mocked)
 *   - R29 boundary audit · 0 coercitive strings post-response
 *   - Loading state · typing 3 dots animation
 *   - Error fallback · system_error inline en log + friendly tone
 *
 * Pattern reuse · OPS-045 15ª aplicación consecutiva: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 */
import { expect, type Page } from "@playwright/test";

export const PROJECT_BB_ID = "11223344-5566-7788-99aa-bbccddeeff00";

// ============================================================
// Mock chat responses (LLM enabled · friendly cliente · R29 clean)
// ============================================================

// ============================================================
// Mock route helpers
// ============================================================

/**
 * Patrones coercitivos prohibidos R29 · audit empírico E2E.
 */
export const COERCITIVE_PATTERNS = [
  "llevas",
  "deadline urgente",
  "se acaba el tiempo",
  "tienes que ahora",
  "ya deberías",
  "estás retrasado",
  "fecha límite",
];

/**
 * Patrones admin lingo prohibidos cliente-facing (R30 inverso).
 */
export const ADMIN_LINGO_PATTERNS = [
  "evidence_type_id",
  "audit trail",
  "rbac",
  "tenant context",
];


// ─────────────────────────────────────────────────────────────────────────
// CopilotoDock (el copiloto de cliente UNICO desde feat/fulkro-100). Habla por
// SSE con /client-portal/copiloto/chat/stream; el widget anterior
// (copiloto-cliente-*, /client-portal/copilot/chat) ya no existe.
// ─────────────────────────────────────────────────────────────────────────

const DOCK_STREAM = "**/api/v1/client-portal/copiloto/chat/stream";

function sse(texto: string): string {
  return (
    `data: ${JSON.stringify({ type: "start", chunks_used: 1 })}\n\n` +
    `data: ${JSON.stringify({ type: "delta", text: texto })}\n\n` +
    "data: [DONE]\n\n"
  );
}

export async function mockCopilotoDockStream(
  page: Page,
  texto: string,
  opciones: { retrasoMs?: number } = {},
) {
  await page.route(DOCK_STREAM, async (route) => {
    if (opciones.retrasoMs) {
      await new Promise((r) => setTimeout(r, opciones.retrasoMs));
    }
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: sse(texto),
    });
  });
}

export async function mockCopilotoDockError(page: Page) {
  await page.route(DOCK_STREAM, (route) =>
    route.fulfill({ status: 500, json: { detail: "Internal Server Error" } }),
  );
}

export const RESPUESTA_DOCK_AMABLE =
  "Tu siguiente paso es la **categorización**: es como el DNI de tu proyecto ENS. " +
  "Marcos te acompaña en cada paso, sin prisa por tu parte.";

/** Abre el dock y pulsa la primera accion rapida que ofrezca la pagina. */
export async function abrirDockYPreguntar(page: Page) {
  await page.getByTestId("copiloto-dock-toggle").click();
  await expect(page.getByTestId("copiloto-dock-open")).toBeVisible();
  const accion = page.getByTestId("copiloto-messages").getByRole("button").first();
  await expect(accion).toBeVisible({ timeout: 10_000 });
  await accion.click();
}
