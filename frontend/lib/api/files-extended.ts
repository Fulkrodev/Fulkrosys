/**
 * Files extended API · SAN-E v3.MB-6 atom 7.
 *
 * 7 decisiones Marcos (Q1-Q7):
 * - Q1 B · scope evidence + documents (workspace defer 7.bis)
 * - Q2 D · hybrid ILIKE search (filename + full_text_content + metadata)
 * - Q3 D · NO diff (version listing only)
 * - Q4 B · iframe browser native PDF preview
 * - Q5 A · scan_clean_only filter toggle
 * - Q6 B · current + collapsed history
 * - Q7 B · separated documents + evidence tabs
 */
import { clientApi } from "@/lib/client-portal-api";
import type { EvidenceScanStatus } from "@/components/ui/scan-status-badge";

export type FileSort = "recent" | "name" | "size";

export interface ClientDocumentExtended {
  id: string;
  codigo: string | null;
  version: string | null;
  created_at: string | null;
  estado: string | null;
  clasificacion: string | null;
  nombre: string | null;
  file_size_bytes: number | null;
  pdf_path: string | null;
  docx_path: string | null;
  storage_path: string | null;
  // 1.C.G.B v3.10 · folder context para arborescencia friendly cliente
  folder_id: string | null;
  folder_name: string | null;
  folder_path: string | null;
}

export interface ClientFolderNode {
  id: string;
  parent_folder_id: string | null;
  name: string;
  virtual_path: string;
  is_standard: boolean;
  standard_code: string | null;
  custom_order: number | null;
  children?: ClientFolderNode[];
}

export interface ClientEvidence {
  id: string;
  project_id: string;
  tipo: string | null;
  nombre_tipo: string | null;
  evidence_type_id: string | null;
  fichero_nombre_original: string | null;
  fichero_mime_type: string | null;
  fichero_tamano_bytes: number | null;
  measure_code: string | null;
  fecha_evidencia: string | null;
  fecha_caducidad: string | null;
  vigente: boolean | null;
  scan_status: EvidenceScanStatus;
  scan_completed_at: string | null;
  created_at: string | null;
}

export interface DocumentVersionEntry {
  id: string;
  version: string;
  hash_sha256: string | null;
  generado_por: string | null;
  generado_at: string | null;
  firmado_por: string | null;
  firmado_at: string | null;
}

export interface DocumentVersionsResponse {
  document_id: string;
  current_version: string | null;
  codigo: string | null;
  nombre: string | null;
  history: DocumentVersionEntry[];
}

interface ListDocumentsParams {
  q?: string;
  clasificacion?: string;
  folderId?: string;
  sort?: FileSort;
  limit?: number;
  offset?: number;
}

interface ListEvidenceParams {
  q?: string;
  scanCleanOnly?: boolean;
  sort?: FileSort;
  limit?: number;
  offset?: number;
}

function buildQs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== "" && v !== null,
  );
  if (entries.length === 0) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of entries) {
    sp.set(k, String(v));
  }
  return `?${sp.toString()}`;
}

export async function listDocumentsExtended(
  params: ListDocumentsParams = {},
): Promise<ClientDocumentExtended[]> {
  const qs = buildQs({
    q: params.q,
    clasificacion: params.clasificacion,
    folder_id: params.folderId,
    sort: params.sort,
    limit: params.limit,
    offset: params.offset,
  });
  return clientApi<ClientDocumentExtended[]>(`/client-portal/documents${qs}`);
}

/**
 * Folders tree para arborescencia cliente · 1.C.G.B v3.10.
 *
 * Backend retorna flat list ordered (is_standard DESC · custom_order · code · name).
 * Frontend reconstituye árbol via parent_folder_id.
 */
export async function getClientFoldersTree(): Promise<ClientFolderNode[]> {
  return clientApi<ClientFolderNode[]>(`/client-portal/folders/tree`);
}

export interface ClientUploadDocumentBody {
  nombre: string;
  contenido_base64: string;
  tipo_mime?: string;
  folder_id?: string;
  descripcion?: string;
}

export interface ClientUploadDocumentResult {
  id: string;
  nombre: string;
  folder_id: string | null;
  content_hash: string;
  file_size_bytes: number;
}

/**
 * Upload documento cliente · 1.C.G.B v3.10.
 *
 * Permission-limited vs admin IDMS intake:
 * - NO tags ENS · NO clasificacion explícita
 * - SÍ folder selector + descripción opcional
 * - Auth via cookie session (get_current_client_user backend)
 */
export async function uploadClientDocument(
  body: ClientUploadDocumentBody,
): Promise<ClientUploadDocumentResult> {
  return clientApi<ClientUploadDocumentResult>(
    `/client-portal/documents/upload`,
    { json: body },
  );
}

export async function listEvidenceExtended(
  params: ListEvidenceParams = {},
): Promise<ClientEvidence[]> {
  const qs = buildQs({
    q: params.q,
    scan_clean_only: params.scanCleanOnly,
    sort: params.sort,
    limit: params.limit,
    offset: params.offset,
  });
  return clientApi<ClientEvidence[]>(`/client-portal/evidence${qs}`);
}

export async function getDocumentVersions(
  documentId: string,
): Promise<DocumentVersionsResponse> {
  return clientApi<DocumentVersionsResponse>(
    `/client-portal/documents/${documentId}/versions`,
  );
}

/**
 * Returns the URL to use as iframe src for PDF preview (same-origin streaming).
 * Backend serves Content-Disposition: inline + X-Frame-Options: SAMEORIGIN.
 */
export function documentPreviewUrl(documentId: string): string {
  return `/api/v1/client-portal/documents/${documentId}/preview`;
}

export function evidencePreviewUrl(evidenceId: string): string {
  return `/api/v1/client-portal/evidence/${evidenceId}/preview`;
}

export function documentDownloadUrl(documentId: string): string {
  return `/api/v1/client-portal/documents/${documentId}/download`;
}

export function evidenceDownloadUrl(evidenceId: string): string {
  return `/api/v1/client-portal/evidence/${evidenceId}/download`;
}
