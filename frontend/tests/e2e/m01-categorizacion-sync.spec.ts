/**
 * E2E test · M01 Categorización sync admin → cliente.
 *
 * Sesión 3B-2B.8 CLUSTER 1 Phase 1A.3 (~5s SSE roundtrip target).
 *
 * Flow:
 * 1. Admin crea un sistema de información con un tipo de información (API M01)
 * 2. Cliente login + visita /client-portal/categorizacion (suscribe SSE)
 * 3. Admin categoriza el sistema (POST /categorize)
 * 4. Cliente ve el toast del evento SSE en ≤5s, con el nombre de ESE sistema
 * 5. audit_log registra cliente.categorizacion.viewed de este cliente en esta
 *    ejecución (leído con el export CSV del portal del auditor, que es la vía
 *    de solo lectura del audit_log por proyecto)
 *
 * AUTOSUFICIENTE: antes se saltaba sin FULKRO_TEST_PROJECT_ID +
 * FULKRO_TEST_SYSTEM_ID y en local no corría nunca. Ahora crea en runtime, con
 * las APIs admin reales, un cliente AISLADO (su único proyecto es el que el
 * portal resuelve por R27) y un sistema nuevo por ejecución. Si las dos
 * variables de entorno están definidas se usan como override (con el cliente
 * de test compartido, como hacía la versión anterior).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";
import {
  adminCsrfHeaders,
  ensureIsolatedPortalClient,
} from "./_helpers/isolated-portal-client";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

const ENV_PROJECT_ID = process.env.FULKRO_TEST_PROJECT_ID;
const ENV_SYSTEM_ID = process.env.FULKRO_TEST_SYSTEM_ID;
const SHARED_CLIENT_EMAIL = "test-client-e2e@example.com";
const CLOCK_SKEW_MS = 5_000;

test.describe("M01 Categorización sync admin → cliente E2E", () => {
  test("admin completes categorización → cliente sees update via SSE", async ({
    browser,
  }) => {
    const runStartedAt = Date.now();
    const runTag = `e2e-${runStartedAt.toString(36)}`;

    // 2 contexts paralelos (admin + cliente)
    const adminContext = await browser.newContext();
    const clienteContext = await browser.newContext();
    await loginAsMarcos(adminContext);
    const adminHeaders = await adminCsrfHeaders(adminContext);

    let projectId: string;
    let systemId: string;
    let systemNombre: string;
    let clientLogin: { email?: string; password?: string };

    if (ENV_PROJECT_ID && ENV_SYSTEM_ID) {
      projectId = ENV_PROJECT_ID;
      systemId = ENV_SYSTEM_ID;
      const list = await adminContext.request.get(
        `${BACKEND_BASE}/api/v1/categorization/projects/${projectId}/systems`,
      );
      expect(list.ok(), "GET sistemas del proyecto de env").toBeTruthy();
      const sys = ((await list.json()) as Array<{ id: string; nombre: string }>)
        .find((s) => s.id === systemId);
      expect(sys, "FULKRO_TEST_SYSTEM_ID pertenece al proyecto").toBeTruthy();
      systemNombre = sys!.nombre;
      clientLogin = {};
    } else {
      const iso = await ensureIsolatedPortalClient(adminContext, {
        cif: "B90000101",
        nombre: "Test E2E Client m01-sync",
        email: "m01-sync@e2e.fulkro.example",
        projectNombre: "Proyecto ENS E2E m01-sync",
        categoria: "MEDIA",
      });
      projectId = iso.projectId;
      clientLogin = { email: iso.email, password: iso.password };

      // Sistema NUEVO por ejecución: el toast que esperamos nombra ESTE
      // sistema, así que no puede pasar con el evento de otra ejecución.
      systemNombre = `Sistema ${runTag}`;
      const sr = await adminContext.request.post(
        `${BACKEND_BASE}/api/v1/categorization/projects/${projectId}/systems`,
        {
          headers: adminHeaders,
          data: { nombre: systemNombre, descripcion: "Alta E2E m01-sync" },
        },
      );
      expect(sr.status(), await sr.text()).toBe(201);
      systemId = ((await sr.json()) as { id: string }).id;
      const it = await adminContext.request.post(
        `${BACKEND_BASE}/api/v1/categorization/systems/${systemId}/information-types`,
        {
          headers: adminHeaders,
          data: {
            items: [
              {
                nombre: "Expedientes de licitación",
                valoracion_d: "MEDIO",
                valoracion_i: "MEDIO",
                valoracion_c: "BAJO",
                valoracion_a: "BAJO",
                valoracion_t: "BAJO",
              },
            ],
          },
        },
      );
      expect(it.status(), await it.text()).toBe(201);
    }

    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { ...clientLogin, dismissTutorial: true });
    const clientEmail = clientLogin.email ?? SHARED_CLIENT_EMAIL;

    // Cliente visita la página; esperamos a que su EventSource esté abierto
    // antes de disparar el evento (si no, el evento sale antes de que haya
    // suscriptor y el toast no llega nunca: SSE no reenvía sin Last-Event-ID).
    const sseOpen = clientePage.waitForResponse((r) =>
      r.url().includes(`/client-portal/projects/${projectId}/events`),
    );
    await clientePage.goto("/client-portal/categorizacion");
    await expect(clientePage.getByTestId("cat-view")).toBeVisible({
      timeout: 10_000,
    });
    expect((await sseOpen).status(), "SSE cliente abierto").toBe(200);

    // Admin completes M01 categorize via API call (faster than UI walkthrough)
    const resp = await adminContext.request.post(
      `${BACKEND_BASE}/api/v1/categorization/systems/${systemId}/categorize`,
      {
        headers: adminHeaders,
        data: { aprobado_por: "Marcos · E2E Test Auditor" },
      },
    );
    expect(resp.ok(), await resp.text()).toBeTruthy();
    const categoria = ((await resp.json()) as { categoria_resultante: string })
      .categoria_resultante;

    // Cliente receives SSE toast within 5s · con el sistema y la categoría
    await expect(
      clientePage.getByText(
        `ha completado la categorización de ${systemNombre} (categoría ${categoria})`,
      ),
    ).toBeVisible({ timeout: 5_000 });

    // audit_log: la visita del cliente quedó registrada (fila de ESTE cliente
    // y de esta ejecución · no vale una de ejecuciones anteriores).
    const tok = await adminContext.request.post(
      `${BACKEND_BASE}/api/v1/_dev/auditor-portal-token?project_id=${projectId}`,
    );
    expect(tok.ok()).toBeTruthy();
    const { token } = (await tok.json()) as { token: string };
    const csv = await adminContext.request.get(
      `${BACKEND_BASE}/api/v1/public/auditor-portal/${token}/audit-log.csv` +
        `?accion=cliente.categorizacion.viewed&limit=20`,
    );
    expect(csv.ok()).toBeTruthy();
    const rows = (await csv.text())
      .trim()
      .split(/\r?\n/)
      .slice(1)
      .map((line) => line.split(","));
    // Columnas: seq,tabla,accion,usuario,timestamp,payload_new
    const mine = rows.filter(
      (c) =>
        c[2] === "cliente.categorizacion.viewed" &&
        c[3] === clientEmail &&
        Date.parse(c[4]) >= runStartedAt - CLOCK_SKEW_MS,
    );
    expect(mine.length, "audit_log cliente.categorizacion.viewed").toBeGreaterThanOrEqual(1);

    await adminContext.close();
    await clienteContext.close();
  });
});
