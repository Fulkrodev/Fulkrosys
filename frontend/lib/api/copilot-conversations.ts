/**
 * Copilot conversations API client · Sesión 3B-2B.4 Phase 2.4.
 *
 * Wraps M11 CopilotConversation CRUD endpoints:
 *   POST   /api/v1/projects/{project_id}/copilot/conversations
 *   GET    /api/v1/projects/{project_id}/copilot/conversations
 *   GET    /api/v1/projects/{project_id}/copilot/conversations/{conversation_id}
 *   DELETE /api/v1/projects/{project_id}/copilot/conversations/{conversation_id}
 *   POST   /api/v1/projects/{project_id}/copilot/conversations/{conversation_id}/chat
 *   GET    /api/v1/clients/{client_id}/copilot/conversations  (Phase 2.2 NEW · per-cliente)
 *
 * Backend devuelve client_id en cada conversation (Phase 2.2 serializer enrich).
 * RLS isolated post-Phase 2.3 OPTION 1 fix (audit Phase 1.5 finding A) ·
 * cross-cliente queries safe vía endpoint /clients/{id}/...
 */
import { api } from "@/lib/api";

/**
 * Proyecto seleccionable en la memoria del copiloto admin (#23 Ola 5).
 * Trae el project_id REAL (NO client_id) que necesitan los endpoints de
 * conversación (keyed por project_id · get_project_owner).
 */
export interface CopilotMemoryProject {
  project_id: string;
  nombre: string;
  categoria_objetivo: string | null;
  fase: string | null;
  cliente_nombre: string | null;
}

/** Lista proyectos activos para el selector de memoria (admin · #23). */
export async function listMemoryProjects(): Promise<CopilotMemoryProject[]> {
  const res = await api<{ projects: CopilotMemoryProject[] }>(
    "/api/v1/copilot/projects",
  );
  return res.projects;
}

export interface CopilotConversation {
  id: string;
  project_id: string | null;
  /** Sesión 3B-2B.4 Phase 2.2 · habilita cross-project per cliente memoria. */
  client_id: string | null;
  titulo: string | null;
  modelo_default: string | null;
  autor: string | null;
  created_at: string | null;
}

export interface CopilotConversationDetail extends CopilotConversation {
  messages: CopilotConversationMessage[];
}

export interface CopilotConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: unknown | null;
  chunk_ids_used: unknown | null;
  model_used: string | null;
  tokens_input: number | null;
  tokens_output: number | null;
  created_at: string | null;
}

export interface CreateConversationBody {
  titulo: string;
  modelo_default?: string | null;
  autor?: string;
}

export interface ConversationChatBody {
  content: string;
  model?: string | null;
  max_tokens?: number | null;
  include_project_context?: boolean;
}

/** List conversations within a project (sorted desc created_at). */
export async function listProjectConversations(
  projectId: string,
): Promise<{ conversations: CopilotConversation[] }> {
  return api<{ conversations: CopilotConversation[] }>(
    `/api/v1/projects/${projectId}/copilot/conversations`,
  );
}

/**
 * List conversations cross-project per cliente · memoria super-vision.
 *
 * Sesión 3B-2B.4 Phase 2.2 endpoint · Phase 2.3 RLS-isolated (audit Phase 1.5
 * finding A fix). Defence-in-depth: backend filtra WHERE client_id + RLS policy
 * `copilot_isolation` OR clause `client_id = current_client_id()`.
 *
 * Limit clamped backend [1, 200] default 50.
 */
export async function listClientConversations(
  clientId: string,
  options: { limit?: number } = {},
): Promise<{ conversations: CopilotConversation[] }> {
  const params = new URLSearchParams();
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  const qs = params.toString();
  return api<{ conversations: CopilotConversation[] }>(
    `/api/v1/clients/${clientId}/copilot/conversations${qs ? `?${qs}` : ""}`,
  );
}

export async function getConversation(
  projectId: string,
  conversationId: string,
): Promise<CopilotConversationDetail> {
  return api<CopilotConversationDetail>(
    `/api/v1/projects/${projectId}/copilot/conversations/${conversationId}`,
  );
}

export async function createConversation(
  projectId: string,
  body: CreateConversationBody,
): Promise<CopilotConversation> {
  return api<CopilotConversation>(
    `/api/v1/projects/${projectId}/copilot/conversations`,
    { method: "POST", json: body },
  );
}

export async function deleteConversation(
  projectId: string,
  conversationId: string,
): Promise<{ ok: boolean }> {
  return api<{ ok: boolean }>(
    `/api/v1/projects/${projectId}/copilot/conversations/${conversationId}`,
    { method: "DELETE" },
  );
}

/** Respuesta del chat persistente · backend devuelve user+assistant ya guardados. */
export interface ConversationChatResult {
  user_message: CopilotConversationMessage;
  assistant_message: CopilotConversationMessage;
  answer: string;
  citations_found: string[];
  not_in_corpus: boolean;
}

export async function sendConversationChat(
  projectId: string,
  conversationId: string,
  body: ConversationChatBody,
): Promise<ConversationChatResult> {
  return api<ConversationChatResult>(
    `/api/v1/projects/${projectId}/copilot/conversations/${conversationId}/chat`,
    { method: "POST", json: body },
  );
}
