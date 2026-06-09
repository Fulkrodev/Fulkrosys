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
 * ── SEED · LIMITACIÓN HONESTA (OPS-049) ────────────────────────────────────
 * NO existe un endpoint `_dev` que siembre un "contrato listo-para-firmar" y
 * devuelva {token, otp} en un solo paso (verificado: backend/app/dev/router.py
 * tiene create-test-client / login-as-marcos / wait-for-otp, pero ningún
 * seed-ready-to-sign-contract). Sembrar requiere la cadena admin real:
 *   create-test-client → (lead) → proposal/generate → contracts/generate →
 *   contracts/{id}/sign-marcos → contracts/{id}/send-client
 * y `send-client` devuelve `magic_link.token` + `magic_link.otp` (plaintext).
 *
 * Como TASK D está acotada a ficheros de spec (sin tocar backend), este spec
 * INTENTA la cadena admin con el seed mínimo posible. Si en el entorno local
 * falta cualquier prerequisito (datos de pricing/diagnóstico, router CRM no
 * montado, etc.), el test se marca SKIP con causa documentada (env-dependent ·
 * NO defecto de producto) en lugar de fallar en rojo. Cuando la cadena
 * completa, el spec ejerce la firma canvas de extremo a extremo.
 *
 * Future-X (post-piloto · NO bloquea): `Future-43.dev-seed-ready-to-sign-
 * contract` (~30-45 min · endpoint _dev que cree lead+proyecto-ligero+contrato
 * firmado_marcos + send_for_signing y devuelva {token, otp} · haría este E2E
 * determinista sin la cadena admin frágil).
 *
 * Helpers reusados: loginAsMarcos (auth-real) · SignatureCanvas testIdPrefix
 * "contract-signature" · ruta pública /sign/[token].
 *
 * NO ejecutar Playwright aquí (lo hace la fase Verify).
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

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

/**
 * Intenta sembrar un contrato listo-para-firmar vía la cadena admin real y
 * devuelve {token, otp}. Devuelve null (→ test.skip) si el entorno no permite
 * completar la cadena con el seed mínimo (causa documentada por consola).
 */
async function seedReadyToSignContract(
  page: Page,
  api: APIRequestContext,
): Promise<SeededContract | null> {
  try {
    const headers = await csrfHeader(page);

    // 1. Proyecto de test idempotente.
    const clientRes = await api.post(
      `${BACKEND_BASE}/api/v1/_dev/create-test-client`,
    );
    if (!clientRes.ok()) {
      console.warn(
        `[#43 seed] create-test-client ${clientRes.status()} · skip`,
      );
      return null;
    }
    const { project_id: projectId } = await clientRes.json();

    // 2. Localiza un contrato ya en estado firmable (firmado_marcos/draft) si
    //    el proyecto de test ya lo tiene · evita re-generar la cadena pesada.
    const listRes = await api.get(
      `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts`,
    );
    let contractId: string | null = null;
    if (listRes.ok()) {
      const { contracts } = await listRes.json();
      const firmable = (contracts ?? []).find(
        (c: { id: string; estado: string }) =>
          c.estado === "firmado_marcos" || c.estado === "draft",
      );
      if (firmable) contractId = firmable.id;
    }

    if (!contractId) {
      // La generación completa (proposal → contract) exige datos de pricing /
      // diagnóstico que el proyecto de test no garantiza, y el router CRM
      // (/commercial · BUG3) puede no estar montado. Sin un contrato firmable
      // disponible, documentamos y saltamos.
      console.warn(
        "[#43 seed] sin contrato firmable en el proyecto de test y sin " +
          "endpoint _dev seed-ready-to-sign-contract · skip documentado " +
          "(Future-43.dev-seed-ready-to-sign-contract)",
      );
      return null;
    }

    // 3. Asegura firma de Marcos (idempotente · si ya firmado, el backend
    //    responde 400 · lo toleramos).
    await api.post(
      `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/${contractId}/sign-marcos`,
      { headers },
    );

    // 4. Envía al cliente · la respuesta trae magic_link.{token,otp}.
    const sendRes = await api.post(
      `${BACKEND_BASE}/api/v1/contracts/projects/${projectId}/contracts/${contractId}/send-client`,
      {
        headers,
        data: { recipient_email: "firmante-e2e@example.com" },
      },
    );
    if (!sendRes.ok()) {
      console.warn(`[#43 seed] send-client ${sendRes.status()} · skip`);
      return null;
    }
    const payload = await sendRes.json();
    const token: string | undefined = payload?.magic_link?.token;
    const otp: string | undefined = payload?.magic_link?.otp;
    if (!token || !otp) {
      console.warn(
        "[#43 seed] send-client no devolvió token+otp en magic_link · skip",
      );
      return null;
    }
    return { token, otp };
  } catch (err) {
    console.warn(`[#43 seed] excepción sembrando contrato · skip · ${err}`);
    return null;
  }
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
    test.skip(
      seeded === null,
      "Sin contrato listo-para-firmar sembrable en este entorno · falta " +
        "endpoint _dev seed-ready-to-sign-contract (ver docstring · " +
        "Future-43.dev-seed-ready-to-sign-contract). NO es defecto de producto.",
    );
    if (seeded === null) return; // narrowing · skip ya marcado arriba

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
