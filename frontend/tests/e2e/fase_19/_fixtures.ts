/**
 * Fixtures compartidos · fase_19 sub-atom 1.C.G.C v3.10 tests E2E IDMS.
 *
 * Cubre sub-atom 1.C.G v3.10 completo (gestor documental admin+cliente):
 *   - 1.C.G.A admin enrichment (tree + upload + viewer + version history)
 *   - 1.C.G.B cliente enrichment (tree friendly + upload permission-limited)
 *   - R30 inverso verify (admin actions invisible cliente)
 *
 * Pattern reuse · OPS-045 sostenido (12ª aplicación consecutiva): mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend (paridad fase_17/18).
 *
 * Decisión arquitectural: m24_idms = m_dms identity confirmed audit-first.
 * NO crear motor m_dms paralelo · reuse 27 endpoints idms existing.
 */
import type { Page } from "@playwright/test";

export const PROJECT_G_ID = "ddddeeee-1111-2222-3333-444444444444";
export const CLIENT_G_ID = "ddddeeee-aaaa-bbbb-cccc-555555555555";

// 15 carpetas estándar K.0..K.6+retainer · canonical IDMS structure.
const FOLDER_00 = "00000000-1111-1111-1111-000000000001";
const FOLDER_01 = "00000000-1111-1111-1111-000000000002";
const FOLDER_02 = "00000000-1111-1111-1111-000000000003";
const FOLDER_03 = "00000000-1111-1111-1111-000000000004";
const FOLDER_04 = "00000000-1111-1111-1111-000000000005";
const FOLDER_05 = "00000000-1111-1111-1111-000000000006";
const FOLDER_06 = "00000000-1111-1111-1111-000000000007";
const FOLDER_07 = "00000000-1111-1111-1111-000000000008";
const FOLDER_08 = "00000000-1111-1111-1111-000000000009";
const FOLDER_09 = "00000000-1111-1111-1111-00000000000a";
const FOLDER_10 = "00000000-1111-1111-1111-00000000000b";
const FOLDER_11 = "00000000-1111-1111-1111-00000000000c";
const FOLDER_12 = "00000000-1111-1111-1111-00000000000d";
const FOLDER_13 = "00000000-1111-1111-1111-00000000000e";
const FOLDER_99 = "00000000-1111-1111-1111-00000000000f";

const DOC_POLITICA_ID = "aaaa1111-bbbb-cccc-dddd-000000000001";
const DOC_PROCEDIMIENTO_ID = "aaaa1111-bbbb-cccc-dddd-000000000002";
const DOC_EVIDENCIA_ID = "aaaa1111-bbbb-cccc-dddd-000000000003";

// ============================================================
// 15 standard folders (admin tree · K.0..K.6 + 99 misc)
// ============================================================

export const MOCK_15_FOLDERS_TREE_ADMIN = [
  {
    id: FOLDER_00,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "00_Contractual",
    virtual_path: "/00_Contractual/",
    is_standard: true,
    standard_code: "00",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_01,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "01_Gobierno",
    virtual_path: "/01_Gobierno/",
    is_standard: true,
    standard_code: "01",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_02,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "02_Categorizacion",
    virtual_path: "/02_Categorizacion/",
    is_standard: true,
    standard_code: "02",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_03,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "03_Analisis_Riesgos",
    virtual_path: "/03_Analisis_Riesgos/",
    is_standard: true,
    standard_code: "03",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_04,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "04_Declaracion_Aplicabilidad",
    virtual_path: "/04_Declaracion_Aplicabilidad/",
    is_standard: true,
    standard_code: "04",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_05,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "05_Plan_Adecuacion",
    virtual_path: "/05_Plan_Adecuacion/",
    is_standard: true,
    standard_code: "05",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_06,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "06_Normativa",
    virtual_path: "/06_Normativa/",
    is_standard: true,
    standard_code: "06",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_07,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "07_Procedimientos",
    virtual_path: "/07_Procedimientos/",
    is_standard: true,
    standard_code: "07",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_08,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "08_Registros_Operativos",
    virtual_path: "/08_Registros_Operativos/",
    is_standard: true,
    standard_code: "08",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_09,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "09_Evidencias",
    virtual_path: "/09_Evidencias/",
    is_standard: true,
    standard_code: "09",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_10,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "10_Continuidad",
    virtual_path: "/10_Continuidad/",
    is_standard: true,
    standard_code: "10",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_11,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "11_Formacion",
    virtual_path: "/11_Formacion/",
    is_standard: true,
    standard_code: "11",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_12,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "12_Proveedores",
    virtual_path: "/12_Proveedores/",
    is_standard: true,
    standard_code: "12",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_13,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "13_Informes_Tecnicos",
    virtual_path: "/13_Informes_Tecnicos/",
    is_standard: true,
    standard_code: "13",
    custom_order: 0,
    children: [],
  },
  {
    id: FOLDER_99,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "99_Misc",
    virtual_path: "/99_Misc/",
    is_standard: true,
    standard_code: "99",
    custom_order: 0,
    children: [],
  },
];

// Cliente folders flat (mismo set · backend retorna flat · frontend rebuilds tree)
export const MOCK_15_FOLDERS_FLAT_CLIENT = MOCK_15_FOLDERS_TREE_ADMIN.map(
  (f) => ({
    id: f.id,
    parent_folder_id: f.parent_folder_id,
    name: f.name,
    virtual_path: f.virtual_path,
    is_standard: f.is_standard,
    standard_code: f.standard_code,
    custom_order: f.custom_order,
  }),
);

// ============================================================
// Documents · admin (m24_idms endpoint shape)
// ============================================================

export const MOCK_DOC_POLITICA_ADMIN = {
  id: DOC_POLITICA_ID,
  project_id: PROJECT_G_ID,
  nombre: "PSI_v2.docx",
  tipo: "policy",
  template_codigo: "E-100",
  folder_id: FOLDER_06,
  content_hash: "abc123def456" + "0".repeat(52),
  file_size_bytes: 45_678,
  storage_path: "/minio/fulkro-documents/PSI_v2.docx",
  estado: "approved",
  clasificacion: "politica",
  version_actual: "2.0",
  approved_by_user_id: null,
  approved_at: "2026-05-10T10:00:00Z",
  expires_at: null,
  review_period_months: 12,
  created_at: "2026-05-01T10:00:00Z",
};

export const MOCK_DOC_PROCEDIMIENTO_ADMIN = {
  id: DOC_PROCEDIMIENTO_ID,
  project_id: PROJECT_G_ID,
  nombre: "Procedimiento_Backup.docx",
  tipo: "procedure",
  template_codigo: "E-202",
  folder_id: FOLDER_07,
  content_hash: "def456abc123" + "0".repeat(52),
  file_size_bytes: 32_100,
  storage_path: "/minio/fulkro-documents/Procedimiento_Backup.docx",
  estado: "draft",
  clasificacion: "procedimiento",
  version_actual: "1.0",
  approved_by_user_id: null,
  approved_at: null,
  expires_at: null,
  review_period_months: null,
  created_at: "2026-05-05T10:00:00Z",
};

export const MOCK_DOC_EVIDENCIA_ADMIN = {
  id: DOC_EVIDENCIA_ID,
  project_id: PROJECT_G_ID,
  nombre: "Certificado_ISO27001.pdf",
  tipo: "evidence",
  template_codigo: null,
  folder_id: FOLDER_09,
  content_hash: "evi789xyz123" + "0".repeat(52),
  file_size_bytes: 256_789,
  storage_path: "/minio/fulkro-documents/Certificado_ISO27001.pdf",
  estado: "approved",
  clasificacion: "evidencia",
  version_actual: "1.0",
  approved_by_user_id: null,
  approved_at: "2026-05-08T10:00:00Z",
  expires_at: "2027-05-08T10:00:00Z",
  review_period_months: 12,
  created_at: "2026-05-08T10:00:00Z",
};

export const MOCK_DOCUMENTS_ADMIN_ALL = [
  MOCK_DOC_POLITICA_ADMIN,
  MOCK_DOC_PROCEDIMIENTO_ADMIN,
  MOCK_DOC_EVIDENCIA_ADMIN,
];

// Document detail (single response · with tags + versions + folder)
export const MOCK_DOC_DETAIL_POLITICA = {
  ...MOCK_DOC_POLITICA_ADMIN,
  tags: [
    {
      id: "tag-uuid-001",
      document_id: DOC_POLITICA_ID,
      tag_type: "measure_ens",
      tag_value: "op.pl.1",
      confidence: 1.0,
      source: "manual",
      created_at: "2026-05-01T10:00:00Z",
    },
    {
      id: "tag-uuid-002",
      document_id: DOC_POLITICA_ID,
      tag_type: "measure_ens",
      tag_value: "org.1",
      confidence: 1.0,
      source: "manual",
      created_at: "2026-05-01T10:00:00Z",
    },
  ],
  versions: [
    {
      id: "ver-uuid-001",
      document_id: DOC_POLITICA_ID,
      version: "2.0",
      hash_sha256: "abc123def456" + "0".repeat(52),
      contenido_path: "/minio/v2.docx",
      generado_por: "marcos",
      generado_at: "2026-05-10T10:00:00Z",
    },
    {
      id: "ver-uuid-002",
      document_id: DOC_POLITICA_ID,
      version: "1.0",
      hash_sha256: "old111aaa222" + "0".repeat(52),
      contenido_path: "/minio/v1.docx",
      generado_por: "marcos",
      generado_at: "2026-04-15T10:00:00Z",
    },
  ],
  folder: {
    id: FOLDER_06,
    project_id: PROJECT_G_ID,
    parent_folder_id: null,
    name: "06_Normativa",
    virtual_path: "/06_Normativa/",
    is_standard: true,
    standard_code: "06",
    custom_order: 0,
  },
};

// Version history endpoint (separate from detail)
export const MOCK_VERSION_HISTORY_POLITICA = {
  versions: MOCK_DOC_DETAIL_POLITICA.versions,
};

// IDMS stats (existing IdmsWorkbench backward-compat)
export const MOCK_IDMS_STATS = {
  total_documents: 3,
  total_folders: 15,
  total_size_bytes: 334_567,
  by_estado: { approved: 2, draft: 1 },
  by_clasificacion: { politica: 1, procedimiento: 1, evidencia: 1 },
};

export const MOCK_IDMS_EXPIRING_EMPTY: { documents: [] } = { documents: [] };

// ============================================================
// Cliente · documents (client-portal endpoint shape · folder_id + folder_name)
// ============================================================

export const MOCK_CLIENT_DOC_POLITICA = {
  id: DOC_POLITICA_ID,
  codigo: "E-100",
  version: "2.0",
  created_at: "2026-05-01T10:00:00Z",
  estado: "approved",
  clasificacion: "politica",
  nombre: "PSI_v2.docx",
  file_size_bytes: 45_678,
  pdf_path: "/minio/PSI_v2.pdf",
  docx_path: "/minio/PSI_v2.docx",
  storage_path: null,
  folder_id: FOLDER_06,
  folder_name: "06_Normativa",
  folder_path: "/06_Normativa/",
};

export const MOCK_CLIENT_DOC_EVIDENCIA = {
  id: DOC_EVIDENCIA_ID,
  codigo: null,
  version: "1.0",
  created_at: "2026-05-08T10:00:00Z",
  estado: "approved",
  clasificacion: "evidencia",
  nombre: "Certificado_ISO27001.pdf",
  file_size_bytes: 256_789,
  pdf_path: "/minio/Certificado_ISO27001.pdf",
  docx_path: null,
  storage_path: null,
  folder_id: FOLDER_09,
  folder_name: "09_Evidencias",
  folder_path: "/09_Evidencias/",
};

export const MOCK_CLIENT_DOCUMENTS = [
  MOCK_CLIENT_DOC_POLITICA,
  MOCK_CLIENT_DOC_EVIDENCIA,
];

export const MOCK_CLIENT_EVIDENCE_EMPTY: never[] = [];

// ============================================================
// Helpers · mock setup admin
// ============================================================

export async function mockAdminIdmsBase(page: Page) {
  // Folder tree (m24_idms)
  await page.route(
    new RegExp(
      `/api/v1/idms/projects/${PROJECT_G_ID}/idms/folders/tree$`,
    ),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_15_FOLDERS_TREE_ADMIN });
    },
  );

  // List documents (ALL · used by tree counts + DocumentList)
  await page.route(
    new RegExp(
      `/api/v1/idms/projects/${PROJECT_G_ID}/idms/documents(\\?.*)?$`,
    ),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: { documents: MOCK_DOCUMENTS_ADMIN_ALL },
      });
    },
  );

  // Stats (IdmsWorkbench)
  await page.route(
    new RegExp(`/api/v1/idms/projects/${PROJECT_G_ID}/idms/stats$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_IDMS_STATS });
    },
  );

  // Expiring (IdmsWorkbench)
  await page.route(
    new RegExp(
      `/api/v1/idms/projects/${PROJECT_G_ID}/idms/documents/expiring$`,
    ),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_IDMS_EXPIRING_EMPTY });
    },
  );

  // Document detail (viewer modal)
  await page.route(
    new RegExp(
      `/api/v1/idms/projects/${PROJECT_G_ID}/idms/documents/${DOC_POLITICA_ID}$`,
    ),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DOC_DETAIL_POLITICA });
    },
  );

  // Version history endpoint
  await page.route(
    new RegExp(
      `/api/v1/idms/projects/${PROJECT_G_ID}/idms/documents/${DOC_POLITICA_ID}/versions$`,
    ),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_VERSION_HISTORY_POLITICA,
      });
    },
  );

  // Intake upload (mock success)
  await page.route(
    new RegExp(`/api/v1/idms/projects/${PROJECT_G_ID}/idms/intake$`),
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          json: {
            document: MOCK_DOC_PROCEDIMIENTO_ADMIN,
            duplicate: false,
            content_hash: MOCK_DOC_PROCEDIMIENTO_ADMIN.content_hash,
            tags: [],
          },
        });
        return;
      }
      await route.continue();
    },
  );

  // Standard folders catalog
  await page.route(
    new RegExp(`/api/v1/idms/standard-folders$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          folders: MOCK_15_FOLDERS_TREE_ADMIN.map((f) => ({
            code: f.standard_code,
            name: f.name,
            path: f.virtual_path,
          })),
          count: 15,
        },
      });
    },
  );
}

// ============================================================
// Helpers · mock setup cliente
// ============================================================

export async function mockClientIdmsBase(page: Page) {
  // Cliente project_id resolution
  await page.route(
    new RegExp(`/api/v1/client-portal/project$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: { id: PROJECT_G_ID },
      });
    },
  );

  // Cliente folders tree (flat list)
  await page.route(
    new RegExp(`/api/v1/client-portal/folders/tree$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_15_FOLDERS_FLAT_CLIENT,
      });
    },
  );

  // Cliente documents list
  await page.route(
    new RegExp(`/api/v1/client-portal/documents(\\?.*)?$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CLIENT_DOCUMENTS });
    },
  );

  // Cliente evidence list (empty for our scope)
  await page.route(
    new RegExp(`/api/v1/client-portal/evidence(\\?.*)?$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CLIENT_EVIDENCE_EMPTY });
    },
  );

  // Cliente upload (mock success)
  await page.route(
    new RegExp(`/api/v1/client-portal/documents/upload$`),
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          json: {
            id: "uploaded-uuid-001",
            nombre: "test-upload.pdf",
            folder_id: FOLDER_09,
            content_hash: "newhash" + "0".repeat(57),
            file_size_bytes: 12_345,
          },
        });
        return;
      }
      await route.continue();
    },
  );
}

export const TEST_IDS = {
  PROJECT_G_ID,
  CLIENT_G_ID,
  FOLDER_06,
  FOLDER_07,
  FOLDER_09,
  DOC_POLITICA_ID,
  DOC_PROCEDIMIENTO_ID,
  DOC_EVIDENCIA_ID,
};
