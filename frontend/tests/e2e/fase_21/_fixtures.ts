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
import type { Page } from "@playwright/test";

export const PROJECT_BB_ID = "11223344-5566-7788-99aa-bbccddeeff00";

// ============================================================
// Mock chat responses (LLM enabled · friendly cliente · R29 clean)
// ============================================================

export const MOCK_CHAT_RESPONSE_FRIENDLY_LLM = {
  action_id: "que_hago",
  response_text:
    "¡Hola! Tu próximo paso es completar la categorización de tu empresa. " +
    "Es como el DNI de tu proyecto ENS · la primera pieza del puzle. Si " +
    "tienes dudas · pregúntame · sin prisa · a tu ritmo.",
  is_stub: false,
  next_action_hint: "Cuando termines · márcalo como hecho",
  citations: [],
};

export const MOCK_CHAT_RESPONSE_STUB_FALLBACK = {
  action_id: "que_hago",
  response_text:
    'Tu siguiente paso es "Categorización inicial". Si tienes dudas sobre ' +
    "cómo abordarlo · estoy aquí para explicarte. Sin prisa · avanzamos a tu " +
    "ritmo.",
  is_stub: true,
  next_action_hint: "Cuando termines · márcalo como hecho",
  citations: [],
};

export const MOCK_CHAT_RESPONSE_PORQUE_IMPORTA = {
  action_id: "porque_importa",
  response_text:
    "La categorización es importante porque define qué medidas ENS aplicar " +
    "a tu empresa. Imagina que tienes que proteger tu casa: necesitas saber " +
    "primero si guardas joyas o solo libros viejos. Sin esa decisión inicial " +
    "no sabes qué cerraduras necesitas.",
  is_stub: false,
  next_action_hint: null,
  citations: [],
};

// ============================================================
// Mock route helpers
// ============================================================

/**
 * Mock client copilot chat endpoint · responde con LLM friendly real response.
 */
export async function mockCopilotoClienteChatLLM(page: Page) {
  await page.route(
    "**/api/v1/client-portal/copilot/chat",
    async (route) => {
      const request = route.request();
      const body = request.postDataJSON() as { action_id: string };
      if (body.action_id === "porque_importa") {
        await route.fulfill({
          status: 200,
          json: MOCK_CHAT_RESPONSE_PORQUE_IMPORTA,
        });
      } else {
        await route.fulfill({
          status: 200,
          json: MOCK_CHAT_RESPONSE_FRIENDLY_LLM,
        });
      }
    },
  );
}

/**
 * Mock client copilot chat endpoint con error 500 · verify graceful fallback.
 */
export async function mockCopilotoClienteChatError(page: Page) {
  await page.route(
    "**/api/v1/client-portal/copilot/chat",
    async (route) => {
      await route.fulfill({
        status: 500,
        json: { detail: "LLM upstream error" },
      });
    },
  );
}

/**
 * Mock client copilot chat con stub fallback response (is_stub=true).
 */
export async function mockCopilotoClienteChatStubFallback(page: Page) {
  await page.route(
    "**/api/v1/client-portal/copilot/chat",
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_CHAT_RESPONSE_STUB_FALLBACK,
      });
    },
  );
}

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
