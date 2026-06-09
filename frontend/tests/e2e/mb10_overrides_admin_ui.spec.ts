/**
 * MB-10 Atom 10.3.D · E2E spec admin feature flag overrides.
 *
 * Stack real loginAsMarcos · backend endpoints reales /api/v1/admin/feature-flags/*
 * (ADR-046 materializa ADR-036 deferred · MB-10 Atom 10.2/10.3).
 *
 * Cubre (API-level · pattern admin-cosecha-mb19c · admin-magic-link-policy-mb19b):
 * - Endpoints registrados accesibles auth Marcos
 * - GET /overrides 400 si NO project_id ni client_id (Pydantic validation)
 * - GET /overrides 200 con project_id válido (UUID random · lista vacía OK)
 * - POST /override 422 si scope_required violated (Pydantic validator)
 * - DELETE /override/{id} 404 si override no existe
 *
 * UI-level (browser navigate · grant flow · revoke flow): DEFER MB-15 hardening
 * (Block 5 cement · spec hardening dedicated scope). Pattern data-testid ya
 * applied en componente (OPS-058 sostained) · UI scenarios scaffolded forward.
 *
 * Refs: ADR-046 (renamed post-audit B1.2 · was ADR-037 MB-10) · MB-10 Atom 10.3 · Q5.3 cement INVISIBLE cliente sostained.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

function randomUuid(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function getCsrfHeader(
  context: any,
): Promise<{ "x-csrf-token": string }> {
  const cookies = await context.cookies();
  const csrf = cookies.find((c: any) => c.name === "fulkro_csrf")?.value;
  if (!csrf) {
    throw new Error("fulkro_csrf cookie missing — loginAsMarcos no ejecutado?");
  }
  return { "x-csrf-token": csrf };
}

test.describe("MB-10 Atom 10.3 · feature flag overrides admin endpoints", () => {
  test("list overrides: 400 si NO project_id ni client_id", async ({
    context,
  }) => {
    await loginAsMarcos(context);

    const res = await context.request.get(
      `${BACKEND_BASE}/api/v1/admin/feature-flags/overrides`,
    );
    expect(res.status()).toBe(400);

    const body = await res.json();
    expect(String(body.detail).toLowerCase()).toContain("project_id");
  });

  test("list overrides: 200 con project_id válido (lista vacía OK)", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const fakeProjectId = randomUuid();

    const res = await context.request.get(
      `${BACKEND_BASE}/api/v1/admin/feature-flags/overrides?project_id=${fakeProjectId}`,
    );
    expect(res.status()).toBe(200);

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
    expect(body).toEqual([]); // project no existe = sin overrides
  });

  test("grant override: 422 si scope_required violated (sin project_id ni client_id)", async ({
    context,
  }) => {
    await loginAsMarcos(context);
    const csrfHeader = await getCsrfHeader(context);

    const res = await context.request.post(
      `${BACKEND_BASE}/api/v1/admin/feature-flags/override`,
      {
        headers: csrfHeader,
        data: {
          feature_key: "alta_pentest_cpstic",
          override_value: true,
          // project_id NI client_id → Pydantic model_validator raise
        },
      },
    );
    expect(res.status()).toBe(422);

    const body = await res.json();
    // Pydantic devuelve detail array con error message del validator
    const detail = JSON.stringify(body.detail).toLowerCase();
    expect(detail).toContain("project_id");
  });

  test("revoke override: 404 si override no existe", async ({ context }) => {
    await loginAsMarcos(context);
    const csrfHeader = await getCsrfHeader(context);
    const fakeOverrideId = randomUuid();

    const res = await context.request.delete(
      `${BACKEND_BASE}/api/v1/admin/feature-flags/override/${fakeOverrideId}`,
      {
        headers: csrfHeader,
        data: {},
      },
    );
    expect(res.status()).toBe(404);

    const body = await res.json();
    expect(String(body.detail).toLowerCase()).toContain("not found");
  });

  test("admin override endpoints requieren auth (NO anonymous access)", async ({
    request,
  }) => {
    // request directo SIN loginAsMarcos · debería rechazar
    const res = await request.get(
      `${BACKEND_BASE}/api/v1/admin/feature-flags/overrides?project_id=${randomUuid()}`,
    );
    expect([401, 403, 422]).toContain(res.status());
  });
});
