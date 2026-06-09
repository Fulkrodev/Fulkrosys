/**
 * Fixtures compartidos · fase_27 sub-atom 1.D.F.C v3.11 · M03 DdA admin + ProjectTabs sweep.
 *
 * Cubre:
 *  - GET /api/v1/dda/projects/{id}/status → DdaStatusResponse
 *  - GET /api/v1/dda/projects/{id}/stats → DdaAdminStats
 *  - GET /api/v1/dda/projects/{id}/entries → DdaAdminEntry[]
 *  - GET /api/v1/dda/measures/catalog → DdaCatalogMeasure[]
 *  - PATCH /api/v1/dda/entries/{entry_id} → update result
 *  - POST /api/v1/dda/projects/{id}/freeze → freeze result
 *
 * Pattern reuse · OPS-045 sostenido 24ª aplicación · mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 *
 * R23 sostener firmísimo · TODO project-scoped.
 */
import type { Page } from "@playwright/test";

export const PROJECT_F27_ID = "ff271122-3344-5566-7788-99aabbccddee";

// ============================================================
// DdA status (status existing FASE 9.D · M3 admin)
// ============================================================

export const MOCK_DDA_STATUS_EXISTS = {
  project_id: PROJECT_F27_ID,
  exists: true,
  frozen: false,
  frozen_at: null,
  frozen_by: null,
  total_entries: 44,
  approved_entries: 0,
};

export const MOCK_DDA_STATUS_FROZEN = {
  project_id: PROJECT_F27_ID,
  exists: true,
  frozen: true,
  frozen_at: "2026-05-15T10:30:00Z",
  frozen_by: "Juan Pérez · RSEG",
  total_entries: 44,
  approved_entries: 44,
};

export const MOCK_DDA_STATUS_EMPTY = {
  project_id: PROJECT_F27_ID,
  exists: false,
  frozen: false,
  frozen_at: null,
  frozen_by: null,
  total_entries: 0,
  approved_entries: 0,
};

// ============================================================
// DdA stats
// ============================================================

export const MOCK_DDA_STATS_PARTIAL = {
  project_id: PROJECT_F27_ID,
  total_medidas: 73,
  total_aplicables: 44,
  no_aplica: 29,
  implantadas: 20,
  parcial: 10,
  no_implantadas: 8,
  no_valoradas: 6,
  completion_pct: 68.18,
};

// ============================================================
// DdA entries (5 sample medidas)
// ============================================================

export const MOCK_DDA_ENTRIES = [
  {
    id: "entry-uuid-001-marc1-categ1",
    project_id: PROJECT_F27_ID,
    measure_codigo: "org.1",
    measure_nombre: "Política de seguridad",
    measure_marco: "org",
    measure_familia: "org",
    aplicabilidad: "aplica",
    estado_implementacion: "implantada",
    justificacion_no_aplica: null,
    refuerzos_aplicados: null,
    magerit_safeguards: ["S.1.1"],
    responsable: "CISO",
    observaciones: null,
    version: 1,
    aprobado_por: null,
    fecha_aprobacion: null,
  },
  {
    id: "entry-uuid-002-marc1-categ2",
    project_id: PROJECT_F27_ID,
    measure_codigo: "op.exp.1",
    measure_nombre: "Inventario activos",
    measure_marco: "op",
    measure_familia: "op.exp",
    aplicabilidad: "aplica",
    estado_implementacion: "parcial",
    justificacion_no_aplica: null,
    refuerzos_aplicados: null,
    magerit_safeguards: ["S.2.1"],
    responsable: "Equipo TI",
    observaciones: "Pendiente automatización con M22 Discovery",
    version: 1,
    aprobado_por: null,
    fecha_aprobacion: null,
  },
  {
    id: "entry-uuid-003-marc2-categ1",
    project_id: PROJECT_F27_ID,
    measure_codigo: "mp.com.1",
    measure_nombre: "Protección comunicaciones",
    measure_marco: "mp",
    measure_familia: "mp.com",
    aplicabilidad: "aplica",
    estado_implementacion: "no_implantada",
    justificacion_no_aplica: null,
    refuerzos_aplicados: null,
    magerit_safeguards: [],
    responsable: null,
    observaciones: null,
    version: 1,
    aprobado_por: null,
    fecha_aprobacion: null,
  },
  {
    id: "entry-uuid-004-naomi-applica",
    project_id: PROJECT_F27_ID,
    measure_codigo: "mp.com.2",
    measure_nombre: "Cifrado canales comunicación remoto",
    measure_marco: "mp",
    measure_familia: "mp.com",
    aplicabilidad: "no_aplica",
    estado_implementacion: "no_aplica",
    justificacion_no_aplica: "Sistema no expone canales remotos al exterior · solo intranet aislada",
    refuerzos_aplicados: null,
    magerit_safeguards: [],
    responsable: "CISO",
    observaciones: null,
    version: 1,
    aprobado_por: null,
    fecha_aprobacion: null,
  },
  {
    id: "entry-uuid-005-novalor",
    project_id: PROJECT_F27_ID,
    measure_codigo: "op.cont.1",
    measure_nombre: "Continuidad servicio",
    measure_marco: "op",
    measure_familia: "op.cont",
    aplicabilidad: "aplica",
    estado_implementacion: "no_valorada",
    justificacion_no_aplica: null,
    refuerzos_aplicados: null,
    magerit_safeguards: [],
    responsable: null,
    observaciones: null,
    version: 1,
    aprobado_por: null,
    fecha_aprobacion: null,
  },
];

// ============================================================
// Catalog 73 medidas (subset 6 representativas)
// ============================================================

export const MOCK_DDA_CATALOG = [
  {
    codigo: "org.1",
    nombre: "Política de seguridad",
    marco: "org",
    familia: "org",
    descripcion: "Política aprobada por dirección · revisión anual",
    categoria_minima: "BASICA",
  },
  {
    codigo: "org.2",
    nombre: "Normativa de seguridad",
    marco: "org",
    familia: "org",
    descripcion: null,
    categoria_minima: "BASICA",
  },
  {
    codigo: "op.exp.1",
    nombre: "Inventario activos",
    marco: "op",
    familia: "op.exp",
    descripcion: "Inventario completo activos hardware + software",
    categoria_minima: "BASICA",
  },
  {
    codigo: "op.cont.1",
    nombre: "Continuidad servicio",
    marco: "op",
    familia: "op.cont",
    descripcion: null,
    categoria_minima: "MEDIA",
  },
  {
    codigo: "mp.com.1",
    nombre: "Protección comunicaciones",
    marco: "mp",
    familia: "mp.com",
    descripcion: "Cifrado canales · autenticación red",
    categoria_minima: "MEDIA",
  },
  {
    codigo: "mp.com.2",
    nombre: "Cifrado canales comunicación remoto",
    marco: "mp",
    familia: "mp.com",
    descripcion: null,
    categoria_minima: "ALTA",
  },
];

const MOCK_PROJECT_INFO = {
  id: PROJECT_F27_ID,
  nombre: "Test Cliente F27",
  client_id: "client-f27",
};

// ============================================================
// Helpers · mount mocks DdA admin
// ============================================================

interface DdaMockOptions {
  exists?: boolean;
  frozen?: boolean;
}

export async function mockDdaAdmin(
  page: Page,
  opts: DdaMockOptions = {},
) {
  const status = opts.frozen
    ? MOCK_DDA_STATUS_FROZEN
    : opts.exists === false
      ? MOCK_DDA_STATUS_EMPTY
      : MOCK_DDA_STATUS_EXISTS;

  // Project metadata
  await page.route(
    `**/api/v1/clients/projects/${PROJECT_F27_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_INFO });
    },
  );

  // DdA status
  await page.route(
    `**/api/v1/dda/projects/${PROJECT_F27_ID}/status`,
    async (route) => {
      await route.fulfill({ status: 200, json: status });
    },
  );

  // DdA stats
  await page.route(
    `**/api/v1/dda/projects/${PROJECT_F27_ID}/stats`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DDA_STATS_PARTIAL });
    },
  );

  // DdA entries
  await page.route(
    new RegExp(`/api/v1/dda/projects/${PROJECT_F27_ID}/entries`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DDA_ENTRIES });
    },
  );

  // DdA catalog
  await page.route(
    new RegExp("/api/v1/dda/measures/catalog"),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DDA_CATALOG });
    },
  );

  // PATCH entry (update)
  await page.route(
    new RegExp("/api/v1/dda/entries/[^/]+"),
    async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({
          status: 200,
          json: { id: "entry-uuid-001-marc1-categ1", version: 2, updated: true },
        });
      } else {
        await route.continue();
      }
    },
  );

  // POST freeze
  await page.route(
    `**/api/v1/dda/projects/${PROJECT_F27_ID}/freeze**`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          project_id: PROJECT_F27_ID,
          aprobado_por: "Juan Pérez · RSEG",
          fecha_aprobacion: "2026-05-21",
          frozen_entries: 44,
        },
      });
    },
  );

  // POST unfreeze
  await page.route(
    `**/api/v1/dda/projects/${PROJECT_F27_ID}/unfreeze`,
    async (route) => {
      await route.fulfill({ status: 204 });
    },
  );
}

// ============================================================
// Project features (para ProjectTabs feature flags · MEDIA por default)
// ============================================================

export async function mockProjectFeaturesMedia(page: Page) {
  // El endpoint real es /feature-flags (renombrado desde /features) ·
  // verificado en lib/api/feature-flags.ts → getProjectFeatureFlags. El path
  // viejo /features no interceptaba nada → el provider pegaba al backend real
  // con el UUID falso del fixture (404 lento). R23 sostener · MEDIA por default.
  await page.route(
    `**/api/v1/projects/${PROJECT_F27_ID}/feature-flags`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          project_id: PROJECT_F27_ID,
          categoria: "MEDIA",
          archetype: "proveedor_financiero",
          features: {},
        },
      });
    },
  );
}
