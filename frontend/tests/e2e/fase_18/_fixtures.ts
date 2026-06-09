/**
 * Fixtures compartidos · fase_18 sub-atom 1.C.F.5 v3.10 tests E2E.
 *
 * Cubre el sub-atom 1.C.F completo (Equipo del proyecto):
 *   - 1.C.F.1 portal user + tabs render
 *   - 1.C.F.2 departments project-scoped + suggestions ENS-aware per category
 *   - 1.C.F.3 empleados ↔ departments distribution
 *   - 1.C.F.4 roles ENS RD 311/2022 priority per category + assign/vacate
 *
 * Pattern reuse · OPS-045 sostenido (caso 19 prevista): mocks page.route
 * spec-as-code ARTIFACT · NO live backend needed (paridad fase_17).
 */
import type { Page } from "@playwright/test";

export const PROJECT_F_ID = "ffffffff-1111-2222-3333-444444444444";
export const CLIENT_F_ID = "ffffffff-aaaa-bbbb-cccc-dddddddddddd";

const DEPT_TI_ID = "11111111-aaaa-bbbb-cccc-000000000001";
const DEPT_COMP_ID = "11111111-aaaa-bbbb-cccc-000000000002";

const CONTACT_ALICIA_ID = "22222222-aaaa-bbbb-cccc-000000000001";
const CONTACT_BERNARDO_ID = "22222222-aaaa-bbbb-cccc-000000000002";
const CONTACT_CARLA_ID = "22222222-aaaa-bbbb-cccc-000000000003";

// ============================================================
// Project metadata (header / ProjectTabs)
// ============================================================

export const MOCK_PROJECT_INFO = {
  id: PROJECT_F_ID,
  nombre: "Fintech Plus SL",
  client_id: CLIENT_F_ID,
  categoria_objetivo: "MEDIA",
};

// ============================================================
// Portal user (1.C.F.1.1)
// ============================================================

export const MOCK_PORTAL_USER_EMPTY = {
  project_id: PROJECT_F_ID,
  client_id: CLIENT_F_ID,
  client_user: null,
  portal_contact: null,
  complete: false,
};

export const MOCK_PORTAL_USER_ENSURED = {
  project_id: PROJECT_F_ID,
  client_id: CLIENT_F_ID,
  client_user: {
    id: "33333333-aaaa-bbbb-cccc-000000000001",
    email: "poc@fintechplus.es",
    full_name: "PoC FintechPlus",
    must_change_password: true,
    last_login: null,
  },
  portal_contact: {
    id: "33333333-aaaa-bbbb-cccc-000000000002",
    full_name: "PoC FintechPlus",
    email: "poc@fintechplus.es",
    role_title: "Punto de Contacto",
    role_category: "sponsor",
    client_user_id: "33333333-aaaa-bbbb-cccc-000000000001",
  },
  complete: true,
};

// ============================================================
// Project contacts (1.C.F.1 + 1.C.F.3)
// ============================================================

export const MOCK_CONTACTS_EMPLOYEES = [
  {
    id: CONTACT_ALICIA_ID,
    client_id: CLIENT_F_ID,
    project_id: PROJECT_F_ID,
    full_name: "Alicia Muñoz",
    email: "alicia@fintechplus.es",
    phone: null,
    linkedin_url: null,
    role_title: "CISO",
    role_category: "ciso",
    is_primary: false,
    is_signatory: true,
    has_portal_access: false,
    notes_marcos: null,
    is_active: true,
    created_at: "2026-05-01T10:00:00Z",
    department_id: null,
  },
  {
    id: CONTACT_BERNARDO_ID,
    client_id: CLIENT_F_ID,
    project_id: PROJECT_F_ID,
    full_name: "Bernardo López",
    email: "bernardo@fintechplus.es",
    phone: null,
    linkedin_url: null,
    role_title: "Técnico",
    role_category: "tecnico",
    is_primary: false,
    is_signatory: false,
    has_portal_access: false,
    notes_marcos: null,
    is_active: true,
    created_at: "2026-05-02T10:00:00Z",
    department_id: null,
  },
  {
    id: CONTACT_CARLA_ID,
    client_id: CLIENT_F_ID,
    project_id: PROJECT_F_ID,
    full_name: "Carla Ruiz",
    email: "carla@fintechplus.es",
    phone: null,
    linkedin_url: null,
    role_title: "DPO",
    role_category: "dpo",
    is_primary: false,
    is_signatory: false,
    has_portal_access: false,
    notes_marcos: null,
    is_active: true,
    created_at: "2026-05-03T10:00:00Z",
    department_id: null,
  },
];

export const MOCK_CONTACTS_LIST_RESPONSE = {
  project_id: PROJECT_F_ID,
  contacts: MOCK_CONTACTS_EMPLOYEES,
  total: MOCK_CONTACTS_EMPLOYEES.length,
  with_portal_access: 0,
};

// ============================================================
// Departments (1.C.F.2)
// ============================================================

export const MOCK_DEPARTMENTS_EMPTY: never[] = [];

export const MOCK_DEPT_TI = {
  id: DEPT_TI_ID,
  project_id: PROJECT_F_ID,
  code: "TI",
  name: "Tecnologías de la Información",
  description: "Operación y administración sistemas TI",
  created_at: "2026-05-01T10:00:00Z",
  updated_at: "2026-05-01T10:00:00Z",
};

export const MOCK_DEPT_COMP = {
  id: DEPT_COMP_ID,
  project_id: PROJECT_F_ID,
  code: "COMPLIANCE",
  name: "Compliance + RGPD",
  description: "Cumplimiento normativo, DPO, riesgos",
  created_at: "2026-05-01T10:00:00Z",
  updated_at: "2026-05-01T10:00:00Z",
};

export const MOCK_DEPARTMENTS_MEDIA = [MOCK_DEPT_TI, MOCK_DEPT_COMP];

export const MOCK_DEPT_SUGGESTIONS_MEDIA_EMPTY = {
  project_id: PROJECT_F_ID,
  project_category: "MEDIA",
  suggestions: [
    {
      code: "TI",
      name: "Tecnologías de la Información",
      description: "Operación y administración sistemas TI",
    },
    {
      code: "COMPLIANCE",
      name: "Compliance + RGPD",
      description: "Cumplimiento normativo, DPO, riesgos",
    },
  ],
  existing_count: 0,
};

export const MOCK_DEPT_SUGGESTIONS_MEDIA_FILLED = {
  ...MOCK_DEPT_SUGGESTIONS_MEDIA_EMPTY,
  existing_count: 2,
};

export const MOCK_DEPT_REPORT_TI_FILLED = {
  project_id: PROJECT_F_ID,
  departments: [
    {
      department_id: DEPT_TI_ID,
      code: "TI",
      name: "Tecnologías de la Información",
      total_contacts: 1,
      by_role_category: { tecnico: 1 },
    },
    {
      department_id: DEPT_COMP_ID,
      code: "COMPLIANCE",
      name: "Compliance + RGPD",
      total_contacts: 0,
      by_role_category: {},
    },
  ],
  unassigned: {
    total_contacts: 2,
    by_role_category: { ciso: 1, dpo: 1 },
  },
  total_employees: 3,
};

export const MOCK_DEPT_REPORT_EMPTY = {
  project_id: PROJECT_F_ID,
  departments: [
    {
      department_id: DEPT_TI_ID,
      code: "TI",
      name: "Tecnologías de la Información",
      total_contacts: 0,
      by_role_category: {},
    },
    {
      department_id: DEPT_COMP_ID,
      code: "COMPLIANCE",
      name: "Compliance + RGPD",
      total_contacts: 0,
      by_role_category: {},
    },
  ],
  unassigned: {
    total_contacts: 3,
    by_role_category: { ciso: 1, tecnico: 1, dpo: 1 },
  },
  total_employees: 3,
};

export const MOCK_DEPT_CONTACTS_TI_WITH_BERNARDO = [
  {
    id: CONTACT_BERNARDO_ID,
    full_name: "Bernardo López",
    email: "bernardo@fintechplus.es",
    role_title: "Técnico",
    role_category: "tecnico",
    has_portal_access: false,
    department_id: DEPT_TI_ID,
  },
];

// ============================================================
// ENS required roles (1.C.F.4)
// ============================================================

export const MOCK_ENS_PRIORITY_MEDIA = {
  sponsor: "critical",
  responsable_informacion: "critical",
  responsable_servicio: "critical",
  responsable_seguridad: "critical",
  responsable_sistema: "critical",
  administrador_seguridad: "recommended",
};

type EnsRoleAssignmentMock = {
  contact_id: string;
  full_name: string;
  email: string;
  role_title: string;
} | null;

type EnsRolesStatusMock = {
  project_id: string;
  client_id: string;
  project_category: string;
  priority: Record<string, string>;
  roles: Record<string, EnsRoleAssignmentMock>;
  all_assigned: boolean;
  missing: string[];
  critical_missing: string[];
  total_assigned: number;
  total_required: number;
};

export const MOCK_ENS_ROLES_EMPTY_MEDIA: EnsRolesStatusMock = {
  project_id: PROJECT_F_ID,
  client_id: CLIENT_F_ID,
  project_category: "MEDIA",
  priority: MOCK_ENS_PRIORITY_MEDIA,
  roles: {
    sponsor: null,
    responsable_informacion: null,
    responsable_servicio: null,
    responsable_seguridad: null,
    responsable_sistema: null,
    administrador_seguridad: null,
  },
  all_assigned: false,
  missing: [
    "sponsor",
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
  ],
  critical_missing: [
    "sponsor",
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
  ],
  total_assigned: 0,
  total_required: 6,
};

export const MOCK_ENS_ROLES_RI_ASSIGNED_MEDIA: EnsRolesStatusMock = {
  ...MOCK_ENS_ROLES_EMPTY_MEDIA,
  roles: {
    ...MOCK_ENS_ROLES_EMPTY_MEDIA.roles,
    responsable_informacion: {
      contact_id: CONTACT_ALICIA_ID,
      full_name: "Alicia Muñoz",
      email: "alicia@fintechplus.es",
      role_title: "CISO",
    },
  },
  missing: [
    "sponsor",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
  ],
  critical_missing: [
    "sponsor",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
  ],
  total_assigned: 1,
};

// ============================================================
// Helpers · mock setups per tab
// ============================================================

export async function mockEquipoCommon(page: Page) {
  // ProjectTabs metadata.
  await page.route(
    new RegExp(`/api/v1/clients/projects/${PROJECT_F_ID}$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_INFO });
    },
  );
  // Some pages also call /api/v1/projects/{id}/info (best effort fallback).
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/info$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_INFO });
    },
  );
}

export async function mockPortalUserEmpty(page: Page) {
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/portal-user$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PORTAL_USER_EMPTY });
    },
  );
}

export async function mockPortalUserEnsured(page: Page) {
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/portal-user$`),
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          json: {
            project_id: PROJECT_F_ID,
            client_id: CLIENT_F_ID,
            client_user_id: "33333333-aaaa-bbbb-cccc-000000000001",
            portal_contact_id: "33333333-aaaa-bbbb-cccc-000000000002",
            created_user: true,
            created_contact: true,
            temp_password: "Tmp-Pass-Mock123",
          },
        });
        return;
      }
      await route.fulfill({ status: 200, json: MOCK_PORTAL_USER_ENSURED });
    },
  );
}

export async function mockProjectContactsEmployees(page: Page) {
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/contacts$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CONTACTS_LIST_RESPONSE });
    },
  );
}

export async function mockDepartmentsEmptyMedia(page: Page) {
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/departments$`),
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          json: MOCK_DEPT_TI,
        });
        return;
      }
      await route.fulfill({ status: 200, json: MOCK_DEPARTMENTS_EMPTY });
    },
  );
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_F_ID}/departments/suggestions$`,
    ),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_DEPT_SUGGESTIONS_MEDIA_EMPTY,
      });
    },
  );
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/departments/bulk$`),
    async (route) => {
      await route.fulfill({
        status: 201,
        json: MOCK_DEPARTMENTS_MEDIA,
      });
    },
  );
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/departments/report$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DEPT_REPORT_EMPTY });
    },
  );
}

export async function mockDepartmentsFilledMedia(page: Page) {
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/departments$`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DEPARTMENTS_MEDIA });
    },
  );
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_F_ID}/departments/suggestions$`,
    ),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_DEPT_SUGGESTIONS_MEDIA_FILLED,
      });
    },
  );
  await page.route(
    new RegExp(`/api/v1/projects/${PROJECT_F_ID}/departments/report$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_DEPT_REPORT_TI_FILLED,
      });
    },
  );
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_F_ID}/departments/${DEPT_TI_ID}/contacts$`,
    ),
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_DEPT_CONTACTS_TI_WITH_BERNARDO,
      });
    },
  );
  // PATCH contact department assignment
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_F_ID}/contacts/[^/]+/department$`,
    ),
    async (route) => {
      if (route.request().method() === "PATCH") {
        await route.fulfill({
          status: 200,
          json: {
            id: CONTACT_BERNARDO_ID,
            full_name: "Bernardo López",
            email: "bernardo@fintechplus.es",
            role_title: "Técnico",
            role_category: "tecnico",
            has_portal_access: false,
            department_id: DEPT_TI_ID,
          },
        });
        return;
      }
      await route.continue();
    },
  );
}

export async function mockEnsRolesEmptyMedia(page: Page) {
  let currentStatus = MOCK_ENS_ROLES_EMPTY_MEDIA;
  await page.route(
    new RegExp(
      `/api/v1/admin/projects/${PROJECT_F_ID}/ens-required-roles$`,
    ),
    async (route) => {
      await route.fulfill({ status: 200, json: currentStatus });
    },
  );
  // PATCH assign role → after this, GET returns RI assigned variant.
  await page.route(
    new RegExp(
      `/api/v1/admin/projects/${PROJECT_F_ID}/ens-required-roles/responsable_informacion$`,
    ),
    async (route) => {
      if (route.request().method() === "PATCH") {
        currentStatus = MOCK_ENS_ROLES_RI_ASSIGNED_MEDIA;
        await route.fulfill({
          status: 200,
          json: {
            role: "responsable_informacion",
            contact_id: CONTACT_ALICIA_ID,
            full_name: "Alicia Muñoz",
            email: "alicia@fintechplus.es",
            role_title: "CISO",
          },
        });
        return;
      }
      await route.continue();
    },
  );
}

export const TEST_IDS = {
  PROJECT_F_ID,
  CLIENT_F_ID,
  DEPT_TI_ID,
  DEPT_COMP_ID,
  CONTACT_ALICIA_ID,
  CONTACT_BERNARDO_ID,
  CONTACT_CARLA_ID,
};
