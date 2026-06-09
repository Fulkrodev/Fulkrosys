# Motor `m_meetings` · Reuniones Externas + Actas

Gestión de reuniones externas (Meet/Zoom/Teams cliente · NO videocall propio) + actas + acciones post-meeting + cross-motor M30 log_interaction. ADR-024 supersedes ADR-004 (videocall propio cancelado). SSE A18 stream para insight live (TODO-A18-LATENCY RESOLVED). PostMeetingActions: 4 acciones cross-motor (A19 propuesta + projects + M12 firma + email).

## Funcionalidades

- **CRUD reuniones** (`service.py`) create · list · get · update · soft delete + workflow (`complete_meeting` + `cancel_meeting`).
- **10 endpoints API** (`api.py`):
  - `POST /` create_meeting
  - `GET /` list_meetings (filters)
  - `GET /search` search FTS GIN español sobre `notes_markdown`
  - `GET /by-client/{client_id}` vista histórica + interlocutor JOIN
  - `GET /{meeting_id}` detail + interlocutor mini-card
  - `PATCH /{meeting_id}` update partial pre-completion
  - `POST /{meeting_id}/complete` notes + duration + auto-log M30
  - `POST /{meeting_id}/cancel` idempotente
  - `POST /{meeting_id}/sse-init` genera `sse_session_id`
  - `POST /{meeting_id}/post-action` 4 acciones cross-motor
  - `DELETE /{meeting_id}` soft delete (delegated cancel)
- **HTML render safe** (`_render_safe_html`) defensa profunda · render real client-side via `react-markdown` + `rehype-sanitize` (plan v4.2 6.31).
- **Actas service** (`actas_service.py` + `actas_portal_api.py`) actas formales reuniones + portal cliente view.
- **Actions cross-motor** (`actions.py`) 4 acciones post-meeting:
  - A19 RedactorPropuestasAgent para P-001
  - Projects update (state transitions)
  - M12 magic link `FIRMA_DOCUMENTO` para K.6 firma
  - EmailSender consolidado para resúmenes out-of-band
- **SSE A18 stream** para insight live durante reunión (sse_session_id generation).
- **Auto-log M30** `log_interaction(meeting_attended)` al `complete_meeting` si interlocutor presente.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.294 |
| Files | 7 |
| Status | production-grade · sub-bloque 7.A.4 FASE 7 |
| Tests | `backend/tests/motors/m_meetings/` |
| API prefix | `/api/v1/admin/meetings/*` (+ actas portal cliente sub-router) |
| RBAC | Admin-only `require_owner` router-level (M-Marcos pool) + cliente actas portal |

## Key files

- `api.py` · 10 endpoints admin meetings
- `actas_portal_api.py` · endpoints cliente portal actas
- `service.py` · core CRUD + workflow + cross-motor M30
- `actas_service.py` · actas formales logic
- `actions.py` · 4 post-meeting actions cross-motor
- `schemas.py` · Pydantic in/out

## DB tables

N/A motor-specific declarado · usa modelo compartido:

- `ExploratoryMeetingRow` (`backend/app/models/conformity_lifecycle.py:302`) · path mantenido por dominio compartido H5 audit pre-FASE 7

RLS por meetings tables.

## Cross-motor integration

- **Inbound**: ninguno directo
- **Outbound** (5 motores · HUB outbound):
  - M05 Signing (firma actas K.6)
  - M12 Magic Link (`FIRMA_DOCUMENTO` purpose)
  - M18 Communication (email signature + resúmenes)
  - M21 Portal Cliente (actas portal cliente view)
  - M30 Client Contacts (auto-log `meeting_attended` interaction)
- **LLM agents**: A18 SSE insight live + A19 RedactorPropuestasAgent (post-action P-001)

## Limitaciones conocidas

### NO videocall propio (ADR-024 supersedes ADR-004)

Decisión cement: NO LiveKit/Daily/Jitsi propio · cliente PYME usa Meet/Zoom/Teams habitualmente. Motor solo trackea metadata reunión (programación · participantes · notas) sin engine de video.

### HTML render solo client-side defense

`_render_safe_html` espejo M29 (defensa profunda sin nuevas deps). Render real markdown sucede **client-side** (`react-markdown` + `rehype-sanitize` plan v4.2 6.31). Server-side render NO disponible · trade-off cement (anti-XSS server overhead vs client trust).

## ADRs referenced

- ADR-004 · reuniones externas + panel A18 admin-only (**SUPERSEDED**)
- ADR-024 · supersedes ADR-004 (videocall propio cancelado)

## Cement OPS

Sub-bloque 7.A.4 FASE 7. Pattern coherente con M29 ClientMessagingService + M30 ClientContactService. ExploratoryMeetingRow path mantenido en `conformity_lifecycle.py` por dominio compartido H5 audit (cement architectural).
