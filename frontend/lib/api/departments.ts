/**
 * Departments API client wrapper · sub-atom 1.C.F.2.2.
 *
 * Espejo de backend/app/motors/m30_client_contacts/department_api.py.
 * 7 endpoints REST project-scoped admin-only.
 *
 * BASE = `/api/v1/projects/{project_id}/departments` (OPS-044 sostener ·
 * full path en lugar de doble prefix wrapper).
 */
import { api } from "@/lib/api";

const base = (projectId: string) =>
  `/api/v1/projects/${projectId}/departments`;

export type Department = {
  id: string;
  project_id: string;
  code: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type DepartmentCreate = {
  code: string;
  name: string;
  description?: string | null;
};

export type DepartmentUpdate = {
  name?: string;
  description?: string | null;
};

export type DepartmentSuggestion = {
  code: string;
  name: string;
  description: string;
};

export type DepartmentSuggestionsResponse = {
  project_id: string;
  project_category: string | null;
  suggestions: DepartmentSuggestion[];
  existing_count: number;
};

export async function listDepartments(
  projectId: string,
): Promise<Department[]> {
  return api<Department[]>(base(projectId));
}

export async function getDepartmentSuggestions(
  projectId: string,
): Promise<DepartmentSuggestionsResponse> {
  return api<DepartmentSuggestionsResponse>(`${base(projectId)}/suggestions`);
}

export async function createDepartment(
  projectId: string,
  payload: DepartmentCreate,
): Promise<Department> {
  return api<Department>(base(projectId), {
    method: "POST",
    json: payload,
  });
}

export async function bulkCreateDepartments(
  projectId: string,
  items: DepartmentCreate[],
): Promise<Department[]> {
  return api<Department[]>(`${base(projectId)}/bulk`, {
    method: "POST",
    json: { items },
  });
}

export async function updateDepartment(
  projectId: string,
  departmentId: string,
  payload: DepartmentUpdate,
): Promise<Department> {
  return api<Department>(`${base(projectId)}/${departmentId}`, {
    method: "PATCH",
    json: payload,
  });
}

export async function deleteDepartment(
  projectId: string,
  departmentId: string,
): Promise<void> {
  await api<void>(`${base(projectId)}/${departmentId}`, {
    method: "DELETE",
  });
}

// ============================================================
// Sub-atom 1.C.F.3.2 · assign/bulk/list/report
// ============================================================

export type ContactSummaryForDepartment = {
  id: string;
  full_name: string;
  email: string;
  role_title: string;
  role_category: string;
  has_portal_access: boolean;
  department_id: string | null;
};

export type DepartmentReportBucket = {
  department_id: string;
  code: string;
  name: string;
  total_contacts: number;
  by_role_category: Record<string, number>;
};

export type DepartmentReport = {
  project_id: string;
  departments: DepartmentReportBucket[];
  unassigned: {
    total_contacts: number;
    by_role_category: Record<string, number>;
  };
  total_employees: number;
};

export async function assignContactToDepartment(
  projectId: string,
  contactId: string,
  departmentId: string | null,
): Promise<ContactSummaryForDepartment> {
  return api<ContactSummaryForDepartment>(
    `/api/v1/projects/${projectId}/contacts/${contactId}/department`,
    {
      method: "PATCH",
      json: { department_id: departmentId },
    },
  );
}

export async function bulkAssignContacts(
  projectId: string,
  departmentId: string,
  contactIds: string[],
): Promise<ContactSummaryForDepartment[]> {
  return api<ContactSummaryForDepartment[]>(
    `${base(projectId)}/${departmentId}/assign-contacts`,
    {
      method: "POST",
      json: { contact_ids: contactIds },
    },
  );
}

export async function listContactsForDepartment(
  projectId: string,
  departmentId: string,
): Promise<ContactSummaryForDepartment[]> {
  return api<ContactSummaryForDepartment[]>(
    `${base(projectId)}/${departmentId}/contacts`,
  );
}

export async function getDepartmentReport(
  projectId: string,
): Promise<DepartmentReport> {
  return api<DepartmentReport>(`${base(projectId)}/report`);
}
