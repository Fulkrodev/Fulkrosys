/**
 * FASE 10.C.2 · sign-flow purposes parametrizado.
 *
 * 8 purposes: los vigentes (firma_documento · aprobacion_acta ·
 * aprobacion_propuesta) se ejecutan con tokens REALES generados vía
 * POST /api/v1/magic-links/generate y se comprueba el flujo que pinta
 * /sign/{token}; los 5 deprecados v3 se comprueban por su rechazo 422.
 *
 * Setup por test:
 *   1. POST /api/v1/_dev/create-test-client → obtiene project_id real
 *      (idempotente · seeder dev/router.py).
 *   2. POST /api/v1/magic-links/generate (no auth dep · solo RLS por
 *      project_id) con purpose + recipient_email + scope contextual.
 *   3. Extrae token plano de la response (devuelto una sola vez).
 *   4. clearCookies() · navega a /sign/{token} como público.
 *   5. Verifica que el multiplex page.tsx renderiza el componente
 *      correcto (heading + actionLabel disclaimer + botón aprobación).
 *
 * Componentes esperados (multiplex):
 *   - aprobacion_propuesta → ApprovePropuestaFlow  (vigente · ejecutado)
 *
 * Deprecados v3 (ADR-020 · MB-4.bis3 · cliente actúa in-portal · el
 * MagicLinkPolicyEnforcer hard-rechaza su generación → 422, que es lo que se
 * prueba; el componente permanece en el codebase):
 *   - aprobacion_factura → ApproveFacturaFlow
 *   - validacion_cambio_alcance → ValidateScopeChangeFlow
 *   - aceptacion_riesgo_residual → AcceptResidualRiskFlow
 *   - consentimiento_tratamiento_datos → SignDPAFlow
 *   - confirmacion_conformidad → ConfirmConformidadFlow
 *
 * Ver ADR-011 (email customization · purposes #24-#35), FASE 4.5 sub-bloque B.2,
 * ADR-020 v3 (policy_enforcer.py DEPRECATED_V3_CLIENT_FACING).
 */
import { test, expect, type Page } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

interface PurposeConfig {
  purpose: string;
  expectedComponent: string;
  expectedTitle: RegExp;
  expectedActionPhrase: RegExp;
  expectedApproveButton: RegExp;
  /**
   * ADR-020 v3 (MB-4.bis3) · purpose deprecado client-facing: el cliente
   * realiza la acción in-portal (login normal), NO recibe magic-link. El
   * MagicLinkPolicyEnforcer hard-rechaza la generación → POST
   * /magic-links/generate devuelve 422. El componente de flujo permanece en
   * el codebase, pero ya NO es alcanzable por magic-link, así que el caso se
   * prueba el rechazo 422 en lugar del flujo. Ver policy_enforcer.py
   * DEPRECATED_V3_CLIENT_FACING.
   */
  deprecatedV3?: boolean;
  scope?: Record<string, unknown>;
}

const PURPOSES: PurposeConfig[] = [
  {
    // §3.1 audit-2026-06-15 · firma_documento YA NO es mock: el dispatcher lo
    // enruta al flujo REAL DocumentSigningFlow (consume magic-link + Ed25519 m05).
    purpose: "firma_documento",
    expectedComponent: "DocumentSigningFlow",
    expectedTitle: /Firma de documento/i,
    expectedActionPhrase: /firmo conforme/i,
    expectedApproveButton: /Firmar con Ed25519/i,
    scope: {
      document_type: "acta_e012",
      recipient_name: "Responsable de la Información E2E",
      recipient_role: "responsable_informacion",
      acta_snapshot_hash:
        "e2e00000000000000000000000000000000000000000000000000000000e2e00",
    },
  },
  {
    // Flujo REAL ApproveActaFlow (m18 · firma del asistente) · reemplazó al
    // mock LegacyDocumentSignFlow.
    purpose: "aprobacion_acta",
    expectedComponent: "ApproveActaFlow",
    expectedTitle: /Aprobación del acta/i,
    expectedActionPhrase: /He revisado el acta y la apruebo/i,
    expectedApproveButton: /Aprobar acta/i,
    scope: { codigo: "ACTA-E2E-001", asistente_nombre: "Asistente E2E" },
  },
  {
    purpose: "aprobacion_propuesta",
    expectedComponent: "ApprovePropuestaFlow",
    expectedTitle: /Aprobación de propuesta/i,
    expectedActionPhrase: /aprobación de la propuesta/i,
    expectedApproveButton: /Aprobar propuesta/i,
    scope: {
      propuesta_codigo: "P-E2E-001-2026",
      importe_total: "12.500 EUR",
      condiciones: ["Plazo 6 meses", "Pago 30/60/90"],
    },
  },
  {
    purpose: "aprobacion_factura",
    expectedComponent: "ApproveFacturaFlow",
    expectedTitle: /Aprobación de factura/i,
    expectedActionPhrase: /aprobación de la factura/i,
    expectedApproveButton: /Aprobar factura/i,
    deprecatedV3: true, // cliente aprueba in-portal /client-portal/billing (ADR-020 v3)
    scope: {
      factura_codigo: "F-E2E-001-2026",
      importe: "3.500 EUR",
      conceptos: [{ descripcion: "Servicios consultoría ENS", importe: "3.500 EUR" }],
    },
  },
  {
    purpose: "validacion_cambio_alcance",
    expectedComponent: "ValidateScopeChangeFlow",
    expectedTitle: /Validación de cambio de alcance/i,
    expectedActionPhrase: /validación del cambio de alcance/i,
    expectedApproveButton: /Validar cambio/i,
    deprecatedV3: true, // cliente valida in-portal /client-portal/risks (ADR-020 v3)
    scope: {
      cambio_codigo: "CC-E2E-001",
      descripcion_cambio: "Inclusión sistema externo en alcance",
      sistemas_afectados: ["S-WEB-001", "S-API-002"],
      impacto_estimado: "Bajo",
    },
  },
  {
    purpose: "aceptacion_riesgo_residual",
    expectedComponent: "AcceptResidualRiskFlow",
    expectedTitle: /Aceptación de riesgo residual/i,
    expectedActionPhrase: /aceptación del riesgo residual/i,
    expectedApproveButton: /Aceptar riesgo/i,
    deprecatedV3: true, // cliente acepta in-portal /client-portal/risks (ADR-020 v3)
    scope: {
      riesgo_codigo: "R-E2E-001",
      descripcion_riesgo: "Acceso no autorizado a panel admin",
      probabilidad: "BAJA",
      impacto: "MEDIO",
      nivel_residual: "BAJO",
    },
  },
  {
    purpose: "consentimiento_tratamiento_datos",
    expectedComponent: "SignDPAFlow",
    expectedTitle: /Acuerdo de Tratamiento de Datos/i,
    expectedActionPhrase: /Acuerdo de Tratamiento de Datos/i,
    expectedApproveButton: /Firmar DPA/i,
    deprecatedV3: true, // cliente firma DPA in-portal /client-portal/firma (ADR-020 v3)
    scope: {
      dpa_version: "v1.0-2026",
      fecha_efectiva: "2026-05-01",
      categorias_datos: ["Identificativos", "Profesionales"],
      finalidades: ["Gestión proyecto consultoría"],
    },
  },
  {
    purpose: "confirmacion_conformidad",
    expectedComponent: "ConfirmConformidadFlow",
    expectedTitle: /Confirmación de conformidad/i,
    expectedActionPhrase: /confirmación del estado de conformidad/i,
    expectedApproveButton: /Confirmar conformidad/i,
    deprecatedV3: true, // cliente firma conformidad in-portal /client-portal/firma (ADR-020 v3)
    scope: {
      porcentaje_implantacion: 87,
      medidas_implantadas: 65,
      total_medidas: 75,
      evidencias_recopiladas: 142,
    },
  },
];

async function ensureTestProjectId(page: Page): Promise<string> {
  const url = BACKEND_BASE + "/api/v1/_dev/create-test-client";
  const res = await page.request.post(url);
  if (!res.ok()) {
    throw new Error(
      "POST /_dev/create-test-client devolvió " + res.status() + ": " + (await res.text()),
    );
  }
  const data = await res.json();
  return data.project_id as string;
}

async function generateMagicLink(
  page: Page,
  projectId: string,
  purpose: string,
  scope?: Record<string, unknown>,
): Promise<string> {
  // POST /generate requiere auth Marcos (global_dep authenticate_request) + CSRF
  // triple binding (header x-csrf-token + cookie fulkro_csrf + JWT claim).
  // loginAsMarcos ya inyectó las 2 cookies en el context. El header CSRF se
  // extrae de la cookie fulkro_csrf (no httpOnly).
  const cookies = await page.context().cookies();
  const csrf = cookies.find((c) => c.name === "fulkro_csrf")?.value;
  if (!csrf) {
    throw new Error("fulkro_csrf cookie missing — loginAsMarcos no ejecutado?");
  }
  const url = BACKEND_BASE + "/api/v1/magic-links/generate";
  const res = await page.request.post(url, {
    headers: { "x-csrf-token": csrf },
    data: {
      project_id: projectId,
      purpose,
      recipient_email: "test-client-e2e@example.com",
      scope: scope ?? null,
    },
  });
  if (!res.ok()) {
    throw new Error(
      "POST /magic-links/generate " + purpose + " devolvió " + res.status() + ": " + (await res.text()),
    );
  }
  const data = await res.json();
  if (!data.token || typeof data.token !== "string") {
    throw new Error("Response /generate sin field token: " + JSON.stringify(data));
  }
  return data.token as string;
}

test.describe("FASE 10.C.2 · sign-flow purposes parametrizado", () => {
  for (const config of PURPOSES) {
    if (config.deprecatedV3) {
      // ADR-020 v3 · MagicLinkPolicyEnforcer hard-rechaza la generación
      // (DEPRECATED_V3_CLIENT_FACING): el cliente hace la acción in-portal con
      // login normal. Lo que existe hoy es ese rechazo, y es lo que se prueba.
      test(config.purpose + " → rechazado (deprecated v3 · ADR-020)", async ({ page }) => {
        await loginAsMarcos(page.context());
        const projectId = await ensureTestProjectId(page);
        const csrf = (await page.context().cookies()).find(
          (c) => c.name === "fulkro_csrf",
        )?.value;
        const res = await page.request.post(
          BACKEND_BASE + "/api/v1/magic-links/generate",
          {
            headers: { "x-csrf-token": csrf ?? "" },
            data: {
              project_id: projectId,
              purpose: config.purpose,
              recipient_email: "test-client-e2e@example.com",
              scope: config.scope ?? null,
            },
          },
        );
        expect(res.status()).toBe(422);
        expect((await res.json()).detail).toMatch(/deprecated v3/i);
      });
      continue;
    }

    test(config.purpose + " → " + config.expectedComponent, async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on("console", (msg) => {
        if (
          msg.type() === "error" &&
          !msg.text().includes("Failed to load resource") &&
          !msg.text().includes("net::ERR_") &&
          !msg.text().includes("the server responded with a status")
        ) {
          consoleErrors.push(msg.text());
        }
      });

      // Auth Marcos para POST /generate (require auth · global_dep).
      await loginAsMarcos(page.context());

      const projectId = await ensureTestProjectId(page);
      const token = await generateMagicLink(page, projectId, config.purpose, config.scope);

      // Ruta /sign/[token] es pública. Limpiamos cookies por si quedaron de pasos previos.
      await page.context().clearCookies();

      await page.goto("/sign/" + token);
      await page.waitForLoadState("domcontentloaded");

      await expect(
        page.getByRole("heading").filter({ hasText: config.expectedTitle }).first(),
      ).toBeVisible({ timeout: 15_000 });

      await expect(
        page.getByText(config.expectedActionPhrase).first(),
      ).toBeVisible();

      await expect(
        page.getByRole("button", { name: config.expectedApproveButton }).first(),
      ).toBeVisible();

      expect(consoleErrors).toEqual([]);
    });
  }
});
