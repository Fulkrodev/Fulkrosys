/**
 * Helpers auth E2E Playwright — sesiones reales backend, NO firma frontend.
 *
 * loginAsMarcos: POST /api/v1/_dev/login-as-marcos. Backend crea row
 * auth_sessions + emite cookies httpOnly (fulkro_session) + csrf
 * (fulkro_csrf no httpOnly) reusando `auth_service.create_session` y
 * `_set_auth_cookies` del flow admin real. Sesión indistinguible de
 * un login Marcos normal — pasa el revocation lookup que `/auth/me`
 * hace contra BD.
 *
 * loginAsClient: form fill real /client-portal/login con credenciales
 * del cliente E2E sintético creado en globalSetup.
 *
 * Decisión post-hallazgo (vs plan v4.2 inicial Playwright firma JWT):
 * backend hace double check (signature + BD revocation lookup) por
 * defensa ENS. JWT pre-firmado externamente sin row en auth_sessions
 * = 401 en /auth/me. El endpoint dev real es la solución honesta y
 * además simplifica el helper (sin jose, sin PRIVATE_KEY en runtime
 * tests).
 *
 * Distinto del pattern mock de `helpers.ts` (mockAuthenticated): aquí
 * usamos el flow real backend. Tests pipeline/meeting/etc siguen con
 * mocks por su foco UI flow.
 *
 * Ver ADR-013 (separación 3 portales), ADR-019 (CSRF), ADR-020.
 */

import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import { request } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

/**
 * Clave de persist del active-project-store (Zustand + persist · ADR-054).
 * Source of truth: `STORAGE_KEY` en `frontend/lib/stores/active-project-store.ts`.
 * El blob serializado es `{ state, version }` (createJSONStorage default).
 */
const ACTIVE_PROJECT_STORAGE_KEY = "fulkro-active-project";

/** Shape mínimo de ActiveProject (mirror del store · NO importar para evitar
 *  arrastrar "use client" + zustand al runtime de Playwright). */
interface SeedActiveProject {
  id: string;
  name: string;
  clientId: string;
  clientName: string;
  ensCategory: "BASICA" | "MEDIA" | "ALTA" | null;
  status: string;
  lastAccessedAt: number;
}

/**
 * Cache module-level del proyecto de test Marcos. `create-test-client` es
 * idempotente pero hace I/O BD: lo resolvemos una vez por proceso worker
 * Playwright y reusamos en cada `loginAsMarcos`.
 */
let _cachedSeedProject: SeedActiveProject | null = null;

interface CreateTestClientResponse {
  client_id: string;
  project_id: string;
}

interface ProjectHeaderResponse {
  project: {
    id: string;
    nombre: string;
    categoria_objetivo: string | null;
    lifecycle_state: string | null;
    fase: string | null;
  };
  cliente: { id: string; nombre: string };
}

function parseSeedCategory(
  raw: string | null,
): "BASICA" | "MEDIA" | "ALTA" | null {
  return raw === "BASICA" || raw === "MEDIA" || raw === "ALTA" ? raw : null;
}

/**
 * Resuelve (idempotente, cacheado) el proyecto del cliente de test E2E para
 * sembrar el active-project-store. Usa el MISMO endpoint dev que `globalSetup`
 * (`create-test-client`) + el header endpoint real (mismo que `ActiveProjectSync`)
 * para obtener metadata fiel (nombre, cliente, categoría MEDIA).
 *
 * Devuelve null si no se puede resolver (backend caído / endpoint 404 prod):
 * en ese caso `loginAsMarcos` simplemente NO siembra (degradación limpia · no
 * rompe el login con cookies, que es el contrato mínimo del helper).
 */
async function resolveSeedProject(
  ctx: APIRequestContext,
): Promise<SeedActiveProject | null> {
  if (_cachedSeedProject) return _cachedSeedProject;
  try {
    const res = await ctx.post(
      `${BACKEND_BASE}/api/v1/_dev/create-test-client`,
    );
    if (!res.ok()) return null;
    const data = (await res.json()) as CreateTestClientResponse;

    // Metadata fiel vía header endpoint (cookies Marcos ya en ctx).
    let name = "Proyecto ENS Test E2E";
    let clientName = "Test E2E Client";
    let ensCategory: "BASICA" | "MEDIA" | "ALTA" | null = "MEDIA";
    let status = "ACTIVE";
    try {
      const header = await ctx.get(
        `${BACKEND_BASE}/api/v1/projects/${data.project_id}/header`,
      );
      if (header.ok()) {
        const h = (await header.json()) as ProjectHeaderResponse;
        name = h.project.nombre ?? name;
        clientName = h.cliente.nombre ?? clientName;
        ensCategory = parseSeedCategory(h.project.categoria_objetivo);
        status =
          h.project.lifecycle_state ?? h.project.fase ?? status;
      }
    } catch {
      // header opcional · fallback a constantes conocidas del seed dev
    }

    _cachedSeedProject = {
      id: data.project_id,
      name,
      clientId: data.client_id,
      clientName,
      ensCategory,
      status,
      lastAccessedAt: Date.now(),
    };
    return _cachedSeedProject;
  } catch {
    return null;
  }
}

export async function loginAsMarcos(context: BrowserContext): Promise<void> {
  const ctx = await request.newContext();
  try {
    const res = await ctx.post(`${BACKEND_BASE}/api/v1/_dev/login-as-marcos`);
    if (!res.ok()) {
      throw new Error(
        `_dev/login-as-marcos devolvió ${res.status()}. ` +
          `¿Backend running en ${BACKEND_BASE}? ¿app_env != "production"?`,
      );
    }
    // ctx.storageState() incluye las cookies que el response Set-Cookie
    // agregó al APIRequestContext. Las propagamos al BrowserContext
    // del test para que las páginas las envíen como cookie automática.
    const state = await ctx.storageState();
    const authCookies = state.cookies.filter(
      (c) => c.name === "fulkro_session" || c.name === "fulkro_csrf",
    );
    if (authCookies.length === 0) {
      throw new Error(
        "_dev/login-as-marcos no devolvió cookies fulkro_session+fulkro_csrf.",
      );
    }
    await context.addCookies(authCookies);

    // ── Dismiss del tour onboarding admin ───────────────────────────────
    // `OnboardingTourAdmin` abre un overlay role="dialog"
    // (data-testid="admin-tour-overlay") en el PRIMER montaje admin si la
    // flag localStorage `fulkro_admin_tour_completed` está ausente. Ese
    // overlay (z-[60], fixed inset-0) INTERCEPTA todos los pointer events →
    // los `locator.click` de las specs admin hacen timeout 30s. Es el espejo
    // exacto del `fulkro_tutorial_completed` que `loginAsClient` ya setea
    // para el portal cliente. Lo sembramos vía addInitScript (corre en CADA
    // documento ANTES del bundle de la app → el useEffect del tour ve la flag
    // y NO abre). Specs que testean el tour explícitamente pueden limpiar la
    // flag en su propio beforeEach. Source of truth del key:
    // components/admin/copilot/OnboardingTourAdmin.tsx (STORAGE_KEY).
    await context.addInitScript(() => {
      try {
        window.localStorage.setItem("fulkro_admin_tour_completed", "1");
      } catch {
        // incognito / storage disabled · ignore
      }
    });

    // ── Dismiss del CopilotGuidedFlow en las 8 páginas ENS core ─────────
    // `CopilotGuidedFlow` (Sesión 3B-2B.4) se monta ENCIMA del panel de cada
    // página ENS (dda · magerit · risks · plan · evidence · conformity ·
    // dossier · dimensiones) y renderiza su PROPIO heading
    // (data-testid="copilot-guided-<phaseId>"). Ese heading colisiona con el
    // heading de contenido del panel (mismo texto, ej. "Declaración de
    // Aplicabilidad") → las specs admin que usan getByRole("heading", …) sin
    // scope disparan strict-mode violation. Un admin real que ya ha usado la
    // app tiene estos guías cerrados (flag localStorage
    // `fulkro_copilot_guided_dismissed_<phaseId>` · STORAGE_KEY_PREFIX en
    // CopilotGuidedFlow.tsx). Sembramos los flags vía addInitScript (corre en
    // CADA documento ANTES del bundle → el componente arranca dismissed y NO
    // renderiza el heading colisionante). Specs que testean el guided flow
    // explícitamente pueden limpiar su flag en su propio beforeEach.
    await context.addInitScript(() => {
      const phaseIds = [
        "categorizacion-dimensiones",
        "magerit-analysis",
        "dda-applicability",
        "risks-register",
        "plan-adecuacion",
        "evidence-vault",
        "conformity-declaration",
        "dossier-enac",
        "roadmap-overview",
      ];
      try {
        for (const id of phaseIds) {
          window.localStorage.setItem(
            `fulkro_copilot_guided_dismissed_${id}`,
            "1",
          );
        }
      } catch {
        // incognito / storage disabled · ignore
      }
    });

    // ── Siembra del active-project-store (ADR-054) ──────────────────────
    // Las ~101 specs admin project-scoped asumen un proyecto activo. Sin
    // sembrar, el shell admin muestra el gate "Selecciona un proyecto" /
    // "Sin proyecto activo" porque `activeProject` arranca null (sólo se
    // hidrata desde la URL param vía ActiveProjectSync). Sembramos el blob
    // de persist (mismo shape `{ state, version }` que createJSONStorage)
    // con un proyecto VÁLIDO del cliente de test → el store hidrata
    // `activeProject` + `lastUsedProjectId` al montar (default shallow merge
    // de zustand persist mergea ambas claves del blob).
    //
    // `context.addInitScript` se ejecuta en CADA documento nuevo, ANTES de
    // cualquier script de la página → el store ya está sembrado cuando la
    // app monta. Specs que requieran un estado distinto (empty / un
    // lastUsedProjectId concreto) registran su PROPIO `page.addInitScript`
    // que corre DESPUÉS (los scripts de contexto preceden a los de página)
    // y sobreescribe la clave → su intención gana (ej.
    // active_project_banner.spec empty-state · projects_selector_landing
    // "último usado"). NO afecta al portal cliente (loginAsClient va aparte
    // y el cliente no usa este store · R29).
    const seed = await resolveSeedProject(ctx);
    if (seed) {
      await context.addInitScript(
        ({ key, project }) => {
          try {
            // No pisar si la página ya tiene valor (defensa extra · el orden
            // context→page hace que los specs que siembran su propio estado
            // ganen igualmente).
            if (window.localStorage.getItem(key)) return;
            window.localStorage.setItem(
              key,
              JSON.stringify({
                state: {
                  activeProject: project,
                  lastUsedProjectId: project.id,
                },
                version: 0,
              }),
            );
          } catch {
            // incognito / storage disabled · ignore
          }
        },
        { key: ACTIVE_PROJECT_STORAGE_KEY, project: seed },
      );
    }
  } finally {
    await ctx.dispose();
  }
}

export interface LoginAsClientOptions {
  email?: string;
  password?: string;
  /**
   * Si true (default) marca el tutorial onboarding como completado vía
   * `localStorage.fulkro_tutorial_completed` post-login para evitar que el
   * overlay bloquee selectores `data-testid` del dashboard en specs que NO
   * testean el tutorial. Specs que verifican comportamiento del tutorial
   * (ej. `mb7_3_tutorial.spec.ts`) deben pasar `dismissTutorial: false` o
   * limpiar la flag mediante `context.addInitScript` en su `beforeEach`.
   */
  dismissTutorial?: boolean;
}

export async function loginAsClient(
  page: Page,
  options: LoginAsClientOptions = {},
): Promise<void> {
  const email = options.email ?? "test-client-e2e@example.com";
  const password = options.password ?? "TestP@ssw0rd123!";

  await page.goto("/client-portal/login");
  // Anclar al input por id (#email/#password): el getByLabel(/Email/i) chocaba
  // en strict-mode con el mailto del FulkroFooter (aria-label "Enviar email a…",
  // Ejecutable 7.6). Selector estable, sin colisión con copy de marca.
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Entrar/i }).click();
  await page.waitForURL(/\/client-portal\/(dashboard|account)/, {
    timeout: 10_000,
  });

  if (options.dismissTutorial !== false) {
    await page.evaluate(() => {
      try {
        window.localStorage.setItem("fulkro_tutorial_completed", "1");
      } catch {
        // incognito / storage disabled · ignore
      }
    });
  }
}
