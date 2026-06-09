/**
 * E2E · fase_36 cliente cloud-connections steady-state (Sesión 3B-2B.8 Phase 1C).
 *
 * Verifica:
 *  - Sidebar nav entry "Conexiones cloud" navigates /cloud-connections
 *  - Hero steady-state visible (NO botón "Saltar")
 *  - "Mis conexiones activas" lista connectors connected con badges
 *  - Remediations badge link → /remediaciones cuando hay pendientes
 *  - Disconnect modal opens · justification required · submit calls
 *    POST /request-disconnect chat-mediated
 *  - "Añadir nuevas conexiones" renderiza CloudConnectFirstStep (DRY OPS-026)
 *  - ADR-014 sostained · NUNCA call DELETE endpoint cliente
 *  - WCAG axe-core 0 violations cross sections
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import {
  CONNECTORS_WITH_M365_CONNECTED,
  mockCloudConnectClientBase,
} from "../../fase_32/_fixtures";

const PROJECT_ID = "f32f32f3-2f32-4f32-bf32-f32f32f32f32";
const CONNECTOR_M365_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

async function mockRemediationsEmpty(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/client-portal/cloud-gaps**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        project_id: PROJECT_ID,
        count: 0,
        gaps: [],
      }),
    });
  });
}

async function mockRemediationsTwoPending(
  page: import("@playwright/test").Page,
) {
  await page.route("**/api/v1/client-portal/cloud-gaps**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        project_id: PROJECT_ID,
        count: 2,
        gaps: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            project_id: PROJECT_ID,
            ens_measure_code: "op.acc.6",
            severity: "high",
            title: "MFA missing",
            explanation_es: null,
            suggested_action: null,
            approval_status: "proposed_to_cliente",
            proposed_to_cliente_at: "2026-05-25T10:00:00Z",
            cliente_approval_at: null,
            resolved_at: null,
            evidence_link_id: null,
          },
          {
            id: "22222222-2222-2222-2222-222222222222",
            project_id: PROJECT_ID,
            ens_measure_code: "op.acc.5",
            severity: "medium",
            title: "Privilege excess",
            explanation_es: null,
            suggested_action: null,
            approval_status: "proposed_to_cliente",
            proposed_to_cliente_at: "2026-05-25T11:00:00Z",
            cliente_approval_at: null,
            resolved_at: null,
            evidence_link_id: null,
          },
        ],
      }),
    });
  });
}

test.describe("fase_36 · cliente /cloud-connections steady-state", () => {
  test("sidebar nav entry navigates + hero steady-state renders", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsEmpty(page);

    await page.goto("/client-portal/");

    // Sidebar entry visible
    const navLink = page.getByTestId("cliente-nav-conexiones-cloud");
    await expect(navLink).toBeVisible();
    await navLink.click();

    await expect(page).toHaveURL(/\/client-portal\/cloud-connections/);
    await expect(page.getByTestId("cloud-connections-page")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Conexiones cloud/i, level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByText(/Gestiona tus conexiones/i),
    ).toBeVisible();
  });

  test("lista connections activas + badges + sin remediations no link", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsEmpty(page);

    await page.goto("/client-portal/cloud-connections");

    // Badge "Conectado" (statusLabel("connected")) y metadata viven DENTRO de
    // la card del conector · scope al card evita cualquier ambigüedad/race con
    // el skeleton de carga.
    const card = page.getByTestId("cloud-connection-card-microsoft_365");
    await expect(card).toBeVisible();
    await expect(card.getByText(/Microsoft 365/i).first()).toBeVisible();
    // UI drift: /Conectado/i (case-insensitive) matchea el badge "Conectado" y
    // el texto friendly "... conectado · 42 elementos" → strict-mode 2 elementos.
    await expect(card.getByText(/Conectado/i).first()).toBeVisible();
    await expect(card.getByText(/42 elementos detectados/i)).toBeVisible();

    // Remediations link NOT visible cuando 0 pendientes
    await expect(
      page.getByTestId("cloud-connections-remediations-link"),
    ).toHaveCount(0);
  });

  test("remediations badge link cuando hay pendientes", async ({ page }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsTwoPending(page);

    await page.goto("/client-portal/cloud-connections");

    const link = page.getByTestId("cloud-connections-remediations-link");
    await expect(link).toBeVisible();
    await expect(link).toContainText("2 mejoras propuestas pendientes");
    await expect(link).toHaveAttribute(
      "href",
      "/client-portal/remediaciones",
    );
  });

  test("solicitar disconnect modal · ADR-014 chat-mediated", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsEmpty(page);

    // ADR-014 sostained · NUNCA permitir DELETE endpoint cliente
    let unexpectedDeleteCall = false;
    page.on("request", (req) => {
      if (
        req.method() === "DELETE" &&
        req.url().includes("/cloud-connectors/")
      ) {
        unexpectedDeleteCall = true;
      }
    });

    // Mock request-disconnect endpoint
    await page.route(
      `**/api/v1/client-portal/cloud-connectors/${CONNECTOR_M365_ID}/request-disconnect`,
      async (route) => {
        const body = await route.request().postDataJSON();
        expect(body.justification).toBe("Cambiamos a otro IdP");
        await route.fulfill({
          status: 202,
          contentType: "application/json",
          body: JSON.stringify({
            thread_id: "ttttttt-tttt-tttt-tttt-tttttttttttt",
            provider: "microsoft_365",
            connector_id: CONNECTOR_M365_ID,
            friendly_message:
              "Solicitud registrada · Marcos te contactará por chat.",
          }),
        });
      },
    );

    await page.goto("/client-portal/cloud-connections");

    await page
      .getByTestId("cloud-connection-request-disconnect-microsoft_365")
      .click();

    const modal = page.getByTestId("cloud-connect-disconnect-modal");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText(/Microsoft 365/i);
    await expect(modal).toContainText(/Marcos revisará/i);

    await page
      .getByTestId("cloud-disconnect-justification")
      .fill("Cambiamos a otro IdP");

    const reqWait = page.waitForRequest((req) =>
      req
        .url()
        .includes(
          `/cloud-connectors/${CONNECTOR_M365_ID}/request-disconnect`,
        ),
    );
    await page.getByTestId("cloud-disconnect-submit").click();
    await reqWait;

    // ADR-014 sostained empirical
    expect(unexpectedDeleteCall).toBe(false);
  });

  test("añadir nuevas conexiones · render CloudConnectFirstStep (DRY reuse)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsEmpty(page);

    await page.goto("/client-portal/cloud-connections");

    // CloudConnectFirstStep renderizado (component reuse)
    await expect(page.getByTestId("cloud-connect-first-step")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-grid")).toBeVisible();
    // Heading add-section visible
    await expect(
      page.getByRole("heading", { name: /Añadir nuevas conexiones/i }),
    ).toBeVisible();
  });

  test("WCAG axe-CI · 0 violations cross-page", async ({ page }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });
    await mockRemediationsTwoPending(page);

    await page.goto("/client-portal/cloud-connections");
    await page.waitForSelector('[data-testid="cloud-connections-page"]');

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(
      results.violations,
      `axe violations encontradas:\n${JSON.stringify(
        results.violations.map((v) => ({ id: v.id, impact: v.impact })),
        null,
        2,
      )}`,
    ).toHaveLength(0);
  });
});
