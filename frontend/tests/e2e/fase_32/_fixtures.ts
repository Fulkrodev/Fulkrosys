/**
 * Fixtures fase_32 · Cloud Connectors cliente onboarding (sub-atom 1.D.X.I v3.12).
 *
 * Mocks API cliente:
 *   GET  /api/v1/client-portal/cloud-connectors/providers/catalog
 *   GET  /api/v1/client-portal/cloud-connectors
 *   POST /api/v1/client-portal/cloud-connectors/connect/{provider}
 */
import type { Page } from "@playwright/test";

export const PROJECT_F32_ID = "f32f32f3-2f32-4f32-bf32-f32f32f32f32";

const PROVIDERS_CATALOG = [
  {
    provider: "microsoft_365",
    display_name: "Microsoft 365 / Entra ID",
    icon_emoji: "🔵",
    requires_oauth: true,
    cliente_friendly_blurb:
      "Cuentas, grupos y MFA · solo lectura · 5 minutos. Detectamos usuarios sin MFA y privilegios excesivos.",
  },
  {
    provider: "google_workspace",
    display_name: "Google Workspace",
    icon_emoji: "🟢",
    requires_oauth: true,
    cliente_friendly_blurb:
      "Usuarios, grupos y dispositivos · solo lectura · verificamos MFA y políticas Workspace.",
  },
  {
    provider: "azure",
    display_name: "Azure",
    icon_emoji: "🟦",
    requires_oauth: true,
    cliente_friendly_blurb:
      "Recursos cloud Azure · subscripciones y resource groups · solo lectura · detectamos configuraciones inseguras.",
  },
  {
    provider: "aws",
    display_name: "AWS",
    icon_emoji: "🟧",
    requires_oauth: false,
    cliente_friendly_blurb:
      "IAM, buckets y EC2 · pegar Access Key con permisos solo lectura · detectamos buckets públicos y IAM sin MFA.",
  },
  {
    provider: "github",
    display_name: "GitHub",
    icon_emoji: "⚫",
    requires_oauth: true,
    cliente_friendly_blurb:
      "Si desarrollas software · repos, miembros y secrets · solo lectura · detectamos secrets expuestos.",
  },
  {
    provider: "manual_import",
    display_name: "Subir inventario manual",
    icon_emoji: "📊",
    requires_oauth: false,
    cliente_friendly_blurb:
      "Sube un Excel con tus sistemas · te ayudamos a construir el inventario · funciona perfecto como fallback.",
  },
];

interface ConnectorSummary {
  id: string; // Sesión 3B-2B.8 Phase 1C · connector_id propio
  provider: string;
  status: string;
  last_sync_at: string | null;
  resources_count: number;
  friendly_message: string;
}

interface ConnectorsList {
  items: ConnectorSummary[];
  project_id: string;
}

const CONNECTORS_EMPTY: ConnectorsList = {
  items: [],
  project_id: PROJECT_F32_ID,
};

const CONNECTORS_WITH_M365_CONNECTED: ConnectorsList = {
  items: [
    {
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      provider: "microsoft_365",
      status: "connected",
      last_sync_at: "2026-05-21T14:00:00Z",
      resources_count: 42,
      friendly_message: "✓ Microsoft 365 conectado · 42 elementos detectados.",
    },
  ],
  project_id: PROJECT_F32_ID,
};

/**
 * Mock base: catalog + list vacío + project resolve.
 */
export async function mockCloudConnectClientBase(
  page: Page,
  opts: { connectorsList?: ConnectorsList } = {},
) {
  const connectorsList = opts.connectorsList ?? CONNECTORS_EMPTY;

  await page.route(
    "**/api/v1/client-portal/project",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: PROJECT_F32_ID,
          nombre: "Cliente Piloto F32",
          estado: "ACTIVE",
        }),
      });
    },
  );

  await page.route(
    "**/api/v1/client-portal/cloud-connectors/providers/catalog",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: PROVIDERS_CATALOG }),
      });
    },
  );

  await page.route(
    "**/api/v1/client-portal/cloud-connectors",
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(connectorsList),
        });
      } else {
        await route.continue();
      }
    },
  );
}

/**
 * Mock connect-flow init · responde según provider.
 *
 * B1: el oauth_redirect ahora devuelve `m16_connector_type` (el short name de
 * M16) y el front llama al endpoint REAL M16 oauth-init para obtener el
 * authorize_url. Mockeamos ambos pasos (connect + oauth-init).
 */
const _M16_CONNECTOR_TYPE: Record<string, string> = {
  microsoft_365: "microsoft",
  google_workspace: "google",
  azure: "azure",
  github: "github",
};

export async function mockCloudConnectInitFlow(
  page: Page,
  opts: { provider: string; nextStep: "oauth_redirect" | "manual_upload" },
) {
  const connectorType =
    _M16_CONNECTOR_TYPE[opts.provider] ?? opts.provider;

  await page.route(
    `**/api/v1/client-portal/cloud-connectors/connect/${opts.provider}`,
    async (route) => {
      const body =
        opts.nextStep === "oauth_redirect"
          ? {
              connector_id: "11111111-1111-1111-1111-111111111111",
              provider: opts.provider,
              next_step: "oauth_redirect",
              m16_connector_type: connectorType,
              message: "Te llevamos a autorizar de forma segura · solo lectura.",
            }
          : {
              connector_id: "22222222-2222-2222-2222-222222222222",
              provider: opts.provider,
              next_step: "manual_upload",
              message: "Sube tu Excel/CSV en la siguiente pantalla.",
            };
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );

  if (opts.nextStep === "oauth_redirect") {
    // Paso 2 · M16 oauth-init real → authorize_url. Apuntamos a una ruta
    // same-origin benigna para que la navegación final no rompa el test.
    await page.route(
      `**/portal/onboarding/projects/*/connectors/${connectorType}/oauth-init`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            authorize_url: "/client-portal/onboarding?oauth=mock",
            state: "test-state-token",
          }),
        });
      },
    );
  }
}

export { CONNECTORS_EMPTY, CONNECTORS_WITH_M365_CONNECTED, PROVIDERS_CATALOG };
