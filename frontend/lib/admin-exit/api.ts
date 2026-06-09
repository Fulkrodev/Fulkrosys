/**
 * Admin Exit Checklist API client (SAN-E v3.MB-3.1).
 *
 * Wired al backend M25 exit-checklist (commit MB-3.A · 5 endpoints):
 *   GET    /api/v1/projects/{id}/exit-checklist
 *   POST   /api/v1/projects/{id}/exit-checklist/{item_id}/complete
 *   POST   /api/v1/projects/{id}/exit-checklist/{item_id}/uncomplete
 *   POST   /api/v1/projects/{id}/exit-checklist/{item_id}/set-status
 *   POST   /api/v1/projects/{id}/exit-checklist/check-readiness
 *
 * ADR-046 v3 SAN-E.MB-3.A: capa validacion granular pre-cierre proyecto
 * sobre lifecycle FSM existente. 4 categorias x 4 estados.
 */
import { api } from "@/lib/api";

export type ExitCategory =
  | "legal"
  | "tecnico"
  | "documentacion"
  | "operacional";

export type ExitStatus =
  | "pendiente"
  | "completado"
  | "bloqueado"
  | "no_aplica";

export interface ExitChecklistItem {
  id: string;
  item_code: string;
  label: string;
  category: ExitCategory;
  status: ExitStatus;
  evidence_id: string | null;
  completed_at: string | null;
  completed_by: string | null;
  note: string | null;
}

export interface ExitProgressByCategory {
  total: number;
  completed: number;
  blocked: number;
  not_applicable: number;
}

export interface ExitProgress {
  total: number;
  completed: number;
  applicable: number;
  not_applicable: number;
  completed_pct: number;
  by_category: Record<string, ExitProgressByCategory>;
}

export interface ExitChecklistResponse {
  project_id: string;
  items: ExitChecklistItem[];
  progress: ExitProgress;
}

export interface ExitItemMutationResponse {
  id: string;
  item_code: string;
  status: ExitStatus;
  completed_at: string | null;
}

export interface ExitReadiness {
  ready_to_close: boolean;
  total: number;
  completed: number;
  blockers: string[];
  warnings: string[];
}

const base = (projectId: string) =>
  `/api/v1/projects/${projectId}/exit-checklist`;

export function getExitChecklist(
  projectId: string,
): Promise<ExitChecklistResponse> {
  return api<ExitChecklistResponse>(base(projectId));
}

export function completeExitItem(
  projectId: string,
  itemId: string,
  body: { evidence_id?: string | null; note?: string | null } = {},
): Promise<ExitItemMutationResponse> {
  return api<ExitItemMutationResponse>(`${base(projectId)}/${itemId}/complete`, {
    method: "POST",
    json: body,
  });
}

export function uncompleteExitItem(
  projectId: string,
  itemId: string,
): Promise<ExitItemMutationResponse> {
  return api<ExitItemMutationResponse>(
    `${base(projectId)}/${itemId}/uncomplete`,
    { method: "POST", json: {} },
  );
}

export function setExitItemStatus(
  projectId: string,
  itemId: string,
  body: { status: ExitStatus; note?: string | null },
): Promise<ExitItemMutationResponse> {
  return api<ExitItemMutationResponse>(`${base(projectId)}/${itemId}/set-status`, {
    method: "POST",
    json: body,
  });
}

export function checkExitReadiness(
  projectId: string,
): Promise<ExitReadiness> {
  return api<ExitReadiness>(`${base(projectId)}/check-readiness`, {
    method: "POST",
    json: {},
  });
}
