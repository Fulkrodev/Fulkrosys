/**
 * Helpers E2E Playwright · acceso real al portal del auditor ENAC.
 *
 * El portal se abre con un magic-link AUDITOR_PORTAL_ENAC (requires_otp=True):
 * el token solo no basta, `AuditorPortalEntry` pide el código OTP antes de
 * arrancar la sesión (POST /session). Antes cada spec esperaba el token en
 * `AUDITOR_PORTAL_TOKEN` y se saltaba sin él, así que en local nunca corría.
 * Aquí lo acuñamos en runtime con el mismo endpoint dev que usa el CI
 * (`/_dev/auditor-portal-token`, que devuelve token + OTP), y las variables de
 * entorno siguen mandando si están definidas (override).
 */
import { expect, type APIRequestContext, type Page } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

/** Proyecto FIJO rico que siembra globalSetup (DdA ALTA + MAGERIT). */
export const FIXED_RICH_PROJECT_ID = "00000000-0000-0000-0000-000000000001";

export interface AuditorAccess {
  token: string;
  /** null si el token viene de env sin `AUDITOR_PORTAL_OTP`. */
  otp: string | null;
  projectId: string;
}

/**
 * Resuelve el acceso del auditor para un spec.
 *
 * Orden: `AUDITOR_PORTAL_TOKEN` (+ `AUDITOR_PORTAL_OTP`) de env si existe; si
 * no, se acuña uno nuevo sobre `FULKRO_TEST_PROJECT_ID` o, en su defecto, el
 * proyecto fijo rico (re-sembrado idempotente: los pasos que anotan medidas y
 * miran la matriz DdA-evidencias necesitan DdA real, y ese proyecto la tiene).
 */
export async function resolveAuditorAccess(
  request: APIRequestContext,
): Promise<AuditorAccess> {
  const envToken = process.env.AUDITOR_PORTAL_TOKEN;
  const envProject = process.env.FULKRO_TEST_PROJECT_ID;

  if (envToken) {
    let projectId = envProject;
    if (!projectId) {
      // El proyecto sale del propio token (peek de metadata · no consume uso).
      const meta = await request.get(
        `${BACKEND_BASE}/api/v1/public/auditor-portal/${envToken}`,
      );
      if (!meta.ok()) {
        throw new Error(
          `metadata del AUDITOR_PORTAL_TOKEN de env devolvió ${meta.status()}`,
        );
      }
      projectId = ((await meta.json()) as { project: { id: string } }).project
        .id;
    }
    return {
      token: envToken,
      otp: process.env.AUDITOR_PORTAL_OTP || null,
      projectId,
    };
  }

  let projectId = envProject;
  if (!projectId) {
    const rich = await request.post(
      `${BACKEND_BASE}/api/v1/_dev/seed-rich-demo-project`,
    );
    if (!rich.ok()) {
      throw new Error(
        `_dev/seed-rich-demo-project devolvió ${rich.status()} :: ${await rich.text()}`,
      );
    }
    projectId = ((await rich.json()) as { project_id: string }).project_id;
  }

  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/auditor-portal-token?project_id=${projectId}`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/auditor-portal-token devolvió ${res.status()} :: ${await res.text()}`,
    );
  }
  const body = (await res.json()) as { token: string; otp: string | null };
  return { token: body.token, otp: body.otp, projectId };
}

/**
 * Abre una sección del portal y supera el gate OTP si aparece.
 *
 * El gate se evalúa en cada montaje de `AuditorPortalEntry`, así que cada
 * `page.goto` lo vuelve a mostrar. Esperamos a que la página se decida (gate u
 * chrome del portal) en vez de mirar `isVisible()` al instante, que no espera
 * y daba por ausente un gate que aún estaba cargando la metadata.
 */
export async function openAuditorSection(
  page: Page,
  access: AuditorAccess,
  section: string,
): Promise<void> {
  await page.goto(`/auditor-portal/${access.token}/${section}`);
  const otpInput = page.getByTestId("auditor-otp-input");
  const main = page.getByTestId("auditor-portal-main");
  await expect(otpInput.or(main)).toBeVisible({ timeout: 15_000 });

  if (await otpInput.isVisible()) {
    if (!access.otp) {
      throw new Error(
        "El portal pide OTP y no hay código (define AUDITOR_PORTAL_OTP junto " +
          "a AUDITOR_PORTAL_TOKEN, o deja que el spec acuñe el token).",
      );
    }
    await otpInput.fill(access.otp);
    const sessionResp = page.waitForResponse(
      (r) =>
        r.url().includes(`/auditor-portal/${access.token}/session`) &&
        r.request().method() === "POST",
    );
    await page.getByTestId("auditor-otp-submit").click();
    expect((await sessionResp).status(), "POST /session con OTP").toBe(200);
  }
  await expect(main).toBeVisible({ timeout: 15_000 });
}
