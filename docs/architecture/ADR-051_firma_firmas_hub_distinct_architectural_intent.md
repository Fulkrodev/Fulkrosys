# ADR-051 · `firma/` vs `firmas-hub/` · 2 surfaces architectural intent · NO duplicate

**Status**: Accepted · 2026-05-13 (FASE 2 H3 cement post audit-driven cancel)
**Cement**: OPS-061 6ª aplicación cumulative · audit-first reveal superficial finding

## Context

Audit O3 (2026-05-13) detectó superficialmente:

> "firma/ Y firmas-hub/ cliente routes · legacy + v2 · candidate consolidation (firma/ legacy?)"
> — `O3_FRONTEND_CLIENTE_INVENTORY.md` línea 306 / 313
> — `O15_CONSOLIDATED_SUMMARY.md` HIGH PRIORITY #6 línea 124

Pre-audit empirical FASE-2-H3 reveló **NO duplicate**. Son **2 surfaces architectural intent distinct** sirviendo audiencias y propósitos ortogonales.

## Empirical findings (audit-driven sostained · OPS-026 36ª aplicación)

### Surface 1 · `firma/` = página explicativa legal

- **Path**: `frontend/app/(client-portal)/client-portal/firma/page.tsx` · 235 LOC
- **Tipo**: Server component (`Metadata` + pre-rendering) · sin estado/efectos
- **Components**: NO dedicated dir · reutiliza `@/components/auth/PublicKeyVerifier` + `@/components/ui/*` (server-rendered minimalist)
- **Intent**: página **EXPLICATIVA / educacional** "Cómo funciona la firma electrónica de FULKRO"
- **Cement architectural**: ADR-009 (NO eIDAS/TSA preventivo) + ADR-010 (cláusula firma C-001 + página explicativa) — preserved sostained
- **Cement contractual**: plantilla M06 cláusula 14 C-001 **CITA URL LITERAL** `/client-portal/firma` (modificar URL = breaking change en contratos cliente firmados)
- **Cross-refs preservadas**:
  - `frontend/app/(client-portal)/client-portal/retainer-checkin/page.tsx:91` — link href="/client-portal/firma"
  - `frontend/app/docs/verify-signature/page.tsx:36` — texto público referencia URL literal
  - `frontend/components/auth/PublicKeyVerifier.tsx:9` — docstring "Reutilizable en /client-portal/firma"
- **Trazabilidad DECISIONS.md línea 449**: "ADR-009 + ADR-010 + LEGAL_DISCLAIMERS.md + cláusula 14 C-001 + página /client-portal/firma (**5 puntos consistentes**)"
- **Last modified**: 2026-05-08 `00ca765` (tooltips ENS-friendly density-gated [6/8]) — vivo y mantenido

### Surface 2 · `firmas-hub/` = hub operativo MB-6 atom 0.2

- **Path**: `frontend/app/(client-portal)/client-portal/firmas-hub/page.tsx` · 150 LOC
- **Tipo**: Client component (`"use client"`) · hook `useSigningHistoryClient`
- **Components**: `frontend/components/client-portal/firmas-hub/` · 3 .tsx · 360 LOC
  - `ChainIntegrityBanner.tsx` (96 LOC)
  - `ChainVisualizer.tsx` (76 LOC)
  - `SignatureCard.tsx` (188 LOC)
- **Intent**: **HUB INTERACTIVO** "Mis firmas ENS" · cliente VE todas sus firmas previas + chain integrity status + 4 cards per signable_type + readiness snapshot
- **Cement architectural**: SAN-E v3.MB-6 atom 0.2 implementation cement
- **Backend wire-up**: `GET /api/v1/portal/signing/projects/{id}/history` (motor M05 signing)
- **Sidebar navigation**: `frontend/components/layout/ClientSidebar.tsx:77` — `{ label: "Mis firmas", href: "/client-portal/firmas-hub", icon: FileSignature }`
- **E2E tests**:
  - `frontend/tests/e2e/firmas-hub-cliente-e2e.spec.ts` (spec dedicado MB-6 atom 0.2 + chain evolution atoms 1-7)
  - `frontend/tests/e2e/dpc-anual-cliente-e2e.spec.ts:45` (referencia 6-link sidebar)
  - `frontend/tests/e2e/policies-cliente-e2e.spec.ts:32` (policy_approval card chain shape)
- **Last modified**: 2026-05-11 `02bfc3b` (firmas-hub · chain integrity visualization · MB-6 atom 0.2)

## Decision

**NO consolidate. NO eliminate `firma/`. NO merge `firma/` → `firmas-hub/`.**

2 surfaces sirven intents distintos arquitectónicamente cementados:

| Aspecto | `firma/` | `firmas-hub/` |
|---|---|---|
| Audiencia | cliente (educacional + verificador público) | cliente (operativo) |
| Naturaleza | estática · legal disclosure | dinámica · transaccional |
| Cement | ADR-009 + ADR-010 + C-001 contractual | MB-6 atom 0.2 + ADR-020 in-portal review |
| Navegación | links contextuales (retainer + docs + plantilla) | sidebar item dedicado "Mis firmas" |
| Backend | ninguno (server-rendered + public key verifier) | `GET /api/v1/portal/signing/projects/{id}/history` |

Eliminar `firma/` rompería **5 puntos consistentes** de trazabilidad ADR-010 (incluyendo cláusula contractual C-001 firmada por clientes).

Audit O3 #6 finding RECLASSIFIED ✅ RESOLVED via audit-driven cancel.

## Consequences

- `firma/` preservado as-is — ADR-010 + C-001 URL literal cement sostained
- `firmas-hub/` preservado as-is — MB-6 atom 0.2 backend API integration sostained
- Plantilla M06 cláusula C-001 NO touch — cement contractual sostained
- Cross-refs (`retainer-checkin` + `docs/verify-signature` + `PublicKeyVerifier`) preserved
- NO scope creep refactor sin necessity empirical (OPS-027 sostained)

## OPS cement

- **OPS-026 audit-first 36ª aplicación** · pre-audit cazó audit O3 falso-positivo antes de ejecutar cleanup
- **OPS-061 6ª aplicación cumulative** · vaporware-detection pattern (6 instancias acumuladas: M32 Capabilities · features panel path · Intelligence cross-motor · backup encryption-as-stub · ADR-037/042/043 self-collisions · copilot/copiloto "duplicate" H2 ADR-049 · ahora firma/firmas-hub "duplicate" H3 ADR-051)
- **OPS-027 sostained** · existing infra discovery · NO scope creep
- **OPS-062 sostained** · architectural cement con ADR explicit ≠ silent debt

## Referencias

- ADR-009 — FULKRO NO implementa firma cualificada eIDAS/TSA
- ADR-010 — Cláusula firma C-001 + página "Cómo funciona la firma"
- ADR-020 — Tablas sessions separadas con cookie común + dual dispatcher
- ADR-049 — Copilot Agent 14 · 3 surfaces architectural intent · NO duplicate (FASE 2 H2 cement)
- DECISIONS.md líneas 316, 338, 442, 449 (ADR-010 trazabilidad 5 puntos consistentes)
- `O3_FRONTEND_CLIENTE_INVENTORY.md` línea 306 / 313 (audit O3 finding · RECLASSIFIED ✅ RESOLVED)
- `O15_CONSOLIDATED_SUMMARY.md` HIGH PRIORITY #6 línea 124 (RECLASSIFIED ✅ RESOLVED)
