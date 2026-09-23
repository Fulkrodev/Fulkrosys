/**
 * E2E · M02 MAGERIT: el admin congela el analisis → el cliente se entera por
 * SSE, y el cliente no puede congelar (portal READ-ONLY).
 *
 * Autosuficiente: antes se saltaba entero si no habia FULKRO_TEST_PROJECT_ID
 * y FULKRO_TEST_MAGERIT_ANALYSIS_ID, asi que no se ejecutaba nunca, y cuando
 * se ejecutaba aceptaba un 409 ("ya congelado") sin comprobar nada. Ahora
 * prepara lo que necesita por la API, como en la interfaz:
 *   1. cliente aislado (el portal muestra el proyecto MAS RECIENTE del
 *      cliente y el compartido acumula proyectos de otros specs);
 *   2. un contacto nombrado Responsable de la Seguridad (congelar se le
 *      atribuye · Anexo III 1.d · sin RSEG el backend responde 403);
 *   3. un analisis NUEVO por ejecucion, que se congela de verdad (200).
 */
import { type BrowserContext, expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";
import {
  adminCsrfHeaders,
  ensureIsolatedPortalClient,
} from "./_helpers/isolated-portal-client";

// Probabilidad MAGERIT (escala MB/B/M/A/MA del Libro II).
const PROBABILIDAD = "M";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

async function analisisCongelable(
  admin: BrowserContext,
): Promise<{ projectId: string; analysisId: string; nombre: string; email: string; password: string }> {
  const iso = await ensureIsolatedPortalClient(admin, {
    cif: "B90000102",
    nombre: "Test E2E Client m02-sync",
    email: "m02-sync@e2e.fulkro.example",
    projectNombre: "Proyecto ENS E2E m02-sync",
    categoria: "MEDIA",
  });
  const h = await adminCsrfHeaders(admin);
  const tag = Date.now().toString(36);

  const contacto = await admin.request.post(
    `${BACKEND_BASE}/api/v1/projects/${iso.projectId}/contacts`,
    {
      headers: h,
      data: {
        full_name: `RSEG E2E ${tag}`,
        email: `rseg-${tag}@e2e.fulkro.example`,
        role_title: "Responsable de la Seguridad",
        role_category: "tecnico",
      },
    },
  );
  expect(contacto.status(), await contacto.text()).toBe(201);
  const contactId = ((await contacto.json()) as { id: string }).id;
  const rol = await admin.request.patch(
    `${BACKEND_BASE}/api/v1/admin/projects/${iso.projectId}/ens-required-roles/responsable_seguridad`,
    { headers: h, data: { contact_id: contactId, notes: null } },
  );
  expect(rol.ok(), await rol.text()).toBeTruthy();

  const nombre = `Análisis E2E ${tag}`;
  const an = await admin.request.post(
    `${BACKEND_BASE}/api/v1/magerit/projects/${iso.projectId}/analysis`,
    { headers: h, data: { name: nombre } },
  );
  expect(an.status(), await an.text()).toBe(201);
  const analysisId = ((await an.json()) as { id: string }).id;

  // Congelar exige al menos un calculo de riesgo ("no risk calculations
  // exist"): un activo, una amenaza valorada y el riesgo intrinseco.
  const activos = await admin.request.post(
    `${BACKEND_BASE}/api/v1/magerit/analysis/${analysisId}/assets`,
    {
      headers: h,
      data: {
        assets: [{
          code: `SRV-${tag}`, name: "Servidor de expedientes",
          asset_type_code: "S", value_d: 6, value_i: 6, value_c: 4,
          value_a: 4, value_t: 4,
        }],
      },
    },
  );
  expect(activos.status(), await activos.text()).toBe(201);
  const assetId = ((await activos.json()) as Array<{ id: string }>)[0].id;
  const amenazas = await admin.request.post(
    `${BACKEND_BASE}/api/v1/magerit/analysis/${analysisId}/threats`,
    {
      headers: h,
      data: {
        assessments: [{
          asset_id: assetId, threat_code: "A.5", probability: PROBABILIDAD,
          degradation_d: 50, degradation_i: 50, degradation_c: 50,
          degradation_a: 0, degradation_t: 0,
        }],
      },
    },
  );
  expect(amenazas.status(), await amenazas.text()).toBe(201);
  const calculo = await admin.request.post(
    `${BACKEND_BASE}/api/v1/magerit/analysis/${analysisId}/calculate-intrinsic`,
    { headers: h },
  );
  expect(calculo.ok(), await calculo.text()).toBeTruthy();

  return { projectId: iso.projectId, analysisId, nombre, email: iso.email, password: iso.password };
}

test.describe("M02 MAGERIT sync admin → cliente READ-ONLY E2E", () => {
  test("admin congela MAGERIT → el cliente ve el aviso por SSE", async ({ browser }) => {
    const adminContext = await browser.newContext();
    const clienteContext = await browser.newContext();
    await loginAsMarcos(adminContext);
    const { projectId, analysisId, nombre, email, password } =
      await analisisCongelable(adminContext);

    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { email, password, dismissTutorial: true });
    // Esperar a que el EventSource este abierto antes de disparar el evento:
    // SSE no reenvia lo emitido antes de suscribirse.
    const sseOpen = clientePage.waitForResponse((r) =>
      r.url().includes(`/client-portal/projects/${projectId}/events`),
    );
    await clientePage.goto("/client-portal/magerit");
    expect((await sseOpen).status(), "SSE cliente abierto").toBe(200);

    const resp = await adminContext.request.post(
      `${BACKEND_BASE}/api/v1/magerit/analysis/${analysisId}/freeze`,
      { headers: await adminCsrfHeaders(adminContext) },
    );
    expect(resp.status(), await resp.text()).toBe(200);

    await expect(
      clientePage.getByText(`El consultor ha actualizado ${nombre}`),
    ).toBeVisible({ timeout: 5_000 });

    await adminContext.close();
    await clienteContext.close();
  });

  test("el cliente no puede congelar MAGERIT (portal READ-ONLY)", async ({ browser }) => {
    const adminContext = await browser.newContext();
    await loginAsMarcos(adminContext);
    const { analysisId, email, password } = await analisisCongelable(adminContext);
    await adminContext.close();

    const clienteContext = await browser.newContext();
    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { email, password, dismissTutorial: true });
    const csrf = (await clienteContext.cookies()).find((c) => c.name === "fulkro_csrf")?.value ?? "";
    // Con su CSRF valido: si falla, es por falta de permiso y no por el token.
    const resp = await clienteContext.request.post(
      `${BACKEND_BASE}/api/v1/magerit/analysis/${analysisId}/freeze`,
      { headers: { "x-csrf-token": csrf } },
    );
    expect([401, 403]).toContain(resp.status());
    await clienteContext.close();
  });
});
