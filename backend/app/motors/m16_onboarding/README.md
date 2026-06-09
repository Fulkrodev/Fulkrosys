# Motor 16 · Adaptive Onboarding

Onboarding adaptativo cliente: catálogo de templates por sector + role + estado · OAuth connectors (Microsoft 365 · Google Workspace · etc.) · LMS (Learning Management System) integrado · PKG (Package Generator) ingest tool registry · token encryption Fernet AES-128-CBC. Permite al cliente completar fase K.1 (intake) sin cuenta vía magic-link interlocutor.

## Funcionalidades

- **Catálogo templates** (`catalog_loader.py`) per sector + role + session state · `find_template_for` lookup.
- **Sessions onboarding** (`OnboardingSession` model) state machine `SessionState` (draft → sent → in_progress → completed → cancelled).
- **OAuth connectors** (`oauth_service.py` + `oauth_state_service.py` + `connectors/` subdir) wire-up M365/Google Workspace/GitHub Apps/etc.
- **Token encryption Fernet** (`token_encryption.py`) AES-128-CBC para tokens OAuth en BD · cumplimiento ISMS.
- **LMS integration** (`lms_service.py` + `lms_docx.py`) sistema de learning para cliente (cursos ENS · políticas internas · awareness).
- **PKG tools** (`pkg_service.py` + `pkg_ingest_service.py` + `pkg_tools.py` + `pkg_tools_registry.py`) Package Generator ingest tooling para cliente upload bulk data.
- **Discovery service** (`discovery_service.py`) auto-discovery infraestructura cliente post-OAuth.
- **Client service** (`client_service.py`) gestión datos cliente onboarding.
- **Portal API** (`portal_api.py`) cliente interlocutor responde questionnaire vía magic-link.
- **Addendum v22** (`addendum_v22.py`) extensiones MB-9.bis multi-norma.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 5.435 |
| Files | 20 (+2 subdirs: `connectors/` · `templates/`) |
| Status | production-grade · M16-A sub-pase foundation IMPLEMENTED |
| Tests | `backend/tests/motors/m16_onboarding/` |
| API prefix | `/api/v1/onboarding/*` (admin) + portal-api cliente |
| RBAC | Cat A · Marcos-only admin · cliente interlocutor vía magic-link |

## Key files

- `api.py` · endpoints HTTP admin (CRUD sessions · catalog · send)
- `portal_api.py` · endpoints cliente vía magic-link
- `service.py` · `OnboardingService` core
- `catalog_loader.py` · `load_all_templates` + `find_template_for` + `list_available_sectors`
- `client_service.py` · gestión datos cliente
- `discovery_service.py` · auto-discovery infraestructura
- `oauth_service.py` · OAuth flow gestión
- `oauth_state_service.py` · state CSRF protection
- `token_encryption.py` · Fernet AES-128-CBC tokens
- `lms_service.py` + `lms_docx.py` · Learning Management System
- `pkg_service.py` + `pkg_ingest_service.py` + `pkg_tools.py` + `pkg_tools_registry.py` · Package Generator
- `enums.py` · `Role` · `Sector` · `SessionState`
- `schemas.py` · Pydantic in/out
- `types.py` · tipos compartidos
- `addendum_v22.py` · extensiones MB-9.bis
- `connectors/` · subdir OAuth connectors M365/Google/etc.
- `templates/` · subdir templates onboarding per sector

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `OnboardingSession` (`backend/app/models/onboarding.py`)
- `OAuthConnector` (subdir connectors)
- `PkgIngestRun` (PKG ingestion runs)

RLS por `onboarding_sessions`.

## Cross-motor integration

- **Inbound**:
  - M21 Diagnosis (consume onboarding completion state)
  - M22 Discovery (consume infraestructura discovery output)
- **Outbound**:
  - M12 Magic Link (interlocutor magic-link sin cuenta)
  - M21 Portal Cliente (cliente UI portal)
  - M27 Conformity (mapping inicial conformity)
  - M28 Change Governance (cambios infra detectados)
- **LLM agents**: ninguno directo (motor template-driven)

## Limitaciones conocidas

### M16-B cliente flow forward

M16-A (foundation · admin creates sessions) IMPLEMENTED. M16-B (cliente consume magic link + responder preguntas + auto-discovery flow completo end-to-end) parcialmente implementado · refinement forward post-cliente piloto.

## ADRs referenced

- ADR-019 · CSRF triple binding cliente (OAuth state protection)
- ADR-020 · tablas sessions separadas con cookie común + dual dispatcher

## Cement OPS

Token encryption Fernet AES-128-CBC es invariante ISMS (tokens OAuth nunca plaintext en BD). Multi-sector templates extensibles (PYME · sanidad · educación · industrial · etc.).
