# Motor 30 · Client Contacts

Catálogo de contactos por cliente (**NO usuarios del portal** · distinto de M21 ClientUser). Permite a Marcos mantener una agenda profesional con cargos, roles, signatarios, preferencias de comunicación y notas internas + timeline de interacciones cross-motor (A18 reuniones · M29 mensajes · M12 magic links · M14 contratos). Plan v4.2 FASE 5.5. Roles ENS staff (Responsable Seguridad · Sponsor · DPO · etc.).

## Funcionalidades

- **CRUD contactos** per cliente (`service.py` · 13 métodos plan v4.2 FASE 5.5.B): create · list · get_by_id · update · deactivate · activate · delete_cascade.
- **Timeline cross-motor** (`get_timeline`) consolidated event timeline per contacto (reuniones A18 · mensajes M29 · magic links M12 · contratos M14).
- **Auto-log interaction** (`log_interaction`) entry point cross-motor. A18/M14/M29 invocan tras crear su entity.
- **Get for copilot context** (`get_for_copilot_context`) provides contacto context to A14 Copiloto.
- **Import CSV** + **Export CSV** bulk operations (10 endpoints plan v4.2 FASE 5.5.C).
- **Full-text search GIN** index sobre contactos.
- **Roles ENS staff** (`roles_ens.py`) catálogo roles ENS (Responsable Seguridad · Sponsor · DPO · Tech · Legal · etc.).
- **ENS required** (`ens_required.py` + `ens_required_api.py`) tracking de roles ENS obligatorios cumplidos per cliente.
- **Project scope** (`project_scope_api.py`) scope contactos per proyecto.
- **TODO-M30-M12-INTEGRATION-001** [BAJA]: M12 Magic Links FK `sent_to_contact_id` diferido (H1 audit pre-impl 2026-04-29).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.107 |
| Files | 9 |
| Status | production-grade · FASE 5.5 plan v4.2 cement |
| Tests | `backend/tests/motors/m30_client_contacts/` |
| API prefix | `/api/v1/clients/{client_id}/contacts/*` (+ ens-required + project-scope sub-routers) |
| RBAC | Cat A · Marcos-only (`require_owner`) · M30 admin-only |

## Key files

- `api.py` · 10 endpoints CRUD + timeline + import/export CSV
- `ens_required_api.py` · endpoints ENS roles required tracking
- `project_scope_api.py` · endpoints project scope contactos
- `service.py` · `ClientContactsService` 13 métodos core
- `models.py` · ORM `client_contacts` + `client_contact_interactions`
- `roles_ens.py` · catálogo roles ENS staff
- `ens_required.py` · ENS required tracking logic
- `schemas.py` · Pydantic in/out (ClientContactCreate · etc.)

## DB tables

Motor-specific (ORM en `models.py`):

- `client_contacts` · catálogo contactos per cliente
- `client_contact_interactions` · timeline interactions cross-motor (sourcing A18 · M29 · M12 · M14)

RLS · `USING (true)` + RBAC `require_owner` (M30 admin-only · R4 audit cement 2026-04-29).

## Cross-motor integration

- **Inbound** (**HUB inbound cross-motor**): motores que invocan `log_interaction`:
  - M06 Document Factory (stakeholders helper)
  - M12 Magic Link (envío contactos · diferido FK)
  - M14 Contracts (firmantes contractuales)
  - M18 Communication (destinatarios reports)
  - M28 Change Governance (notificación stakeholders cambio)
  - M29 Client Messaging (auto-log mensaje a contacto)
  - M_meetings (A18 reuniones)
- **Outbound**: ninguno directo
- **LLM agents**: A14 Copiloto (consume `get_for_copilot_context`)

## ADRs referenced

- ADR-012 · M30 Client Contacts motor nuevo (cement decisión inicial)
- ADR-020 · in-portal review pattern (cliente VE contactos in-portal)
- ADR-046 · capability vs feature_flag

## Cement OPS

`log_interaction` es entry point cross-motor invariante (timeline cliente sourcing 7 motores upstream). NO usuarios del portal cement (distinto de M21 ClientUser · contactos profesionales agenda Marcos). FASE 5.5 plan v4.2 cement. R4 audit RLS `USING (true)` + RBAC require_owner es invariante (M30 admin-only).
