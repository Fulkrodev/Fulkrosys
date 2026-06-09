# ADR-049 · Copilot Agent 14 · 3 surfaces architectural intent · NO duplicate

**Status**: Accepted · 2026-05-13 (FASE 2 H2 cement post audit-driven)
**Cement**: OPS-061 5ª aplicación · audit-first reveal superficial finding

## Context

Audit O2 (2026-05-13) detected superficially "copilot/copiloto duplicate component dirs · consolidate candidate". Pre-audit empirical FASE-2-H2 reveló NO duplicate · 3 surfaces architectural distinct intent serving 2 audiences distinct (admin owner pool + cliente client_user pool).

## Empirical inventory cumulative (audit-driven sostained)

### Surface 1 · Admin Sheet side panel

- **Path**: `frontend/components/copilot/` (English · matches `/admin/copilot` route)
- **6 files · 609 LOC** (CitationPopover · CopilotComposer · CopilotMessage · CopilotMessages · CopilotPanel · QuickActionButtons)
- **Trigger**: `useCopilotPanelShortcut` keyboard binding
- **UI**: shadcn Sheet side overlay
- **Consumer**: `(admin)/layout.tsx <CopilotPanel />`

### Surface 2 · Admin fullscreen page

- **Path**: `frontend/app/(admin)/admin/copilot/page.tsx`
- **Component**: `components/agents/CopilotChat` (3rd component · separate)
- **Trigger**: URL navigation
- **UI**: Fullscreen 3-col chat
- **Endpoint**: `POST /api/v1/agents/14/invoke` (DevHint streaming mock pendiente)

### Surface 3 · Cliente floating dock

- **Path**: `frontend/components/copiloto/` (Spanish · matches backend convention)
- **1 file · 264 LOC** (CopilotoDock)
- **Trigger**: auto-mounted `ClientPortalChrome` always visible
- **UI**: Floating bottom-right dock
- **Endpoint**: SSE `/api/v1/client-portal/copiloto/chat/stream`

## Backend consistency

```text
backend/app/motors/m11_copiloto/         Spanish (matches cliente surface)
backend/app/agents/agent_14_copiloto/    Spanish (matches cliente surface)
```

Agent 14 underlying service shared cross-surfaces.

## Decision

**NO consolidate**. 3 surfaces serve different pools/audiences/contexts.

Architectural intent intentional cement:
- English admin convention (admin route URLs · admin components)
- Spanish cliente convention (matches backend motors/agents)
- 3 distinct surfaces empirical · ADR-013 separación 3 portales honored

## Consequences

- Components dirs preserved as-is (`copilot/` admin + `copiloto/` cliente)
- `frontend/components/agents/CopilotChat` admin fullscreen surface preserved
- Audit O2 finding "copilot/copiloto duplicate" RECLASSIFIED ✅ RESOLVED via audit-driven cancel · OPS-061 5ª aplicación
- Tests E2E asserting separation cement preserved (`separacion-portales.spec.ts:55-59` cement ADR-013)

## OPS cement

- **OPS-026** audit-first 34ª aplicación · pre-audit cazó superficial finding
- **OPS-061** 5ª aplicación · vaporware-detection cumulative pattern
- **OPS-027** sostained · existing infra discovery · reuse vs reinvent (NO scope creep refactor sin necessity empirical)
