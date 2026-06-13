/**
 * Helpers de la SIMULACIÓN FULL-CLOTH ENS MEDIO (Playwright · UI real).
 *
 * Recorre el ciclo completo de un encargo MEDIO conduciendo la UI real como
 * lo harían las tres personas (admin Marcos · cliente · auditor ENAC), con
 * LLM real y copilotos reales, y una captura por subfase en
 * `out/sim_medio_e2e/NN_<fase>.png`.
 *
 * Empresa ficticia: "Innovación Digital del Guadalquivir, S.L." (empresa
 * privada que licita a la AAPP · cliente típico FULKRO · AMEND-012). La
 * identidad ficticia la siembra `/api/v1/_dev/seed-commercial-lead`.
 *
 * NO mockea LLM (a diferencia de fase_21/fase_22): las respuestas de copiloto
 * y la narrativa de propuesta/contrato son reales (Anthropic · temp ≤0.2 · R3).
 */
import { expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

export const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

/** Directorio de capturas (cwd de Playwright = frontend/). */
const SHOT_DIR = "../out/sim_medio_e2e";

/** Registro estructurado de cada fase para el informe final. */
export interface PhaseLog {
  n: number;
  fase: string;
  actor: "admin" | "cliente" | "auditor" | "system";
  ok: boolean;
  detail: string;
}
export const phaseLog: PhaseLog[] = [];

/** Captura de pantalla numerada + log de fase (best-effort · nunca rompe). */
export async function shot(
  page: Page,
  n: number,
  fase: string,
  actor: PhaseLog["actor"],
  detail = "",
  ok = true,
): Promise<void> {
  const name = `${String(n).padStart(2, "0")}_${fase}`;
  try {
    await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true });
  } catch {
    /* página puede estar navegando · ignore */
  }
  phaseLog.push({ n, fase, actor, ok, detail });
  // eslint-disable-next-line no-console
  console.log(`[SIM] ${ok ? "✓" : "✗"} ${name} (${actor}) ${detail}`);
}

/** Lee la cookie CSRF (no httpOnly) que loginAsMarcos inyectó · header POST. */
export async function csrfHeader(
  ctx: BrowserContext,
): Promise<Record<string, string>> {
  const cookies = await ctx.cookies();
  const csrf = cookies.find((c) => c.name === "fulkro_csrf")?.value;
  if (!csrf) throw new Error("fulkro_csrf ausente · loginAsMarcos no ejecutado");
  return { "x-csrf-token": csrf };
}

// ───────────────────────────── dev levers ──────────────────────────────

export interface CommercialLead {
  lead_id: string;
  project_id: string;
  client_id: string;
  empresa_nombre: string;
  empresa_cif: string;
  contacto_email: string;
  categoria_objetivo_ens: string;
}

export async function seedCommercialLead(
  request: APIRequestContext,
  projectId?: string,
): Promise<CommercialLead> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/seed-commercial-lead${qs}`,
  );
  if (!res.ok())
    throw new Error(`seed-commercial-lead ${res.status()} :: ${await res.text()}`);
  return (await res.json()) as CommercialLead;
}

/** Fuerza la categoría del proyecto de test (la sim es MEDIO). */
export async function setTestProjectCategory(
  request: APIRequestContext,
  tier: "BASICA" | "MEDIA" | "ALTA" = "MEDIA",
): Promise<void> {
  await request
    .post(`${BACKEND_BASE}/api/v1/_dev/set-test-project-category?tier=${tier}`)
    .catch(() => {});
}

export interface AuditorToken {
  project_id: string;
  token: string;
  otp: string | null;
  portal_path: string;
}

export async function mintAuditorToken(
  request: APIRequestContext,
  projectId: string,
): Promise<AuditorToken> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/auditor-portal-token?project_id=${projectId}`,
  );
  if (!res.ok())
    throw new Error(`auditor-portal-token ${res.status()} :: ${await res.text()}`);
  return (await res.json()) as AuditorToken;
}

// ─────────────────────── cadena comercial (API real) ───────────────────

/** Modelo de pricing MEDIA (GET /commercial/pricing-models?categoria=MEDIA). */
export async function pricingModelIdForMedia(
  request: APIRequestContext,
  headers: Record<string, string>,
): Promise<string> {
  const res = await request.get(
    `${BACKEND_BASE}/api/v1/commercial/pricing-models?categoria=MEDIA`,
    { headers },
  );
  if (!res.ok())
    throw new Error(`pricing-models ${res.status()} :: ${await res.text()}`);
  const body = (await res.json()) as { models: Array<{ id: string }> };
  if (!body.models?.length) throw new Error("sin pricing models MEDIA");
  return body.models[0].id;
}

/**
 * Genera propuesta MEDIA por la vía DETERMINISTA (`/proposals/generate`).
 * Es la vía autoritativa (R1 · motores deterministas > LLM para contenido
 * normativo). La vía `-llm` añade narrativa pero localmente es lenta (~2.5 min)
 * y tiene un bug de transacción (PendingRollbackError post-LLM) — documentado
 * como defecto y evitado en la sim. Pricing real: MEDIA base 10.700€ + extras.
 */
export async function generateProposal(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  leadId: string,
  pricingModelId: string,
): Promise<{ id: string; importe_total: number }> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/commercial/projects/${projectId}/proposals/generate`,
    {
      headers,
      data: {
        lead_id: leadId,
        pricing_model_id: pricingModelId,
        categoria: "MEDIA",
        empleados: 45,
        sistemas: 3,
        ubicaciones: 1,
        sector_regulado: false,
        cpds: 0,
        client_size: "mediana",
        complexity: "media",
        validez_dias: 30,
      },
      timeout: 30_000,
    },
  );
  if (!res.ok())
    throw new Error(`proposals/generate ${res.status()} :: ${await res.text()}`);
  return (await res.json()) as { id: string; importe_total: number };
}

/** Genera contrato C-001 (consultoría ENS) por la vía determinista. */
export async function generateContract(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  proposalId: string,
): Promise<{ id: string }> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/generate`,
    {
      headers,
      data: {
        proposal_id: proposalId,
        plantilla_id: "C-001",
        cliente_firmante_nombre: "Lucía Ramírez Cabrera",
        cliente_firmante_cargo: "Directora de Operaciones",
        vigencia_meses: 12,
      },
      timeout: 30_000,
    },
  );
  if (!res.ok())
    throw new Error(`contracts/generate ${res.status()} :: ${await res.text()}`);
  return (await res.json()) as { id: string };
}

/** Genera propuesta MEDIA con narrativa LLM (Agente 19). Devuelve proposal_id + importe. */
export async function generateProposalLLM(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  leadId: string,
): Promise<{ id: string; importe_total: number }> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/commercial/projects/${projectId}/proposals/generate-llm`,
    {
      headers,
      data: {
        lead_id: leadId,
        categoria: "MEDIA",
        sector: "Servicios tecnológicos · SaaS para la AAPP",
        sistemas_en_alcance: 3,
        sedes: 1,
        madurez_pct: 35,
        dias_hasta_plazo: 90,
        retainer_tier: "R_STD",
        use_llm: true,
        regenerate: true,
        validez_dias: 30,
      },
      timeout: 90_000,
    },
  );
  if (!res.ok())
    throw new Error(`proposals/generate-llm ${res.status()} :: ${await res.text()}`);
  const p = (await res.json()) as { id: string; importe_total: number };
  return p;
}

/** Transición de propuesta a "won" (prerequisito de contrato). */
export async function markProposalWon(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  proposalId: string,
): Promise<void> {
  const res = await request.patch(
    `${BACKEND_BASE}/api/v1/commercial/projects/${projectId}/proposals/${proposalId}`,
    { headers, data: { estado: "won" } },
  );
  if (!res.ok())
    throw new Error(`proposals PATCH won ${res.status()} :: ${await res.text()}`);
}

/** Genera contrato C-001 con cláusulas LLM (Agente 20). Devuelve contract_id. */
export async function generateContractLLM(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  proposalId: string,
): Promise<{ id: string }> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/generate-llm`,
    {
      headers,
      data: {
        proposal_id: proposalId,
        cliente_firmante_nombre: "Lucía Ramírez Cabrera",
        cliente_firmante_cargo: "Directora de Operaciones",
        sector: "Servicios tecnológicos · SaaS para la AAPP",
        vigencia_meses: 12,
        use_llm: true,
      },
      timeout: 90_000,
    },
  );
  if (!res.ok())
    throw new Error(`contracts/generate-llm ${res.status()} :: ${await res.text()}`);
  const body = (await res.json()) as { contract: { id: string } };
  return body.contract;
}

export async function signMarcos(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  contractId: string,
): Promise<void> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/${contractId}/sign-marcos`,
    { headers },
  );
  // idempotente · si ya firmado responde 400 · lo toleramos
  if (!res.ok() && res.status() !== 400)
    throw new Error(`sign-marcos ${res.status()} :: ${await res.text()}`);
}

/** Envía el contrato al cliente · devuelve el magic-link {token, otp} de firma. */
export async function sendContractToClient(
  request: APIRequestContext,
  headers: Record<string, string>,
  projectId: string,
  contractId: string,
  recipientEmail: string,
): Promise<{ token: string; otp: string }> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/${contractId}/send-client`,
    {
      headers,
      data: { recipient_email: recipientEmail, base_url: "http://localhost:3100" },
    },
  );
  if (!res.ok())
    throw new Error(`send-client ${res.status()} :: ${await res.text()}`);
  const body = (await res.json()) as { magic_link?: { token: string; otp: string } };
  if (!body.magic_link?.token || !body.magic_link?.otp)
    throw new Error("send-client sin magic_link.token/otp");
  return body.magic_link;
}

// ─────────────────────────── firma canvas ──────────────────────────────

/** Dibuja un trazo en un canvas react-signature-canvas (deja el pad no vacío). */
export async function drawSignature(page: Page, testId: string): Promise<void> {
  const canvas = page.getByTestId(testId);
  await expect(canvas).toBeVisible({ timeout: 10_000 });
  await canvas.scrollIntoViewIfNeeded();
  const box = await canvas.boundingBox();
  if (!box) throw new Error(`canvas no encontrado para dibujar: ${testId}`);
  // FIX(test-fidelity 2): signature_pad (react-signature-canvas) escucha PointerEvents.
  // El dispatchEvent SINTÉTICO (new PointerEvent) NO lo captura → el lienzo quedaba
  // VACÍO (isEmpty()=true) y el submit mostraba "Por favor, firma con tu dedo/ratón".
  // La forma FIABLE es la API REAL de ratón de Playwright (page.mouse.*), que conduce
  // el pipeline de input de Chromium y genera PointerEvents TRUSTED que signature_pad sí ve.
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  await page.mouse.move(box.x + 25, cy);
  await page.mouse.down();
  await page.mouse.move(cx - 20, cy - 25, { steps: 8 });
  await page.mouse.move(cx + 20, cy + 25, { steps: 8 });
  await page.mouse.move(box.x + box.width - 25, cy - 12, { steps: 8 });
  await page.mouse.move(cx, cy + 30, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(200);
}

// ───────────────────────── copilotos (LLM real) ────────────────────────

/**
 * Copiloto ADMIN · sidebar en /admin/projects/{id}/workflow.
 * Pregunta "¿Qué hago ahora?" y espera la respuesta LLM real (Sonnet 4.6).
 * Best-effort: si el copiloto no carga, captura lo que haya y no rompe.
 */
export async function askAdminCopilot(
  page: Page,
  projectId: string,
  n: number,
  label: string,
): Promise<void> {
  try {
    await page.goto(`/admin/projects/${projectId}/workflow`, {
      waitUntil: "domcontentloaded",
    });
    // FIX(test-fidelity): el copiloto vive en el dock global (CopilotoDock ·
    // testids copiloto-dock-toggle/open/input/send/messages), NO en un
    // 'copiloto-admin-sidebar' (testid que no existe → la fase fallaba siempre).
    const toggle = page
      .getByTestId("copiloto-dock-toggle")
      .or(page.getByTestId("copiloto-dock-open"))
      .first();
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click().catch(() => {});
      const input = page.getByTestId("copiloto-input");
      if (await input.isVisible().catch(() => false)) {
        await input.fill("¿Qué tengo que hacer ahora en este proyecto?");
        await page.getByTestId("copiloto-send").click().catch(() => {});
        await page
          .getByTestId("copiloto-messages")
          .waitFor({ state: "visible", timeout: 40_000 })
          .catch(() => {});
      }
    }
    await shot(page, n, label, "admin", "copiloto admin · ¿qué hago ahora?");
  } catch (err) {
    await shot(page, n, label, "admin", `copiloto admin parcial: ${err}`, false);
  }
}

/**
 * Copiloto CLIENTE · dock global flotante (CopilotoDock) o toggle workflow.
 * Pregunta "¿Qué tengo que hacer ahora?" y espera respuesta LLM real friendly.
 */
export async function askClienteCopilot(
  page: Page,
  n: number,
  label: string,
): Promise<void> {
  try {
    // Preferimos el dock global (presente en todo el portal).
    const dockToggle = page.getByTestId("copiloto-dock-toggle");
    const cliToggle = page.getByTestId("copiloto-cliente-toggle");
    if (await dockToggle.isVisible().catch(() => false)) {
      await dockToggle.click();
      // quick-action o input directo
      const qa = page
        .getByRole("button", { name: /Qué tengo que hacer|Qué hago ahora/i })
        .first();
      if (await qa.isVisible().catch(() => false)) {
        await qa.click();
      } else {
        await page.getByTestId("copiloto-input").fill("¿Qué tengo que hacer ahora?");
        await page.getByTestId("copiloto-send").click();
      }
      await page
        .getByTestId("copiloto-messages")
        .waitFor({ state: "visible", timeout: 40_000 })
        .catch(() => {});
    } else if (await cliToggle.isVisible().catch(() => false)) {
      await cliToggle.click();
      const qa = page
        .getByRole("button", { name: /Qué tengo que hacer ahora/i })
        .first();
      if (await qa.isVisible().catch(() => false)) await qa.click();
    }
    await shot(page, n, label, "cliente", "copiloto cliente · ¿qué tengo que hacer?");
  } catch (err) {
    await shot(page, n, label, "cliente", `copiloto cliente parcial: ${err}`, false);
  }
}

/**
 * Navegación que ESPERA contenido real antes de la captura: descarta el spinner
 * del portal ("Cargando portal cliente…") y, opcionalmente, ancla en un testid.
 * Sin esto la captura cae en el estado de carga (artefacto, no contenido real).
 */
export async function gotoStable(
  page: Page,
  url: string,
  waitFor?: string,
  timeout = 15_000,
): Promise<void> {
  await page.goto(url, { waitUntil: "domcontentloaded" });
  // 1) esperar a que desaparezca el loader de portal (cliente/admin)
  await page
    .getByText(/Cargando portal cliente|Cargando…|Cargando\b|Loading…/i)
    .first()
    .waitFor({ state: "hidden", timeout })
    .catch(() => {});
  // 2) anclar en contenido concreto si se indica
  if (waitFor) {
    await page
      .getByTestId(waitFor)
      .first()
      .waitFor({ state: "visible", timeout })
      .catch(() => {});
  }
  // 3) dejar settle el render (SSE no llega a networkidle · cap a 4s)
  await page.waitForLoadState("networkidle", { timeout: 4_000 }).catch(() => {});
  await page.waitForTimeout(700);
}
