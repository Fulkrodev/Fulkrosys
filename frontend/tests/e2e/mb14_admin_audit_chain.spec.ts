/**
 * MB-14 admin · audit chain endpoints (ADR-038 SAN-D MB-14.1).
 *
 * Verifica admin specs stack real (loginAsMarcos existing):
 * - /admin/inbox page placeholder renderiza
 * - audit chain integrity endpoint mockable
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

test.describe("MB-14 admin · audit chain + inbox stack real", () => {
  test("admin inbox page renderiza con hint per-projecto", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/inbox");

    await expect(
      page.getByRole("heading", { name: /Inbox · Chat con clientes/i }),
    ).toBeVisible();
    await expect(
      page.getByText(/vista agregada cross-project se incorporará/i),
    ).toBeVisible();
  });

  test("audit chain integrity endpoint accesible vía mock", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);

    const projectId = "aaaa1111-2222-3333-4444-555555555555";

    let integritySeen = false;
    await page.route(
      `**/api/v1/projects/${projectId}/client-audit/integrity`,
      (route) => {
        integritySeen = true;
        route.fulfill({
          status: 200,
          json: {
            project_id: projectId,
            chain_valid: true,
            broken_at_index: null,
          },
        });
      },
    );

    // Navigate first to set base URL · then fetch from window context.
    await page.goto("/admin/inbox");

    const result = await page.evaluate(async (pid) => {
      const res = await fetch(
        `/api/v1/projects/${pid}/client-audit/integrity`,
        { credentials: "include" },
      );
      return res.json();
    }, projectId);

    expect(integritySeen).toBe(true);
    expect(result.chain_valid).toBe(true);
  });
});
