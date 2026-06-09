import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";
import type { Citation } from "@/lib/sprint4-types";

function csrfHeaders(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { [CSRF_HEADER]: token } : {};
}

export interface CopilotPageContext {
  url?: string;
  clientId?: string;
  projectPhase?: string;
  activeMotor?: string;
}

export interface CopilotChatRequest {
  question: string;
  projectId?: string;
  model?: string;
  maxTokens?: number;
  pageContext?: CopilotPageContext;
}

function serializePageContext(ctx?: CopilotPageContext) {
  if (!ctx) return undefined;
  return {
    url: ctx.url,
    client_id: ctx.clientId,
    project_phase: ctx.projectPhase,
    active_motor: ctx.activeMotor,
  };
}

export interface CopilotChatResponse {
  answer: string;
  citations: Citation[];
  notInCorpus: boolean;
  lowGroundingConfidence: boolean;
  modelUsed: string;
  tokensInput: number;
  tokensOutput: number;
  latencyMs: number;
}

interface BackendCopilotResponse {
  answer: string;
  citations_found: string[];
  chunk_ids_used: string[];
  not_in_corpus: boolean;
  low_grounding_confidence: boolean;
  model_used: string;
  tokens_input: number;
  tokens_output: number;
  latency_ms: number;
  interaction_log_id: number | null;
}

const CITATION_RE = /^([A-Z][A-Za-z0-9\- ]+?)\s*[-–]?\s*(.*)$/;

function toCitation(raw: string, idx: number, chunkId?: string): Citation {
  const match = CITATION_RE.exec(raw.trim());
  const framework = match?.[1]?.trim() || raw.trim() || "Fuente";
  const article = match?.[2]?.trim() || "";
  return {
    id: `cit-${Date.now()}-${idx}`,
    framework,
    article,
    excerpt: raw,
    chunk_id: chunkId,
  };
}

export async function chatWithCopilot(
  req: CopilotChatRequest,
  signal?: AbortSignal,
): Promise<CopilotChatResponse> {
  const body = {
    question: req.question,
    project_id: req.projectId,
    model: req.model,
    max_tokens: req.maxTokens,
    page_context: serializePageContext(req.pageContext),
  };
  const res = await fetch("/api/v1/copilot/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Copilot chat failed (${res.status}): ${detail}`);
  }
  const data: BackendCopilotResponse = await res.json();
  return {
    answer: data.answer,
    citations: data.citations_found.map((raw, i) =>
      toCitation(raw, i, data.chunk_ids_used[i]),
    ),
    notInCorpus: data.not_in_corpus,
    lowGroundingConfidence: data.low_grounding_confidence,
    modelUsed: data.model_used,
    tokensInput: data.tokens_input,
    tokensOutput: data.tokens_output,
    latencyMs: data.latency_ms,
  };
}

export async function* typewriter(
  text: string,
  tokenDelayMs = 14,
): AsyncGenerator<string, void, void> {
  const parts = text.split(/(\s+)/);
  for (const part of parts) {
    if (!part) continue;
    await new Promise((r) => setTimeout(r, tokenDelayMs));
    yield part;
  }
}

export interface CopilotChunkPreview {
  chunk_id: string;
  source: string;
  preview: string;
  score: number;
}

export interface CopilotCitationEvent {
  raw: string;
  norm: string;
  measure: string | null;
  chunk_id: string | null;
  preview: string | null;
}

export interface CopilotDoneEvent {
  answer: string;
  citations_found: string[];
  chunk_ids_used: string[];
  chunks_used: CopilotChunkPreview[];
  not_in_corpus: boolean;
  low_grounding_confidence: boolean;
  confidence: number;
  corpus_gap: boolean;
  model_used: string;
  interaction_log_id: number | null;
}

export type CopilotStreamEvent =
  | {
      type: "start";
      chunks_used: number;
      chunk_ids: string[];
      measure_codes: string[];
      confidence: number;
      corpus_gap: boolean;
    }
  | { type: "delta"; text: string }
  | { type: "citation"; data: CopilotCitationEvent }
  | { type: "done"; data: CopilotDoneEvent }
  | { type: "error"; error: string };

export async function* chatWithCopilotStream(
  req: CopilotChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<CopilotStreamEvent, void, void> {
  const body = {
    question: req.question,
    project_id: req.projectId,
    model: req.model,
    max_tokens: req.maxTokens,
    page_context: serializePageContext(req.pageContext),
  };
  const res = await fetch("/api/v1/copilot/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Copilot stream failed (${res.status}): ${detail}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sepIdx = buffer.indexOf("\n\n");
      while (sepIdx !== -1) {
        const frame = buffer.slice(0, sepIdx);
        buffer = buffer.slice(sepIdx + 2);
        sepIdx = buffer.indexOf("\n\n");

        for (const line of frame.split("\n")) {
          const trimmed = line.trimStart();
          if (!trimmed.startsWith("data:")) continue;
          const payload = trimmed.slice("data:".length).trim();
          if (!payload) continue;
          try {
            yield JSON.parse(payload) as CopilotStreamEvent;
          } catch {
            // ignore malformed frame
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function rawCitationsToCitations(
  raws: string[],
  chunkIds: string[] = [],
): Citation[] {
  return raws.map((raw, i) => toCitation(raw, i, chunkIds[i]));
}
