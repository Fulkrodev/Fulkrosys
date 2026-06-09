# Motor 21 · Portal Cliente

Portal persistente cliente con login email + password (SAN-E v3.MB-1.1 · TOTP off cliente per ADR-046 v3). Usuarios creados por Marcos desde cockpit. Roles con scopes predefinidos + custom. **Distinto de M12 Magic Link**: portal cliente requiere login persistente (sessions long-lived), magic links son tokens one-shot. Sibling de M21_diagnosis (numbering anomaly intencional). **HUB inbound crítico**: 10 motores upstream lo consumen para auth cliente.

## Funcionalidades

- **Auth service** (`auth_service.py`) login email+password · session management · CSRF triple binding · cookie común dual dispatcher (ADR-020).
- **ClientUser management** (Marcos crea/desactiva usuarios desde cockpit `/clients/{id}/users`).
- **Roles + scopes** (`scopes.py`) per ClientUser · scopes predefinidos (TASKS_READ · EVIDENCE_UPLOAD · etc.) + custom.
- **Audit log service** (`audit_log_service.py` + `audit_api.py`) audit trail acciones cliente (ClientUserAudit table).
- **Chat service** (`chat_service.py` + `chat_api.py` + `models_chat.py`) chat bidireccional cliente↔Marcos · `chat_threads` + `chat_messages`.
- **Task service** (`task_service.py` + `task_api.py` + `models_tasks.py` + `task_templates_loader.py`) tareas asignadas a cliente · estados workflow · templates per sector.
- **Notifications inbox** (`notification_service.py` + `notifications_inbox_api.py`) inbox de notificaciones cliente · centralizado per ADR-020.
- **Evidence upload portal** (`evidencias_upload_api.py`) cliente sube evidencias directamente · wire-up M07.
- **Recent activity API** (`recent_activity_api.py`) feed actividad reciente cliente.
- **Branding service** (`branding_service.py` + `admin_branding_api.py`) per-cliente branding (logo · colores · etc. · MB-9 cement).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 4.202 |
| Files | 19 |
| Status | production-grade · SAN-E v3.MB-1.1 cement |
| Tests | `backend/tests/motors/m21_portal_cliente/` |
| API prefix | `/client-auth/*` + `/client-portal/*` + `/clients/{id}/users/*` |
| RBAC | Mixed · cliente vía cookie+CSRF + admin (cockpit) vía `require_owner` |

## Key files

- `api.py` · auth router + portal router + cockpit users router
- `admin_branding_api.py` · branding management cockpit
- `auth_service.py` · login + session + CSRF triple binding
- `branding_service.py` · per-cliente branding logic
- `chat_service.py` + `chat_api.py` · chat bidireccional
- `models_chat.py` · ORM `chat_threads` + `chat_messages`
- `task_service.py` + `task_api.py` · task management
- `models_tasks.py` · ORM `client_tasks`
- `task_templates_loader.py` · task templates per sector
- `audit_log_service.py` + `audit_api.py` · audit trail
- `notification_service.py` + `notifications_inbox_api.py` · inbox cliente
- `evidencias_upload_api.py` · evidence upload portal
- `recent_activity_api.py` · feed actividad
- `scopes.py` · scopes ClientUser predefinidos

⚠️ NO existe `service.py` único · scope split por responsabilidad (auth · branding · chat · task · audit · notification · evidencias).

## DB tables

Motor-specific (ORM en `models_chat.py` + `models_tasks.py`):

- `chat_threads` · threads chat bidireccional
- `chat_messages` · mensajes chat
- `client_tasks` · tareas asignadas cliente

Y modelos compartidos `ClientSession` + `ClientUser` + `ClientUserAudit` (`backend/app/models/client_portal.py`). RLS por `client_*` tables.

## Cross-motor integration

- **Inbound** (motores que consumen M21_portal_cliente · **10 motores hub más grande FULKRO**):
  - M02 MAGERIT (cliente VE riesgos in-portal)
  - M03 DdA (cliente VE DdA + firma E.040)
  - M05 Obligations (cliente VE obligations + Gantt)
  - M05 Signing (auth ClientUser para firma)
  - M06 Document Factory (cliente VE documents)
  - M08 Verification (cliente VE pentest scope · ADR-020 Q5.3)
  - M11 Copiloto (CopilotoDock cliente)
  - M16 Onboarding (transition post-onboarding)
  - M19 Risk (cliente reporta incidentes)
  - M23 Retainer (cliente VE retainer status)
- **Outbound**: ninguno directo (motor de auth + UI portal · self-contained)
- **LLM agents**: ninguno directo

## ADRs referenced

- ADR-013 · separación arquitectónica de portales
- ADR-018 · aceleración auth unificado Mini-Fase 3.5 (IMPLEMENTED)
- ADR-019 · CSRF triple binding cliente
- ADR-020 · tablas sessions separadas + cookie común + dual dispatcher
- ADR-035 · referenced en código
- ADR-036 · referenced en código
- ADR-038 · referenced en código
- ADR-039 · referenced en código
- ADR-042 · magic-link policy híbrida final
- ADR-046 · capability vs feature_flag (TOTP off cliente cement)

## Cement OPS

HUB inbound más grande FULKRO **del cluster H7.C** (10 motores upstream). 10 ADRs referenced · motor más cemented arquitectónicamente. ADR-018+019+020 trio es invariante auth flow cliente (CSRF triple binding + session separation + cookie común dispatcher).
