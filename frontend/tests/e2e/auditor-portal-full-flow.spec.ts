/**
 * Auditor portal full E2E flow · CLUSTER 3 Phase C5.1.
 *
 * Comprehensive 9-step empirical flow cross CLUSTER 2 + 3:
 *   1. Auditor entry via magic link AUDITOR_PORTAL_ENAC (+ OTP step-up)
 *   2. Navigate 9 read-only views (Phase 5)
 *   3. Create 3 annotations · 3 severities (Phase C1)
 *   4. Request 2 clarifications · 2 priorities (Phase C2)
 *   5. Admin respond clarifications via /admin (Phase C2)
 *   6. Auditor review DdA-evidence gaps heatmap (Phase C3)
 *   7. Auditor generate draft audit report PDF (Phase C4)
 *   8. Admin review draft history (Phase C4)
 *   9. Verify audit_log emit per critical action (R6 hash chain)
 *
 * AUTOSUFICIENTE: antes se saltaba entero sin AUDITOR_PORTAL_TOKEN +
 * FULKRO_TEST_PROJECT_ID, y en local no corría nunca. Ahora acuña en runtime
 * un magic-link del auditor (token + OTP) sobre el proyecto fijo rico que
 * siembra globalSetup (tiene DdA ALTA real, que los pasos 3 y 6 necesitan).
 * Las variables de entorno siguen valiendo como override.
 *
 * Los pasos son una sola historia (el 5 responde lo que pregunta el 4, el 9
 * comprueba lo que hicieron los anteriores) → modo serial. Cada texto lleva
 * una marca de ejecución para no confundir lo nuestro con lo que dejaron
 * ejecuciones anteriores sobre el mismo proyecto.
 */
import { expect, test } from "@playwright/test";

import {
  type AuditorAccess,
  openAuditorSection,
  resolveAuditorAccess,
} from "./_helpers/auditor-portal";
import { loginAsMarcos } from "./_helpers/auth-real";

test.describe.configure({ mode: "serial" });

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

// Marca única por ejecución: los textos que creamos la llevan.
const RUN_TAG = `e2e-${Date.now().toString(36)}`;
// Margen de reloj para comparar con el `timestamp` del audit_log (now() de la
// transacción en Postgres · mismo host, pero sin asumir precisión perfecta).
const CLOCK_SKEW_MS = 5_000;

let access: AuditorAccess;
let runStartedAt: number;

const ANNOTATIONS = [
  { severity: "info", label: "Informativo" },
  { severity: "warning", label: "Atención" },
  { severity: "critical", label: "Crítico" },
] as const;

const CLARIFICATIONS = [
  { priority: "urgent", label: "Urgente" },
  { priority: "normal", label: "Normal" },
] as const;

const clarificationText = (priority: string) =>
  `Aclaración ${RUN_TAG} priority=${priority}`;

test.describe("Auditor portal · full E2E flow CLUSTER 2 + 3", () => {
  test.beforeAll(async ({ request }) => {
    runStartedAt = Date.now();
    access = await resolveAuditorAccess(request);
  });

  test("step 1: auditor portal entry + branding propagated", async ({
    page,
    request,
  }) => {
    await openAuditorSection(page, access, "summary");
    await expect(page.getByTestId("auditor-summary-view")).toBeVisible({
      timeout: 10_000,
    });
    // La categoría que pinta el resumen es la del proyecto del token.
    const meta = await request.get(
      `${BACKEND_BASE}/api/v1/public/auditor-portal/${access.token}`,
    );
    expect(meta.ok()).toBeTruthy();
    const { project } = (await meta.json()) as {
      project: { id: string; categoria: string };
    };
    expect(project.id).toBe(access.projectId);
    await expect(page.getByTestId("auditor-summary-categoria")).toBeVisible();
    await expect(page.getByTestId("auditor-summary-categoria")).toContainText(
      new RegExp(project.categoria, "i"),
    );
  });

  test("step 2: navigate 9 read-only views", async ({ page }) => {
    const sections = [
      "summary",
      "dda",
      "magerit",
      "plan",
      "evidence",
      "e041",
      "audit-log",
      "pentest",
      "documents",
    ];
    for (const section of sections) {
      await openAuditorSection(page, access, section);
      // Cada vista termina en `auditor-<section>-view` o, si el proyecto no
      // tiene ese artefacto (plan, E-041, pentest en el proyecto fijo), en su
      // estado vacío explícito `auditor-<section>-empty`. No basta con el
      // chrome: el chrome sale aunque la vista acabe en error.
      await expect(
        page
          .getByTestId(`auditor-${section}-view`)
          .or(page.getByTestId(`auditor-${section}-empty`)),
        `vista ${section}`,
      ).toBeVisible({ timeout: 10_000 });
      await expect(
        page.getByTestId(`auditor-${section}-error`),
        `vista ${section} sin error`,
      ).toHaveCount(0);
    }
  });

  test("step 3: create 3 annotations (one per severity)", async ({
    page,
    request,
  }) => {
    await openAuditorSection(page, access, "dda");
    await expect(page.getByTestId("auditor-dda-view")).toBeVisible({
      timeout: 10_000,
    });
    const annotateBtn = page
      .locator('[data-testid^="auditor-annotate-medida-"]')
      .first();
    await expect(annotateBtn).toBeVisible();
    const medidaId = (await annotateBtn.getAttribute("data-testid"))!.replace(
      "auditor-annotate-medida-",
      "",
    );

    for (const { severity, label } of ANNOTATIONS) {
      await annotateBtn.click();
      await page.getByTestId("auditor-annotation-severity").click();
      await page.getByRole("option", { name: label, exact: true }).click();
      await page
        .getByTestId("auditor-annotation-textarea")
        .fill(`Anotación ${RUN_TAG} severity=${severity}`);
      const created = page.waitForResponse(
        (r) =>
          r.url().includes(`/auditor-portal/${access.token}/annotations`) &&
          r.request().method() === "POST",
      );
      await page.getByTestId("auditor-annotation-submit").click();
      expect((await created).status(), `POST anotación ${severity}`).toBe(201);
      // El diálogo se cierra al guardar (onSuccess) · antes de la siguiente.
      await expect(page.getByTestId("auditor-annotation-textarea")).toBeHidden();
    }

    // Las 3 anotaciones existen en backend, sobre esa medida y con su severidad.
    const list = await request.get(
      `${BACKEND_BASE}/api/v1/public/auditor-portal/${access.token}/annotations`,
    );
    expect(list.ok()).toBeTruthy();
    const { items } = (await list.json()) as {
      items: Array<{
        target_type: string;
        target_id: string;
        flag_severity: string;
        annotation_text: string;
      }>;
    };
    const ours = items.filter((a) => a.annotation_text.includes(RUN_TAG));
    expect(ours.map((a) => a.flag_severity).sort()).toEqual(
      ["critical", "info", "warning"],
    );
    for (const a of ours) {
      expect(a.target_type).toBe("medida");
      expect(a.target_id).toBe(medidaId);
    }
  });

  test("step 4: request 2 clarifications (urgent + normal)", async ({
    page,
    request,
  }) => {
    await openAuditorSection(page, access, "summary");
    // Botón general del topbar (disponible en todas las vistas).
    const clarBtn = page.getByTestId("auditor-clarification-button-general");
    for (const { priority, label } of CLARIFICATIONS) {
      await clarBtn.click();
      await page.getByTestId("auditor-clarification-priority").click();
      await page.getByRole("option", { name: label, exact: true }).click();
      await page
        .getByTestId("auditor-clarification-textarea")
        .fill(clarificationText(priority));
      const created = page.waitForResponse(
        (r) =>
          r.url().includes(`/auditor-portal/${access.token}/clarifications`) &&
          r.request().method() === "POST",
      );
      await page.getByTestId("auditor-clarification-submit").click();
      expect((await created).status(), `POST aclaración ${priority}`).toBe(201);
      await expect(
        page.getByTestId("auditor-clarification-textarea"),
      ).toBeHidden();
    }

    const list = await request.get(
      `${BACKEND_BASE}/api/v1/public/auditor-portal/${access.token}/clarifications`,
    );
    expect(list.ok()).toBeTruthy();
    const { items } = (await list.json()) as {
      items: Array<{ question_text: string; priority: string; status: string }>;
    };
    for (const { priority } of CLARIFICATIONS) {
      const mine = items.find((c) => c.question_text === clarificationText(priority));
      expect(mine, `aclaración ${priority} persistida`).toBeTruthy();
      expect(mine!.priority).toBe(priority);
      expect(mine!.status).toBe("open");
    }
  });

  test("step 5: admin responds clarifications", async ({
    browser,
    request,
  }) => {
    const context = await browser.newContext();
    // loginAsMarcos para admin endpoints require_owner
    await loginAsMarcos(context);
    const adminPage = await context.newPage();
    await adminPage.goto(
      `/admin/projects/${access.projectId}/audit/clarifications`,
    );
    await expect(
      adminPage.getByTestId("admin-clarifications-inbox"),
    ).toBeVisible({ timeout: 15_000 });

    // La tarjeta de NUESTRA aclaración urgente (no "la primera": el proyecto
    // acumula las de ejecuciones anteriores).
    const question = clarificationText("urgent");
    const card = adminPage
      .locator('[data-testid^="admin-clarification-card-"]')
      .filter({ hasText: question });
    await expect(card).toHaveCount(1, { timeout: 10_000 });
    const id = (await card.getAttribute("data-testid"))!.replace(
      "admin-clarification-card-",
      "",
    );
    const answer = `Respuesta admin ${RUN_TAG}`;
    await adminPage.getByTestId(`admin-clarification-response-${id}`).fill(answer);
    const patched = adminPage.waitForResponse(
      (r) =>
        r.url().includes(`/audit/clarifications/${id}`) &&
        r.request().method() === "PATCH",
    );
    await adminPage.getByTestId(`admin-clarification-submit-${id}`).click();
    expect((await patched).status(), "PATCH respuesta admin").toBe(200);
    await expect(card).toContainText("Última respuesta");
    await context.close();

    // El auditor ve la respuesta y la aclaración avanza a "respondida".
    const list = await request.get(
      `${BACKEND_BASE}/api/v1/public/auditor-portal/${access.token}/clarifications`,
    );
    const { items } = (await list.json()) as {
      items: Array<{
        id: string;
        admin_response: string | null;
        status: string;
      }>;
    };
    const mine = items.find((c) => c.id === id);
    expect(mine?.admin_response).toBe(answer);
    expect(mine?.status).toBe("responded");
  });

  test("step 6: review DdA-evidence gaps heatmap + drawer", async ({
    page,
  }) => {
    await openAuditorSection(page, access, "audit/dda-evidence-gaps");
    await expect(page.getByTestId("gap-view")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("gap-coverage-pct")).toContainText("%");
    // Click first medida cell to open drawer
    const firstCell = page.locator('[data-testid^="gap-medida-cell-"]').first();
    await expect(firstCell).toBeVisible();
    const code = (await firstCell.getAttribute("data-testid"))!.replace(
      "gap-medida-cell-",
      "",
    );
    await firstCell.click();
    const drawer = page.getByTestId("gap-medida-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText(code);
    await page.getByTestId("gap-drawer-close").click();
    await expect(drawer).toBeHidden();
  });

  test("step 7: auditor generates draft audit report PDF", async ({
    page,
  }) => {
    await openAuditorSection(page, access, "draft-report");
    await expect(page.getByTestId("draft-report-view")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("draft-preview-iframe")).toBeVisible({
      timeout: 15_000,
    });
    await page
      .getByTestId("draft-opinion-textarea")
      .fill(`Opinión preliminar ${RUN_TAG}`);
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await page.getByTestId("draft-generate-button").click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/borrador_auditoria.*\.pdf/);
    // Es un PDF de verdad, no un blob vacío.
    const path = await download.path();
    const { readFileSync } = await import("node:fs");
    const bytes = readFileSync(path);
    expect(bytes.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(bytes.length).toBeGreaterThan(1_000);
  });

  test("step 8: admin reviews draft report page", async ({ browser }) => {
    const context = await browser.newContext();
    await loginAsMarcos(context);
    const adminPage = await context.newPage();
    await adminPage.goto(
      `/admin/projects/${access.projectId}/audit/draft-report`,
    );
    await expect(
      adminPage.getByTestId("draft-report-admin-view"),
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      adminPage.getByTestId("draft-admin-preview-iframe"),
    ).toBeVisible({ timeout: 15_000 });
    // El iframe trae el borrador renderizado (no un marco vacío).
    await expect(
      adminPage.frameLocator('[data-testid="draft-admin-preview-iframe"]')
        .locator("body"),
    ).not.toBeEmpty();
    await context.close();
  });

  test("step 9: verify audit_log emit per critical action", async ({
    request,
  }) => {
    // Audit log CSV con el token del auditor (Phase 6 endpoint). Filtramos por
    // acción y exigimos al menos una fila POSTERIOR al inicio de esta ejecución:
    // sin eso pasaría con los eventos de cualquier ejecución anterior.
    const expectedEvents = [
      "auditor.session.start",
      "auditor_portal.view",
      "auditor.annotation.created",
      "auditor.clarification.requested",
      "admin.clarification.responded",
      "auditor.view.dda_evidence_gaps",
      "auditor.draft_report.generated",
    ];
    for (const ev of expectedEvents) {
      const csvResp = await request.get(
        `${BACKEND_BASE}/api/v1/public/auditor-portal/${access.token}/audit-log.csv?accion=${encodeURIComponent(ev)}&limit=50`,
      );
      expect(csvResp.ok()).toBeTruthy();
      const rows = (await csvResp.text())
        .trim()
        .split(/\r?\n/)
        .slice(1) // cabecera
        .map((line) => line.split(","));
      // Columnas: seq,tabla,accion,usuario,timestamp,payload_new
      const recent = rows.filter(
        (cols) =>
          cols[2] === ev &&
          Date.parse(cols[4]) >= runStartedAt - CLOCK_SKEW_MS,
      );
      expect(recent.length, `audit_log ${ev} en esta ejecución`).toBeGreaterThanOrEqual(1);
    }
  });
});
