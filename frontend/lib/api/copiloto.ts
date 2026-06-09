/**
 * Copiloto cliente API client · MB-7 atom 7.2.
 *
 * Hits /api/v1/client-portal/copiloto/* endpoints (NO Marcos-only m11).
 * SSE streaming via fetch + ReadableStream reader.
 */
import { api } from "@/lib/api";
import { clientApi } from "@/lib/client-portal-api";

export interface CopilotMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface QuickAction {
  id: string;
  label: string;
  prefill_query: string;
}

export interface PageContext {
  url?: string | null;
  project_phase?: string | null;
  active_motor?: string | null;
}

export interface CopilotChatBody {
  question: string;
  page_context?: PageContext;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export async function fetchQuickActions(
  context: string,
): Promise<QuickAction[]> {
  const qs = new URLSearchParams({ context });
  return clientApi<QuickAction[]>(
    `/client-portal/copiloto/quick-actions?${qs.toString()}`,
  );
}

// Sesión 3B-2B.8 Phase 1D · workflow-aware proactive hint cliente.
export interface CopilotHint {
  has_action: boolean;
  message: string;
  priority: "urgent" | "normal" | "low";
  target_url: string | null;
  motor: string | null;
  action: string | null;
  current_phase: string;
}

export async function fetchCopilotHintCliente(): Promise<CopilotHint> {
  return clientApi<CopilotHint>("/client-portal/copiloto/hint");
}

// FASE 2 gobierno · hint admin (Marcos) workflow-aware + blockers cross-actor.
export interface CopilotBlocker {
  motor: string;
  description: string;
  waiting_on: "admin" | "cliente" | "external_auditor" | "system";
}

export interface CopilotHintAdmin extends CopilotHint {
  blockers: CopilotBlocker[];
  // #22 Ola 5 · medidas aplicables sin evidencia válida (cruce semáforo #20).
  // Códigos ENS (R30 admin · NO cliente). Opcional · backend antiguo no lo trae.
  evidence_gaps?: string[];
}

export async function fetchCopilotHintAdmin(
  projectId: string,
): Promise<CopilotHintAdmin> {
  const qs = new URLSearchParams({ project_id: projectId });
  return api<CopilotHintAdmin>(`/api/v1/copilot/hint?${qs.toString()}`);
}

// #22 Ola 5 · push proactivo admin in-app · avisos recientes para el briefing.
export interface AdminNudge {
  id: string;
  project_id: string | null;
  project_nombre: string | null;
  title: string | null;
  message: string | null;
  motor: string | null;
  phase: string | null;
  created_at: string | null;
}

export async function fetchAdminNudges(limit = 10): Promise<AdminNudge[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  const res = await api<{ nudges: AdminNudge[] }>(
    `/api/v1/copilot/admin-nudges?${qs.toString()}`,
  );
  return res.nudges;
}

/**
 * Stream the answer to a question via SSE.
 *
 * Calls onDelta(text) for each new fragment of the assistant response.
 * Resolves when the stream closes; rejects on network or HTTP error.
 */
export async function streamCopilotAnswer(
  body: CopilotChatBody,
  onDelta: (delta: string) => void,
): Promise<void> {
  const url = `${API_BASE}/api/v1/client-portal/copiloto/chat/stream`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Copilot stream failed: ${resp.status}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames separated by "\n\n"
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!frame.startsWith("data:")) continue;
      const payload = frame.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        const json = JSON.parse(payload);
        if (json.type === "delta" && typeof json.text === "string") {
          onDelta(json.text);
        } else if (json.type === "error") {
          throw new Error(json.error || "Copilot stream error");
        }
      } catch (parseErr) {
        // Frame did not parse — if it's not JSON treat as raw text
        if (parseErr instanceof SyntaxError) {
          onDelta(payload);
        } else {
          throw parseErr;
        }
      }
    }
  }
}
