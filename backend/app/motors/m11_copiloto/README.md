# Motor 11 · Copiloto ENS (Agent 14 wrapper)

Wrapper HTTP del Agent 14 Copiloto (LLM ENS specialist) exponiendo 3 surfaces architectural intent distintos para admin owner y cliente client_user. Persistencia de conversaciones + contexto por proyecto. Cement architectural ADR-049 (3 surfaces NO duplicate).

## Funcionalidades

- **Quick chat sin persistencia** (`/copilot/chat` compat endpoint legacy).
- **CRUD conversaciones persistentes** per `project_id` · `CopilotConversation` + `CopilotMessage` ORM.
- **Chat dentro de conversación** con historial cargado + streaming SSE response.
- **Contexto del proyecto** (`PageContext` injection) basado en página actual + `DdaEntry` + `Finding` + `Evidence` + `AuditSimulationRun` data.
- **Stream answer** (SSE) para respuestas en tiempo real.
- **3 surfaces architectural** (ADR-049 cement):
  - Admin Sheet side panel · `/copilot/*` admin-routed
  - Admin fullscreen page · `app/(admin)/admin/copilot/page.tsx`
  - Cliente floating dock · `portal_api.py` cliente-routed
- **Inline agents API** (`inline_agents_api.py`) endpoints in-page agent calls (sin chat overhead).
- **Portal API cliente** (`portal_api.py`) endpoints cliente client_user (CopilotoDock floating cliente Spanish convention).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 983 (motor más pequeño numerated) |
| Files | 4 |
| Status | production-grade (Sprint C3 expansion 1→8 endpoints) |
| Tests | `backend/tests/motors/m11_copiloto/` |
| API prefix | `/api/v1/copilot/*` (admin) + portal-api cliente |
| RBAC | Mixed · admin via `/copilot` + cliente via `portal_api` |

## Key files

- `api.py` · 8 endpoints admin (chat + CRUD conversaciones + stream)
- `inline_agents_api.py` · endpoints in-page inline agents (sin chat overhead)
- `portal_api.py` · endpoints cliente client_user (CopilotoDock)

⚠️ NO existe `service.py` · wrapper directo de `backend.app.agents.agent_14_copiloto.service` (delegación pura).

## DB tables

N/A motor-specific · usa modelos:
- `CopilotConversation` (`backend/app/models/copilot.py`)
- `CopilotMessage` (`backend/app/models/copilot.py`)

RLS por `copilot_conversations` + `copilot_messages`.

## Cross-motor integration

- **Inbound**: ninguno directo (motor entrada UI · LLM-facing)
- **Outbound**: M08 Verification (queries técnicas) + M21 Portal Cliente (auth ClientUser)
- **LLM agents**: Agent 14 Copiloto (wrapped) · agente especializado ENS con anti-hallucination boundary cement

## Limitaciones conocidas

### NO service.py propio · wrapper de Agent 14

Motor es delgado wrapper HTTP de `agent_14_copiloto.service` · toda lógica LLM + anti-hallucination boundary vive en agent layer. Decisión arquitectónica: separar transport (motor) de cognición (agent).

## ADRs referenced

- ADR-049 · 3 surfaces architectural intent · NO duplicate (admin Sheet + admin fullscreen + cliente Dock) — cemented FASE 2 H2
- ADR-050 · Copilot ADMIN guided mode end-to-end ENS lifecycle · VISIÓN cement · DEFER MB-14 polish bloque mayor

## Cement OPS

Wrapper pattern delgado · scope split agent (cognición) + motor (transport). Sprint C3 expandió 1→8 endpoints. ADR-049 cement: copilot/copiloto NO duplicate · convención inglés admin (matches `/admin/copilot` route) + español cliente (matches backend `m11_copiloto` + `agents/agent_14_copiloto`).
