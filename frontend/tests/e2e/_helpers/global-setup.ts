/**
 * Playwright globalSetup — runs once before all tests.
 *
 * Crea cliente E2E sintético idempotente via /api/v1/_dev/create-test-client.
 * El endpoint es env-gated (404 en producción).
 *
 * Si el endpoint falla, los tests separación-portales fallarán al
 * intentar loginAsClient. Mejor fallar aquí con error claro que dejar
 * que cada test descubra el mismo problema.
 */
import { request } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

async function globalSetup(): Promise<void> {
  const ctx = await request.newContext();
  try {
    const res = await ctx.post(`${BACKEND_BASE}/api/v1/_dev/create-test-client`);
    if (!res.ok()) {
      throw new Error(
        `_dev/create-test-client devolvió ${res.status()}. ` +
          `¿Backend running en ${BACKEND_BASE}? ¿app_env != "production"?`,
      );
    }
    const data = (await res.json()) as {
      email: string;
      user_id: string;
      role: string;
    };
    // eslint-disable-next-line no-console
    console.log(
      `[globalSetup] Cliente E2E listo: ${data.email} (${data.user_id}, role=${data.role})`,
    );

    // Proyecto FIJO E2E rico (UUID determinista 00000000-…-001) que las specs
    // SAN-E v3 (san_e_v3/mb3_* + mb4_*) y admin-settings hardcodean. Sin él las
    // páginas project-scoped muestran el gate "proyecto no encontrado" y ~38
    // specs fallan en cascada. Idempotente · best-effort (si el endpoint no
    // existe en una rama antigua, NO bloquea el resto de la suite).
    try {
      const rich = await ctx.post(
        `${BACKEND_BASE}/api/v1/_dev/seed-rich-demo-project`,
      );
      if (rich.ok()) {
        const r = (await rich.json()) as {
          project_id: string;
          assets_count: number;
          risks_count: number;
          dda_entries_count: number;
        };
        // eslint-disable-next-line no-console
        console.log(
          `[globalSetup] Proyecto fijo E2E sembrado: ${r.project_id} ` +
            `(${r.assets_count} assets · ${r.risks_count} risks · ` +
            `${r.dda_entries_count} DdA entries)`,
        );
      } else {
        // eslint-disable-next-line no-console
        console.warn(
          `[globalSetup] seed-rich-demo-project devolvió ${rich.status()} ` +
            `· specs project-scoped fijo (san_e_v3) pueden fallar.`,
        );
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[globalSetup] seed-rich-demo-project no disponible:", err);
    }
  } finally {
    await ctx.dispose();
  }
}

export default globalSetup;
