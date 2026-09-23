/**
 * FASE 43 · #43 · Firma de CONTRATO comercial con canvas Ed25519 (E2E cliente).
 *
 * Cubre el flujo público autoritativo m13 ContractSigningFlow +
 * `contract_signing_public_api` (`/api/v1/contract-signing/{preview,confirm}`):
 *   1. El lead recibe un magic-link FIRMA_CONTRATO (OTP + geo · decisión A/B).
 *   2. Abre /sign/{token} → el multiplex (purpose `firma_contrato`) renderiza
 *      ContractCanvasSignFlow.
 *   3. Introduce el OTP, su nombre + apellido, DIBUJA su firma en el canvas
 *      (SignatureCanvas · react-signature-canvas) y confirma.
 *   4. Backend: consume magic-link + sign_canvas (Ed25519 + hash chain) +
 *      promueve el proyecto + crea el ClientUser (#7) atómicamente.
 *   5. La UI muestra el estado "Contrato firmado" + sello Ed25519.
 *
 * ── SEED ─────────────────────────────────────────────────────────────────
 * Cada ejecución siembra un contrato NUEVO por la cadena admin real y
 * determinista (la misma que sim-medio · helpers de _helpers/sim-medio.ts):
 *   create-test-client → _dev/seed-commercial-lead → proposals/generate →
 *   proposal "won" → contracts/generate (C-001) → sign-marcos → send-client
 * `send-client` devuelve `magic_link.token` + `magic_link.otp`. Cualquier fallo
 * de la cadena es un fallo del test (antes se convertía en un skip silencioso).
 *
 * Helpers reusados: loginAsMarcos (auth-real) · cadena comercial sim-medio ·
 * SignatureCanvas testIdPrefix "contract-signature" · ruta pública /sign/[token].
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";
import {
  generateContract,
  generateProposal,
  markProposalWon,
  pricingModelIdForMedia,
  seedCommercialLead,
  sendContractToClient,
  signMarcos,
} from "../_helpers/sim-medio";

test.use({ viewport: { width: 1280, height: 900 } });

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

interface SeededContract {
  token: string;
  otp: string;
}

/**
 * Lee la cookie CSRF (no httpOnly) que loginAsMarcos inyectó en el contexto ·
 * necesaria para POSTs admin (triple binding header+cookie+JWT claim).
 */
async function csrfHeader(page: Page): Promise<Record<string, string>> {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((c) => c.name === "fulkro_csrf")?.value;
  if (!csrf) {
    throw new Error("fulkro_csrf cookie ausente · loginAsMarcos no ejecutado");
  }
  return { "x-csrf-token": csrf };
}

/** Siembra un contrato C-001 nuevo, firmado por Marcos y enviado al lead. */
async function seedReadyToSignContract(
  page: Page,
  api: APIRequestContext,
): Promise<SeededContract> {
  const headers = await csrfHeader(page);
  const clientRes = await api.post(
    `${BACKEND_BASE}/api/v1/_dev/create-test-client`,
  );
  expect(clientRes.ok()).toBeTruthy();
  const { project_id: projectId } = (await clientRes.json()) as {
    project_id: string;
  };

  const lead = await seedCommercialLead(api, projectId);
  const pricingModelId = await pricingModelIdForMedia(api, headers);
  const proposal = await generateProposal(
    api, headers, projectId, lead.lead_id, pricingModelId,
  );
  await markProposalWon(api, headers, projectId, proposal.id);
  const contract = await generateContract(api, headers, projectId, proposal.id);
  await signMarcos(api, headers, projectId, contract.id);
  return sendContractToClient(
    api, headers, projectId, contract.id, "firmante-e2e@example.com",
  );
}

/**
 * Dibuja un trazo en el canvas de firma (react-signature-canvas) con eventos
 * de ratón · deja el pad NO vacío para que el submit pase la validación.
 */
async function drawSignature(page: Page, testId: string): Promise<void> {
  const canvas = page.getByTestId(testId);
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("canvas sin boundingBox");
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;
  await page.mouse.move(cx - 40, cy - 10);
  await page.mouse.down();
  await page.mouse.move(cx - 10, cy + 15, { steps: 8 });
  await page.mouse.move(cx + 25, cy - 12, { steps: 8 });
  await page.mouse.move(cx + 45, cy + 8, { steps: 8 });
  await page.mouse.up();
}

test.describe("FASE 43 · firma de contrato comercial canvas Ed25519", () => {
  test("lead firma el contrato en canvas → estado firmado (Ed25519)", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);

    const seeded = await seedReadyToSignContract(page, page.request);

    // La ruta /sign/{token} es pública · limpiamos cookies admin para firmar
    // como el lead sin sesión (la credencial es el token + OTP).
    await context.clearCookies();

    await page.goto(`/sign/${seeded.token}`);
    await page.waitForLoadState("domcontentloaded");

    // El multiplex resolvió purpose firma_contrato → ContractCanvasSignFlow.
    await expect(
      page.getByRole("heading", {
        name: /Firma de tu contrato de servicios FULKRO/i,
      }),
    ).toBeVisible({ timeout: 15_000 });

    // OTP recibido "por canal separado" (aquí · de la respuesta send-client).
    await page.getByLabel(/Código OTP de verificación/i).fill(seeded.otp);

    // Nombre + apellido del firmante (SignatureCanvas testIdPrefix contract-signature).
    await page
      .getByTestId("contract-signature-name-input")
      .fill("Ana");
    await page
      .getByTestId("contract-signature-surname-input")
      .fill("Firmante");

    // Dibuja la firma manuscrita.
    await drawSignature(page, "contract-signature-pad");

    // Confirma · POST /contract-signing/confirm (consume + sign_canvas).
    await page.getByTestId("contract-signature-submit").click();

    // Estado final · contrato firmado + sello Ed25519.
    await expect(
      page.getByRole("heading", { name: /Contrato firmado/i }),
    ).toBeVisible({ timeout: 20_000 });
    await expect(
      page.getByText(/sellada criptográficamente \(Ed25519\)/i),
    ).toBeVisible();
  });
});
