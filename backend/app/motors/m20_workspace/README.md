# Motor 20 · Collaborative Workspace (FULKRO Room)

Workspace colaborativo 1:1 por proyecto cliente · "FULKRO Room" · ficheros + feed + chat + videocalls. Append-only en chat y feed (auditoría inmutable). Files con SHA-256 obligatorio. Videocall state machine (sin LiveKit real · future). Cliente + Marcos comparten espacio único por proyecto.

## Funcionalidades

- **Files workspace** upload con SHA-256 hash obligatorio inmutable.
- **Feed append-only** posts del proyecto (Marcos + cliente) sin edición posterior (audit trail).
- **Chat append-only** mensajes bidireccionales cliente↔Marcos (similar feed pero conversacional).
- **Videocalls state machine** (estado meeting + participants) · LiveKit/Daily/Jitsi NO integrados (decisión ADR-004 sobre-ingeniería preventiva).
- **WorkspaceService** core (`workspace_service.py`) con `WorkspaceError`.
- **1:1 per project** un único workspace por `project_id` (no múltiples rooms · simplicidad cliente PYME).
- **Acceso compartido** Marcos + cliente client_user pueden ambos crear contenido (`require_marcos_or_client`).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.153 |
| Files | 3 |
| Status | production-grade core · videocall state machine sin LiveKit |
| Tests | `backend/tests/motors/m20_workspace/` |
| API prefix | `/api/v1/workspace/*` |
| RBAC | Cat C · cliente accede a su workspace + Marcos también (`require_marcos_or_client`) |

## Key files

- `api.py` · endpoints HTTP workspace (files · feed · chat · videocall state)
- `workspace_service.py` · `WorkspaceService` core + `WorkspaceError`

⚠️ NO existe `service.py` único · core en `workspace_service.py`.

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `WorkspaceFile` + `WorkspacePost` + `WorkspaceMessage` (`backend/app/models/workspace.py`)
- `VideocallState` (state machine ligera)

RLS por `workspace_files` + `workspace_posts` + `workspace_messages`.

## Cross-motor integration

- **Inbound**:
  - M18 Communication (posts automáticos al feed desde reports)
  - M25 Lifecycle (eventos lifecycle posteados al feed)
- **Outbound**: ninguno directo
- **LLM agents**: ninguno (motor colaboración pura)

## Limitaciones conocidas

### Videocalls NO LiveKit integrado

Decisión ADR-004: NO LiveKit/Zoom/Teams internos · cliente PYME usa Meet/Zoom/Teams habitualmente. Workspace solo trackea state machine (programación · estado · participantes) sin engine de video real.

**Cuándo se integrará** · si aparece cliente categoría ALTA con requisito videocall internal-only por compliance · candidate LiveKit con E2E encryption.

## ADRs referenced

- ADR-004 · reuniones externas A18 admin-only (deriva esta decisión de NO LiveKit interno)

## Cement OPS

Append-only chat + feed es invariante audit trail (no edición ni delete post-publicación). SHA-256 obligatorio en files es invariante integrity (workspace ENS = evidence-grade).
