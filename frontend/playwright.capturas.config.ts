/**
 * Playwright config dedicado · capturas reales del producto para la landing.
 *
 * Reutiliza la maquinaria de tests/polish (loginAsClient, viewport sweep) pero
 * con un único worker secuencial y SIN webServer propio: asume el dev server ya
 * corriendo en :3000 (PLAYWRIGHT_PORT). El seeding del proyecto demo NovaEdge y
 * el token de auditor los prepara el orquestador `scripts/capturas_landing.py`
 * (que escribe tests/capturas/.capturas-config.json antes de lanzar esto).
 *
 * Ejecutar (normalmente vía el orquestador):
 *   cd frontend
 *   PLAYWRIGHT_PORT=3000 npx playwright test --config=playwright.capturas.config.ts
 */
import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 3000);

export default defineConfig({
  testDir: "./tests/capturas",
  timeout: 480_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  outputDir: "capturas-test-results",
  use: {
    baseURL: `http://localhost:${PORT}`,
    // Tema claro forzado para las capturas (RGPD-safe demo).
    colorScheme: "light",
    screenshot: "off",
    trace: "off",
    video: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Sin webServer: reutiliza el dev server ya en marcha (:3000). NO spawnea.
});
