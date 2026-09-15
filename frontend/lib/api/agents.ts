/**
 * Cliente de invocación genérica de agentes IA (admin).
 *
 * S15 fix campaña auditoría: el LeadDrawer del pipeline comercial simulaba la
 * invocación de A17/A2/A19 con setTimeout+toast. Este wrapper llama al endpoint
 * real POST /api/v1/agents/{id}/invoke (body genérico).
 */
import { api } from "@/lib/api";

export interface AgentInvokeBody {
  message: string;
  project_id?: string;
  params?: Record<string, unknown>;
  structured_output?: boolean;
  extra_context?: string;
}

/**
 * De donde salio el texto del agente. Sin ANTHROPIC_API_KEY la plataforma NO
 * falla: devuelve una plantilla estatica con 200, y antes de esto la interfaz
 * no tenia forma de distinguirla de una redaccion del modelo.
 */
export type GeneradoPor =
  | "modelo"
  | "plantilla_por_fallo_de_esquema"
  | "sin_clave_de_api";

export type AgentInvokeResult = Record<string, unknown> & {
  generado_por?: GeneradoPor;
};

/** El texto lo escribio el modelo. Sin la marca se asume que NO: cae del lado
 *  seguro, que es el que no presenta una plantilla como si fuera una respuesta. */
export function vinoDelModelo(r: AgentInvokeResult | undefined): boolean {
  return r?.generado_por === "modelo";
}

/** Por que no vino del modelo, en una frase para el usuario. */
export function porQueNoVinoDelModelo(r: AgentInvokeResult | undefined): string {
  return r?.generado_por === "sin_clave_de_api"
    ? "no hay clave de API configurada, así que no se ha llamado a ningún modelo"
    : "el modelo respondió pero su salida no era válida, y se ha servido una plantilla";
}

export function invokeAgent(
  agentId: number,
  body: AgentInvokeBody,
): Promise<AgentInvokeResult> {
  return api<AgentInvokeResult>(`/agents/${agentId}/invoke`, {
    method: "POST",
    json: body,
  });
}
