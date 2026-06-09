import type { Page } from "@playwright/test";

export const SEED_USER = {
  id: "marcos-fulkro-id",
  email: "marcos@fulkro.es",
  display_name: "Marcos Mata Garcia",
  must_change_password: false,
  webauthn_credentials: 0,
  totp_enabled: true,
};

/**
 * Intercepts ``/api/v1/auth/me`` so AuthGuard succeeds without hitting the
 * backend, and seeds session cookies. Call at the start of any test that
 * renders a protected route.
 */
export async function mockAuthenticated(page: Page) {
  await page.context().addCookies([
    {
      name: "fulkro_session",
      value: "e2e-session-token",
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Strict",
    },
    {
      name: "fulkro_csrf",
      value: "e2e-csrf-token",
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Strict",
    },
  ]);
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SEED_USER),
    });
  });
  // Clients endpoint feeds the Sidebar; respond empty to keep tests hermetic.
  await page.route("**/api/v1/clients", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    });
  });
}
