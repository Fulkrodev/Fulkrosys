"use client";

/**
 * Admin Workspace API client (SAN-E v3.MB-4.2).
 *
 * Wraps Motor 20 endpoints (22 totales · 17 únicos · 3 sub-features
 * Files/Chat/Feed · videocalls diferido).
 *
 * Backend dict shapes deriva de:
 *   backend/app/motors/m20_workspace/api.py (_serialize_file ·
 *     _serialize_message · _serialize_feed_item · _serialize_workspace)
 *   backend/app/models/collaboration.py
 */

import { api } from "@/lib/api";

// =====================================================================
// Workspace lifecycle
// =====================================================================

export interface WorkspaceMeta {
  id: string;
  project_id: string;
  nombre: string | null;
  estado: "active" | "archived" | "destroyed" | string;
  config: Record<string, unknown> | null;
  carpeta_docs_path: string | null;
  caducidad_at: string | null;
  livekit_room_id: string | null;
  created_at: string | null;
}

export interface CreateWorkspaceBody {
  nombre?: string;
  config?: Record<string, unknown>;
}

export interface ArchiveBody {
  retention_days?: number;
}

// =====================================================================
// Files
// =====================================================================

export interface WorkspaceFile {
  id: string;
  workspace_id: string;
  project_id: string | null;
  nombre: string;
  carpeta: string | null;
  tipo_mime: string | null;
  tamano_bytes: number | null;
  hash_sha256: string | null;
  storage_path: string | null;
  version: number | null;
  subido_por: string | null;
  subido_at: string | null;
  estado: "active" | "archived" | "deleted" | string;
}

export interface UploadFileBody {
  nombre: string;
  carpeta?: string;
  contenido_base64: string;
  tipo_mime?: string;
  subido_por?: string;
}

export interface FilesTreeNode {
  carpeta: string;
  files_count: number;
  children?: FilesTreeNode[];
}

// =====================================================================
// Chat
// =====================================================================

export type ChatAutorTipo = "marcos" | "cliente" | "sistema";

export interface ChatMessage {
  id: string;
  workspace_id: string;
  autor: string;
  autor_tipo: ChatAutorTipo | string;
  mensaje: string;
  adjunto_file_id: string | null;
  respondiendo_a: string | null;
  created_at: string | null;
}

export interface SendMessageBody {
  autor: string;
  autor_tipo?: ChatAutorTipo;
  mensaje: string;
  adjunto_file_id?: string;
  respondiendo_a?: string;
}

// =====================================================================
// Feed
// =====================================================================

export type FeedItemTipo =
  | "hito_completado"
  | "documento_generado"
  | "evidencia_aportada"
  | "finding_detectado"
  | "tarea_completada"
  | "firma_pendiente"
  | "comentario"
  | "alerta"
  | "reunion_programada";

export type FeedItemAutor = "marcos" | "plataforma" | "cliente" | string;

export interface FeedItem {
  id: string;
  workspace_id: string;
  project_id: string;
  tipo: FeedItemTipo | string;
  titulo: string;
  descripcion: string | null;
  metadata: Record<string, unknown> | null;
  autor: FeedItemAutor;
  leido: boolean;
  leido_at: string | null;
  created_at: string | null;
}

export interface AddFeedItemBody {
  tipo: string;
  titulo: string;
  descripcion?: string;
  autor?: string;
  metadata?: Record<string, unknown>;
}

// =====================================================================
// Summary
// =====================================================================

export interface WorkspaceSummary {
  workspace_id: string;
  files_count: number;
  messages_count: number;
  feed_items_count: number;
  feed_unread: number;
  last_activity_at: string | null;
}

// =====================================================================
// API functions
// =====================================================================

const BASE = "/api/v1/projects";

// -------- Workspace lifecycle --------

export async function getWorkspace(projectId: string): Promise<WorkspaceMeta | null> {
  return api<WorkspaceMeta | null>(`${BASE}/${projectId}/workspace`);
}

export async function createWorkspace(
  projectId: string,
  body: CreateWorkspaceBody = {},
): Promise<WorkspaceMeta> {
  return api<WorkspaceMeta>(`${BASE}/${projectId}/workspace`, {
    method: "POST",
    json: body,
  });
}

export async function archiveWorkspace(
  projectId: string,
  body: ArchiveBody = {},
): Promise<WorkspaceMeta> {
  return api<WorkspaceMeta>(`${BASE}/${projectId}/workspace/archive`, {
    method: "POST",
    json: body,
  });
}

export async function getWorkspaceSummary(
  projectId: string,
): Promise<WorkspaceSummary> {
  return api<WorkspaceSummary>(`${BASE}/${projectId}/workspace/summary`);
}

// -------- Files --------

export async function listWorkspaceFiles(
  projectId: string,
  opts?: { carpeta?: string; estado?: string },
): Promise<WorkspaceFile[]> {
  const qs = new URLSearchParams();
  if (opts?.carpeta) qs.set("carpeta", opts.carpeta);
  if (opts?.estado) qs.set("estado", opts.estado);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await api<{ files: WorkspaceFile[] }>(
    `${BASE}/${projectId}/workspace/files${suffix}`,
  );
  return res.files;
}

export async function getFilesTree(
  projectId: string,
): Promise<FilesTreeNode | Record<string, unknown>> {
  return api<FilesTreeNode | Record<string, unknown>>(
    `${BASE}/${projectId}/workspace/files/tree`,
  );
}

export async function getWorkspaceFile(
  projectId: string,
  fileId: string,
): Promise<WorkspaceFile> {
  return api<WorkspaceFile>(`${BASE}/${projectId}/workspace/files/${fileId}`);
}

export async function uploadWorkspaceFile(
  projectId: string,
  body: UploadFileBody,
): Promise<WorkspaceFile> {
  return api<WorkspaceFile>(`${BASE}/${projectId}/workspace/files`, {
    method: "POST",
    json: body,
  });
}

export async function deleteWorkspaceFile(
  projectId: string,
  fileId: string,
): Promise<WorkspaceFile> {
  return api<WorkspaceFile>(`${BASE}/${projectId}/workspace/files/${fileId}`, {
    method: "DELETE",
  });
}

/**
 * S28b · descarga el binario del fichero (Blob) desde MinIO. Devuelve Blob (no
 * JSON) → fetch directo con credentials, igual que generateDeclarationDocx.
 */
export async function downloadWorkspaceFile(
  projectId: string,
  fileId: string,
): Promise<Blob> {
  const response = await fetch(
    `${BASE}/${projectId}/workspace/files/${fileId}/download`,
    { method: "GET", credentials: "include" },
  );
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      // not JSON · use statusText
    }
    throw new Error(detail);
  }
  return response.blob();
}

/**
 * Convierte un File del navegador a base64 string sin prefix data:.
 * Usado por uploadWorkspaceFile (backend espera contenido_base64).
 */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Lectura de archivo no es string"));
        return;
      }
      const idx = result.indexOf(",");
      resolve(idx >= 0 ? result.slice(idx + 1) : result);
    };
    reader.onerror = () => reject(reader.error ?? new Error("Error leyendo archivo"));
    reader.readAsDataURL(file);
  });
}

// -------- Chat --------

export async function listChatMessages(
  projectId: string,
  opts?: { limit?: number; before?: string },
): Promise<ChatMessage[]> {
  const qs = new URLSearchParams();
  if (opts?.limit) qs.set("limit", String(opts.limit));
  if (opts?.before) qs.set("before", opts.before);
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await api<{ messages: ChatMessage[] }>(
    `${BASE}/${projectId}/workspace/chat${suffix}`,
  );
  return res.messages;
}

export async function sendChatMessage(
  projectId: string,
  body: SendMessageBody,
): Promise<ChatMessage> {
  return api<ChatMessage>(`${BASE}/${projectId}/workspace/chat`, {
    method: "POST",
    json: body,
  });
}

export async function getChatThread(
  projectId: string,
  messageId: string,
): Promise<ChatMessage[]> {
  const res = await api<{ thread: ChatMessage[] }>(
    `${BASE}/${projectId}/workspace/chat/${messageId}/thread`,
  );
  return res.thread;
}

// -------- Feed --------

export async function listFeedItems(
  projectId: string,
  opts?: { tipo?: string; limit?: number; offset?: number },
): Promise<FeedItem[]> {
  const qs = new URLSearchParams();
  if (opts?.tipo) qs.set("tipo", opts.tipo);
  if (opts?.limit !== undefined) qs.set("limit", String(opts.limit));
  if (opts?.offset !== undefined) qs.set("offset", String(opts.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  const res = await api<{ items: FeedItem[] }>(
    `${BASE}/${projectId}/workspace/feed${suffix}`,
  );
  return res.items;
}

export async function addFeedItem(
  projectId: string,
  body: AddFeedItemBody,
): Promise<FeedItem> {
  return api<FeedItem>(`${BASE}/${projectId}/workspace/feed`, {
    method: "POST",
    json: body,
  });
}

export async function markFeedRead(
  projectId: string,
  itemId: string,
): Promise<FeedItem> {
  return api<FeedItem>(`${BASE}/${projectId}/workspace/feed/${itemId}/read`, {
    method: "PATCH",
  });
}

export async function getFeedUnreadCount(
  projectId: string,
): Promise<{ unread_count: number }> {
  return api<{ unread_count: number }>(
    `${BASE}/${projectId}/workspace/feed/unread-count`,
  );
}
