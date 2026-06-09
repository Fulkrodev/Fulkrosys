/**
 * Fixtures compartidos · fase_22 sub-atom 1.D.B.2 v3.11 · Copiloto admin LLM real.
 *
 * Cubre swap-in stub → LLM real admin Sonnet 4.6:
 *   - sidebar render con LLM badge (mode indicator)
 *   - QuickAction trigger + LLM response render
 *   - R30 boundary defensive enrich (tip tutor footer) cuando LLM viola
 *   - Error inline en history (NO red alarm · amber friendly)
 *   - Stub fallback disclaimer cuando is_stub=true
 *
 * Pattern reuse · OPS-045 16ª aplicación consecutiva: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend (paridad
 * fase_17/18/19/20/21).
 */
import type { Page } from "@playwright/test";

// Reuse del payload cronológica de fase_17 · DRY. El CopilotoAdminSidebar vive
// dentro de ProjectCronologicaView, que hace fetch real de la cronológica WCC.
// El proyecto fijo E2E NO tiene datos WCC sembrados → el view error-statea con
// "Project not found" y el sidebar nunca monta. Mockeamos ese endpoint para que
// la vista (y el sidebar copiloto) rendericen.
import { MOCK_CRONOLOGICA_RESPONSE } from "../fase_17/_fixtures";

// FIX specs UI evolucionada: el UUID hardcodeado viejo nunca se siembra. El
// proyecto fijo E2E sembrado por globalSetup (seed-rich-demo-project) usa el
// UUID determinista 00000000-…-001 (ALTA). Apuntamos ahí para que el layout
// project-scoped resuelva el proyecto real (header/tabs/WCC cronológica) ·
// los endpoints de copiloto siguen mockeados. Mismo patrón que san_e_v3.
export const PROJECT_DDD_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

// ============================================================
// Mock chat responses admin (LLM Sonnet 4.6 · tutor cronológico R30)
// ============================================================

export const MOCK_ADMIN_RESPONSE_LLM_REAL = {
  action_id: "que_hago",
  response_text:
    "El siguiente paso del cliente es completar el DICAT · que significa " +
    "Declaración Inicial de Categorización · es decir el documento donde " +
    "se decide oficialmente si el sistema es BÁSICO · MEDIO o ALTO según " +
    "el impacto de seguridad evaluado. Cita: RD 311/2022 Anexo I.",
  is_stub: false,
  next_action_hint: "Marca el sub-paso completo cuando esté hecho",
  citations: [],
};

export const MOCK_ADMIN_RESPONSE_LLM_ENRICHED = {
  action_id: "explica_paso",
  response_text:
    "Como ya sabes el DdA es obligatorio para certificar ENS · debes " +
    "completarlo antes que el resto del workflow continúe.\n\n---\n" +
    "💡 _Tip tutor: Si quieres que profundice en algún concepto ENS · " +
    "pregúntame y te lo explico desde primer principios._",
  is_stub: false,
  next_action_hint: null,
  citations: [],
};

export const MOCK_ADMIN_RESPONSE_STUB_FALLBACK = {
  action_id: "que_hago",
  response_text:
    'Próximo step "del cliente actual": "el sub-paso actual". Te ayudo a ' +
    "redactar contexto si lo necesitas. (LLM completo disponible en breve · " +
    "próximo sprint)",
  is_stub: true,
  next_action_hint: "Marca el sub-paso completo cuando esté hecho",
  citations: [],
};

// ============================================================
// Mock route helpers
// ============================================================

/**
 * Mockea el endpoint cronológica WCC para que ProjectCronologicaView renderice
 * (y con él el CopilotoAdminSidebar). Wildcard sobre cualquier project id ·
 * el view renderiza del payload sin validar project_id contra la URL.
 */
export async function mockCronologicaForCopilotAdmin(page: Page) {
  await page.route(
    "**/api/v1/admin/workflow-command-center/projects/*",
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CRONOLOGICA_RESPONSE });
    },
  );
}

export async function mockCopilotoAdminChatLLM(page: Page) {
  await page.route("**/api/v1/admin/copilot/chat", async (route) => {
    const body = route.request().postDataJSON() as { action_id: string };
    if (body.action_id === "explica_paso") {
      await route.fulfill({
        status: 200,
        json: MOCK_ADMIN_RESPONSE_LLM_ENRICHED,
      });
    } else {
      await route.fulfill({
        status: 200,
        json: MOCK_ADMIN_RESPONSE_LLM_REAL,
      });
    }
  });
}

export async function mockCopilotoAdminChatError(page: Page) {
  await page.route("**/api/v1/admin/copilot/chat", async (route) => {
    await route.fulfill({
      status: 500,
      json: { detail: "LLM upstream error" },
    });
  });
}

export async function mockCopilotoAdminChatStubFallback(page: Page) {
  await page.route("**/api/v1/admin/copilot/chat", async (route) => {
    await route.fulfill({
      status: 200,
      json: MOCK_ADMIN_RESPONSE_STUB_FALLBACK,
    });
  });
}

/**
 * Patterns "assume ENS knowledge" prohibidos R30 sostener empíricamente.
 * Pero NO siempre auditados strict en E2E · pueden aparecer si LLM viola
 * y endpoint enrich con tip tutor footer (defensive · NO fallback total).
 */
export const R30_ASSUME_PATTERNS = [
  "como ya sabes",
  "como conoces",
  "evidentemente",
  "obviamente",
];

/**
 * Definition triggers que cuando aparecen cerca de jargon ENS sostienen R30.
 */
export const R30_DEFINITION_TRIGGERS = [
  "es decir",
  "que significa",
  "es el",
  "es la",
  "se refiere a",
];
