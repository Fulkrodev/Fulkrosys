/**
 * API client · Motor 24 IDMS (m_dms identity · 1.C.G v3.10).
 *
 * 27 endpoints existing en m24_idms · prefix `/api/v1/idms` · paths repiten /idms/:
 *   GET    /api/v1/idms/standard-folders
 *   POST   /api/v1/idms/projects/{id}/idms/folders/initialize
 *   POST   /api/v1/idms/projects/{id}/idms/folders
 *   GET    /api/v1/idms/projects/{id}/idms/folders/tree
 *   POST   /api/v1/idms/projects/{id}/idms/intake
 *   GET    /api/v1/idms/projects/{id}/idms/search
 *   GET    /api/v1/idms/projects/{id}/idms/documents
 *   GET    /api/v1/idms/projects/{id}/idms/documents/{doc_id}
 *   POST   /api/v1/idms/projects/{id}/idms/documents/{doc_id}/versions
 *   GET    /api/v1/idms/projects/{id}/idms/documents/{doc_id}/versions
 *   POST   /api/v1/idms/projects/{id}/idms/documents/{doc_id}/tags
 *   GET    /api/v1/idms/projects/{id}/idms/documents/{doc_id}/tags
 *   GET    /api/v1/idms/projects/{id}/idms/stats
 *   GET    /api/v1/idms/projects/{id}/idms/documents/expiring
 */
import { api } from "@/lib/api";

const BASE = "/api/v1/idms";

export interface IdmsFolderNode {
  id: string;
  project_id: string | null;
  parent_folder_id: string | null;
  name: string;
  virtual_path: string;
  is_standard: boolean;
  standard_code: string | null;
  custom_order: number | null;
  children?: IdmsFolderNode[];
}

export interface IdmsDocument {
  id: string;
  project_id: string;
  nombre: string;
  tipo: string | null;
  template_codigo: string | null;
  folder_id: string | null;
  content_hash: string | null;
  file_size_bytes: number | null;
  storage_path: string | null;
  estado?: string | null;
  clasificacion?: string | null;
  version?: string | null;
  version_actual?: string | null;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  expires_at?: string | null;
  review_period_months?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface IdmsTag {
  id: string;
  document_id: string;
  tag_type: string;
  tag_value: string;
  confidence: number;
  source: string;
  created_at: string | null;
}

export interface IdmsVersion {
  id: string;
  document_id: string;
  version: string;
  hash_sha256: string | null;
  contenido_path: string | null;
  generado_por: string | null;
  generado_at: string | null;
}

export interface IdmsDocumentDetail extends IdmsDocument {
  tags?: IdmsTag[];
  versions?: IdmsVersion[];
  folder?: IdmsFolderNode | null;
}

export interface IdmsStats {
  total_documents?: number;
  by_estado?: Record<string, number>;
  by_clasificacion?: Record<string, number>;
  total_folders?: number;
  total_size_bytes?: number;
  [key: string]: unknown;
}

export interface IdmsIntakeTag {
  type: string;
  value: string;
  source?: string;
  confidence?: number;
}

export interface IdmsIntakeBody {
  nombre: string;
  contenido_base64: string;
  tipo_mime?: string;
  folder_id?: string;
  clasificacion?: string;
  tags?: IdmsIntakeTag[];
  subido_por?: string;
  full_text_content?: string;
}

export interface IdmsIntakeResult {
  document: IdmsDocument;
  duplicate: boolean;
  content_hash: string;
  tags: IdmsTag[];
}

export interface IdmsCreateFolderBody {
  name: string;
  parent_folder_id?: string;
  virtual_path?: string;
}

export interface IdmsCreateVersionBody {
  contenido_base64: string;
  descripcion_cambio?: string;
  subido_por?: string;
}

export const idmsApi = {
  // Catalog
  standardFolders: () =>
    api<{ folders: Array<{ code: string; name: string; path: string }>; count: number }>(
      `${BASE}/standard-folders`,
    ),

  // Stats
  stats: (projectId: string) =>
    api<IdmsStats>(`${BASE}/projects/${projectId}/idms/stats`),

  // Folders
  initializeFolders: (projectId: string) =>
    api<{ folders: IdmsFolderNode[]; count: number }>(
      `${BASE}/projects/${projectId}/idms/folders/initialize`,
      { method: "POST" },
    ),

  createFolder: (projectId: string, body: IdmsCreateFolderBody) =>
    api<IdmsFolderNode>(
      `${BASE}/projects/${projectId}/idms/folders`,
      { json: body },
    ),

  folderTree: (projectId: string) =>
    api<IdmsFolderNode[] | { tree?: IdmsFolderNode[] }>(
      `${BASE}/projects/${projectId}/idms/folders/tree`,
    ),

  // Documents
  listDocuments: (
    projectId: string,
    opts: { folderId?: string; clasificacion?: string } = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.folderId) sp.set("folder_id", opts.folderId);
    if (opts.clasificacion) sp.set("clasificacion", opts.clasificacion);
    const qs = sp.toString();
    return api<{ documents: IdmsDocument[] }>(
      `${BASE}/projects/${projectId}/idms/documents${qs ? `?${qs}` : ""}`,
    );
  },

  getDocument: (projectId: string, documentId: string) =>
    api<IdmsDocumentDetail>(
      `${BASE}/projects/${projectId}/idms/documents/${documentId}`,
    ),

  /**
   * #32 (FRENTE B) · descarga del binario IDMS desde el gestor admin.
   * Endpoint streaming (no JSON) → fetch del blob con cookie de sesión +
   * guardado con el nombre del documento. Resuelve storage_path minio://
   * (durable) con fallback local en backend.
   */
  downloadDocument: async (
    projectId: string,
    documentId: string,
    filename?: string,
  ): Promise<void> => {
    const res = await fetch(
      `${BASE}/projects/${projectId}/idms/documents/${documentId}/download`,
      { credentials: "include" },
    );
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `documento_${documentId}`;
    a.click();
    URL.revokeObjectURL(url);
  },

  intake: (projectId: string, body: IdmsIntakeBody) =>
    api<IdmsIntakeResult>(
      `${BASE}/projects/${projectId}/idms/intake`,
      { json: body },
    ),

  // Versions
  listVersions: (projectId: string, documentId: string) =>
    api<{ versions: IdmsVersion[] }>(
      `${BASE}/projects/${projectId}/idms/documents/${documentId}/versions`,
    ),

  createVersion: (
    projectId: string,
    documentId: string,
    body: IdmsCreateVersionBody,
  ) =>
    api<{ document: IdmsDocument; version: IdmsVersion }>(
      `${BASE}/projects/${projectId}/idms/documents/${documentId}/versions`,
      { json: body },
    ),

  // Search
  search: (
    projectId: string,
    opts: {
      query?: string;
      folderId?: string;
      clasificacion?: string;
      tagType?: string;
      tagValue?: string;
      limit?: number;
    } = {},
  ) => {
    const sp = new URLSearchParams();
    if (opts.query) sp.set("query", opts.query);
    if (opts.folderId) sp.set("folder_id", opts.folderId);
    if (opts.clasificacion) sp.set("clasificacion", opts.clasificacion);
    if (opts.tagType) sp.set("tag_type", opts.tagType);
    if (opts.tagValue) sp.set("tag_value", opts.tagValue);
    if (opts.limit) sp.set("limit", String(opts.limit));
    const qs = sp.toString();
    return api<{ documents: IdmsDocument[] }>(
      `${BASE}/projects/${projectId}/idms/search${qs ? `?${qs}` : ""}`,
    );
  },

  // Tags
  addTag: (
    projectId: string,
    documentId: string,
    body: {
      tag_type: string;
      tag_value: string;
      source?: string;
      confidence?: number;
    },
  ) =>
    api<IdmsTag>(
      `${BASE}/projects/${projectId}/idms/documents/${documentId}/tags`,
      { json: body },
    ),

  // Expiring (already existed)
  expiring: (projectId: string) =>
    api<{ documents: IdmsDocument[] } | IdmsDocument[]>(
      `${BASE}/projects/${projectId}/idms/documents/expiring`,
    ),
};
