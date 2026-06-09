# Motor 6 · Document Factory

Generación masiva de documentos ENS auto-rellenados desde templates DOCX/XLSX usando Jinja2, con firma Ed25519 + conversión a PDF. Factory para los 50+ entregables del flow ENS (políticas, actas, dossiers, planes, normas, etc.) personalizados per cliente. Stakeholder + rectores generators + documentation levels Básica/Media/Alta gradado.

## Funcionalidades

- **Templates DOCX/XLSX** registrados en catálogo versionado (`template_registry.py` + `catalog_loader.py` · 50+ templates).
- **Rendering Jinja2** con filtros custom (`filters.py` · stakeholders · fechas ENS · clasificación).
- **Auto-fill personalization** vía `stakeholders_helper.py` (datos cliente DPO/Security/Marcos + sub-procesadores).
- **Documentation levels** gradados (`documentation_levels.py`) · BÁSICA / MEDIA / ALTA niveles distintos de profundidad documental per medida ENS Anexo II.
- **Excel generators** subdir dedicado para artefactos tabulares (Sub_Processors_Inventory.xlsx · matrices · planificaciones).
- **Rectores generator** (`rectores_generator.py`) genera documentos rectores ENS (Política de Seguridad · Análisis de Riesgos · Plan de Tratamiento).
- **Addendum v22** (`addendum_v22.py`) extensiones MB-9.bis multi-norma (DORA · NIS2 · ENS).
- **Policy sign-off service** (`policy_signoff_service.py`) tracking de firmas de políticas.
- **Firma Ed25519 + PDF conversion** (`signing.py` + `rendering.py`).
- **Render preview** sin generar artifact final (testing UI).
- **Portal cliente view** (`portal_api.py`) cliente visualiza documents disponibles.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 6.284 |
| Files | 117 (incluye `templates/` + `excel_generators/` subdirs con artefactos) |
| Status | production-grade |
| Tests | `backend/tests/motors/m06_document_factory/` |
| API prefix | `/api/v1/document-factory/*` (admin) + portal-api cliente |
| RBAC | Cat A · Marcos-only admin · cliente vía portal-api |

## Key files

- `api.py` · endpoints admin (CRUD templates + generate + preview + dashboard)
- `portal_api.py` · endpoints cliente (list + view documents)
- `service.py` · `DocumentFactoryService` core (template resolve · render · sign · convert)
- `catalog_loader.py` · carga + versioning catálogo templates
- `template_registry.py` · registro central de templates
- `template_resolver.py` · resolución de template per `DocumentType` + `DocumentationLevel`
- `rendering.py` · Jinja2 + DOCX rendering + PDF conversion
- `filters.py` · filtros Jinja2 custom ENS-specific
- `stakeholders_helper.py` · helpers para personalization stakeholders
- `documentation_levels.py` · enums + lógica BÁSICA/MEDIA/ALTA
- `rectores_generator.py` · generador documentos rectores ENS
- `signing.py` · firma Ed25519 wire-up M05_signing
- `policy_signoff_service.py` · tracking firmas políticas
- `addendum_v22.py` · extensiones MB-9.bis multi-norma
- `enums.py` · `DocumentEstado` + tipos
- `exceptions.py` · domain errors (TemplateNotFoundError · MissingPlaceholderError · etc.)
- `schemas.py` · Pydantic in/out
- `excel_generators/` · subdir Excel artifacts generators
- `templates/` · subdir DOCX/XLSX templates source

## DB tables

N/A motor-specific · usa modelos `Template` (`backend/app/models/document_factory.py`) + `Document` (`backend/app/models/documents.py`). RLS por `documents`.

## Cross-motor integration

- **Inbound**: M18 Communication (envío docs adjuntos email/WA) · `reports` cross-motor
- **Outbound**: M05_signing (firma) · M21_portal_cliente · M30 Client Contacts (stakeholders data)
- **LLM agents**: ninguno directo en motor (LLM contextual via M11_copiloto si requested)

## Limitaciones conocidas

### Templates source NO versionados in-DB

Los templates DOCX/XLSX viven como artifacts in `templates/` + `excel_generators/` subdirs · NO en BD. Update template requiere deploy code (commit + rebuild). Aceptable: templates ENS son canónicos y rarely-change por norma.

**Cuándo se externalizará** · si aparece demanda de edición de templates por usuario admin sin code deploy · candidate para M26 Backup-managed template storage.

## ADRs referenced

- ADR-020 · in-portal review pattern (afecta portal_api cliente view)
- ADR-036 · catálogo templates (referenced en service)

## Cement OPS

Motor central pesado · 117 files (incluye templates source). Pattern consistente M04/M19: async methods, AsyncSession, exceptions-driven, no internal commits, RLS enforcement.
