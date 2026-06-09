# Ejecutable 8 · Pasada 15 · Frontend Quality + Junior-Onboardability

## Alcance y método

163 pages (admin 92 / client-portal 38 / portal 15 / radar 4 / legal 8 / public 2 / root 4). Muestra dirigida representativa por portal. **Runtime axe-core NO ejecutado** (no prod build `.next/BUILD_ID` ausente · sin servers :3000/:8000 · auth Ed25519 bloqueado per Pasada 7 OPS-052 72ª) → a11y evaluada por lectura de **97 specs polish** + componentes (permitido por tarea). grep solo verificación.

## 1 · UX coherence / aesthetic / states / responsive / branding por portal

| Portal | Layout/chrome | States (loading/error/empty) | Responsive | Branding | Veredicto |
|--------|---------------|------------------------------|------------|----------|-----------|
| **Admin** | `(admin)/layout.tsx`: AuthGuard owner + skip-link + Sidebar (drawer móvil `role=dialog aria-modal` + Escape) + Header + CommandPalette + CopilotPanel + OnboardingTourAdmin | data-table-skeleton + empty-state + Alert danger+retry primitives existen | `hidden lg:flex` sidebar + drawer móvil | root layout FulkroFooter + favicons | EXCELENTE |
| **Client-portal** | `ClientPortalChrome`: path-aware (login limpio sin chrome) + ClientSidebar/Header + CopilotoDock + OnboardingTutorial + ClientFooter + ClientBrandingProvider + ProjectFeaturesGate | 17/38 pages loading explícito · 16/38 error/empty · resto delega hijos | `hidden lg:flex` + dvh | ClientBrandingProvider (branding cliente) + ClientFooter | BUENO (heterogéneo a nivel page) |
| **Auditor-portal** | `(portal)` magic-link gated 12 sub-rutas `[token]/*` | specs polish auditor 12 (tests/polish/auditor-portal) | cubierto en specs | FulkroFooter global | BUENO |
| **Radar** | `(radar)/layout.tsx` top-level R23 · 4 pages | delega a `LeadsTable`/hooks `useRadarLeads` · h1 presente · InfoTag | tabla | InfoTag + Radar icon | BUENO |

Evidencia: `frontend/app/layout.tsx:47-55` (skip-link), `frontend/app/(admin)/layout.tsx:36-99`, `frontend/components/layout/ClientPortalChrome.tsx:54-77`.

## 2 · WCAG 2.2 AA

- Skip-link `#main-content` con `sr-only focus:not-sr-only` (`layout.tsx:48-53`) · `<main tabIndex={-1} id=main-content>` en ambos layouts.
- TooltipENS: `aria-label="Ayuda: ..."`, `focus-visible:ring-2`, `min-w/h 24px` touch target, tap-to-show móvil (`tooltip-ens.tsx:64-79`).
- CopilotGuidedFlow: `role=complementary` + `aria-label` + botones con `aria-label` toggle/dismiss (`CopilotGuidedFlow.tsx:149-195`).
- **Gate runtime estricto**: `polish-test-fixture.ts:162-165` `wcagAA = criticalSerious.length===0`. **0 de 97 specs pasan `axeExcludeRules`** → color-contrast (serious) SÍ se evalúa en runtime; el comentario de exclusión en `audit-helpers.ts:50` es solo informativo, no aplicado. CI `admin-polish-empirical.yml` exige critical+serious=0 sobre 102 pages.
- Criterios runtime: mobileResponsive (6 viewports, sin overflow horizontal) + keyboardNav (Tab order + focus-visible) + escape-closes-modal + loading/error/empty inyectados (interceptRouteSlow/500/Empty).

**Conclusión a11y**: cobertura de specs robusta; pendiente solo ejecución runtime (env-blocked, NO defecto de código).

## 3 · R30 admin tutor / R29 cliente-friendly

- **R30**: `phaseGuides.ts` cataloga 9 fases ENS (dimensiones/magerit/dda/risks/plan/evidence/conformity/dossier) con intro+whyImportant+steps+commonMistakes+estimatedTime+citas BOE/CCN. OnboardingTourAdmin 6 pasos ("como si fuera tonto · primer principios"). TooltipENS+glosario.
- **R29**: jerga ENS en client-portal SIEMPRE tooltipped. `dda/page.tsx:73` "La <TooltipENS DdA/> es el documento donde tu consultor"; `magerit/page.tsx:7` "Cliente NO edita ni clasifica activos (Marcos opera)"; `conformidad/page.tsx:82` "Marcos preparará tu...". Copy amable "Sin prisa por tu parte". 0 presión coercitiva detectada.

## 4 · Junior-onboardability

**ALTA**. Un junior sin ENS puede operar admin: CopilotGuidedFlow por fase (qué/por qué/cómo/errores) + TooltipENS glosario + OnboardingTourAdmin + CopilotPanel LLM con citas. Roadmap lineal 10 fases. Faltaría solo: atajo Ctrl+K marcado "(próximamente)" en tour.

## 5 · CSP estricta (TODO-SEC-CSP-001)

Diferida a FASE 13 pre-deploy (`next.config.mjs:15-16`). Headers básicos presentes: X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy (camera/mic/geo deshabilitados). Nota: sin `Content-Security-Policy` ni HSTS aún. Coherente con Pasada 9.

## Findings TAGGED

| ID | Título | Sev | Evidencia |
|----|--------|-----|-----------|
| F-15-01 | SSE accompaniment/certificación sin event type → timeline cert no refresca realtime (reconfirma P8 F-08-02) | medium | `useClientProjectEvents.ts:91-101` (sin AccompanimentEventType) + `AuditAccompanimentClienteView.tsx:72` (invalidate genérico) |
| F-15-02 | Cobertura estados loading/error/empty a nivel page heterogénea (17/38 client pages) | low | grep client-portal page.tsx |
| F-15-03 | FulkroFooter único global puede no encajar en auditor/público | info | `layout.tsx:55` |
| F-15-04 | a11y runtime no ejecutable (env-blocked) — solo lectura specs | info | no .next build / no servers / auth Ed25519 |
| F-15-05 | CSP estricta + HSTS diferidos (TODO-SEC-CSP-001) | info | `next.config.mjs:15-16` |

## Conclusión

Frontend de **calidad alta y junior-onboardable**. Infra a11y/tutor production-grade. Único defecto funcional real: F-15-01 (SSE accompaniment) → Pasada 16 añadir AccompanimentEventType al hook. Resto son gaps menores/informativos. CSP/runtime a11y son deferidos conocidos, no regresiones.