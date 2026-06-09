/**
 * Audit Accompaniment API client · Sesión 3B-4 Ejecutable 7.5 Phase 7.5.2 (2026-05-27).
 *
 * 4 endpoints backend (BÁSICO 6 states · MEDIO_ALTO 11 states unified):
 *   POST /api/v1/admin/projects/{id}/accompaniment/advance     advance state machine
 *   POST /api/v1/admin/projects/{id}/accompaniment/artifacts   upload artifact (multipart)
 *   GET  /api/v1/admin/projects/{id}/accompaniment/timeline    admin full timeline
 *   GET  /api/v1/client-portal/accompaniment/timeline          cliente read-only timeline
 */
import { api } from "@/lib/api";

export interface AccompanimentTransitionEntry {
  from_state: string | null;
  to_state: string;
  advanced_by: string | null;
  advanced_at: string;
  transition_metadata: Record<string, unknown>;
}

export interface AccompanimentArtifactEntry {
  id: string;
  state: string;
  artifact_type: string;
  file_path: string;
  file_size_bytes: number;
  sha256: string;
  uploaded_by: string | null;
  uploaded_at: string;
}

export interface AccompanimentTimeline {
  project_id: string;
  category_branch: "BASICO" | "MEDIO_ALTO";
  current_state: string;
  last_advanced_at: string | null;
  is_terminal: boolean;
  transitions: AccompanimentTransitionEntry[];
  artifacts: AccompanimentArtifactEntry[];
}

export interface AccompanimentAdvanceResponse {
  project_id: string;
  from_state: string;
  to_state: string;
  category_branch: "BASICO" | "MEDIO_ALTO";
  is_terminal: boolean;
}

export interface AccompanimentArtifactUploadResponse {
  artifact_id: string;
  state: string;
  artifact_type: string;
  sha256: string;
  size_bytes: number;
}

export const auditAccompanimentApi = {
  getAdminTimeline: (projectId: string): Promise<AccompanimentTimeline> =>
    api<AccompanimentTimeline>(
      `/api/v1/admin/projects/${projectId}/accompaniment/timeline`,
    ),
  advanceState: (
    projectId: string,
    target_state: string,
    transition_metadata: Record<string, unknown> = {},
  ): Promise<AccompanimentAdvanceResponse> =>
    api<AccompanimentAdvanceResponse>(
      `/api/v1/admin/projects/${projectId}/accompaniment/advance`,
      { json: { target_state, transition_metadata } },
    ),
  uploadArtifact: (
    projectId: string,
    state: string,
    artifact_type: string,
    file: File,
  ): Promise<AccompanimentArtifactUploadResponse> => {
    const form = new FormData();
    form.append("state", state);
    form.append("artifact_type", artifact_type);
    form.append("file", file);
    // multipart: NO fijar Content-Type (fetch añade el boundary). El wrapper
    // `api` solo fija Content-Type cuando se usa `json`, así que body=FormData
    // con method POST deja que el navegador ponga el multipart correcto.
    return api<AccompanimentArtifactUploadResponse>(
      `/api/v1/admin/projects/${projectId}/accompaniment/artifacts`,
      { method: "POST", body: form },
    );
  },
};
