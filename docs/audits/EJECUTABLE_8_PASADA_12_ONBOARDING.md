# Ejecutable 8 · Pasada 12 · Onboarding Cliente

Verificación empírica del recorrido del cliente nuevo (primeros 5 minutos · zero friction). Ground-truth de archivos `path:línea`. NO se tocó BD ni se aplicó fix-forward (drift reservado Pasada 16).

## Recorrido paso a paso (page + evidencia)

| # | Paso | Page / archivo | Evidencia | Veredicto intuitividad |
|---|------|----------------|-----------|------------------------|
| 1 | Email primer acceso | `backend/app/motors/m21_portal_cliente/api.py:1351-1380` (`_render_primer_acceso_html`) | Header "Bienvenido a FULKRO" + magic-link `PRIMER_ACCESO_CLIENTE` (m12 `purposes.py:48,210` · TTL 24h · OTP opcional) + `must_change_password=True` (`api.py:1090,1149`) | 🟡 Funciona pero HTML pobre + branding ajeno (ver F-12-01) |
| 2 | Magic-link / login | `frontend/app/(client-portal)/client-portal/login/page.tsx` | Logo + `TooltipENS term="ENS"` (línea 99) · MFA step condicional 401 `requires_mfa` (l.20-26,145) · `must_change_password` → `/account?force_change=1` (l.47-49) | 🟢 Limpio, logo, TooltipENS presente, MFA challenge si aplica |
| 3 | Enrolment MFA | `frontend/app/(client-portal)/client-portal/settings/mfa/page.tsx` + `backend/.../mfa_api.py` | 3-step (initiate→QR→confirm→10 backup codes) · R29 "Sin prisa por tu parte · cuando quieras" (l.77-81) · **opt-in voluntario** | 🟡 Excelente UX pero NO ofrecido en onboarding (ver F-12-02) |
| 4 | First project setup wizard | `frontend/app/(client-portal)/client-portal/onboarding/page.tsx` + `components/project-wizard/steps/*` | Tabs: Conecta sistemas (`CloudConnectFirstStep`) · Wizard (`OnboardingClientFlow`) · Connectors · Cursos · "5 min · solo lectura" (l.100-103) · estados no-project/error friendly (l.81-93) | 🟢 Claro, zero-friction, R29 "Marcos te avisará" |
| 5 | Categorización (m01) | `frontend/.../categorizacion/page.tsx` | **READ-ONLY** cliente VE · admin opera (header comment l.10-13) · SSE `m01.categorizacion.completed` toast (l.56-65) · "Sin prisa por tu parte" (l.214-220) · R30 inverso NO DICAT crudo | 🟢 Cliente-mínimo perfecto (VE, NO opera) |
| 6 | First dashboard | `frontend/.../dashboard/page.tsx` → `ClientDashboardV3.tsx` | Zone1 `HeroAdaptativo` (saludo+tier+fase paso X/Y+countdown) · Zone2 `TodayActionsCards` (max 5, `actions[:5]` backend `adaptive_dashboard_service.py:367`) · Zone3 workflow/messages/docs/invoice | 🟢 Estructura clara sin jargon |
| 7 | Today actions | `TodayActionsCards.tsx` + `adaptive_dashboard_service.py:248-367` | Empty state celebratoria "¡No tienes pendientes!" (l.44-60) · acciones con `~X min` + "Hacerlo ahora" + `requires_step_up` badge OTP | 🟢 Proactivo, accionable, friendly |
| 8 | Tutorial onboarding tour | `components/client-portal/tutorial/OnboardingTutorial.tsx` (montado `ClientPortalChrome.tsx:11,73`) | 5 pasos auto-trigger first-login · `localStorage 'fulkro_tutorial_completed'` (l.16,56-64) · Paso X/Y + Saltar + Empezar · role=dialog aria-label | 🟡 Bueno pero localStorage-only (ver F-12-05) |
| 9 | Copilot friendly | `CopilotoDock` (`ClientPortalChrome.tsx:10,72`) · tutorial paso 3 lo señala | Dock flotante abajo-derecha · "responde con citas a la normativa ENS" | 🟢 Reachable + explicado en tour |
| 10 | Footer / identidad | `ClientFooter` (`ClientPortalChrome.tsx:9,68`) | Footer presente cross-portal | 🟢 |

## Evaluación hiper-intuitividad / friction

**Fortalezas (zero-friction confirmado):**
- Flujo lineal claro: email → login → tutorial → dashboard con Hero "dónde estás / qué hacer hoy".
- TodayActionsCards prioriza max 5 acciones con minutos estimados + CTA "Hacerlo ahora" + empty state celebratoria.
- Onboarding page enmarca "5 min · solo lectura" reduciendo ansiedad.
- Estados no-project/error siempre con copy tranquilizador ("Marcos te avisará").

**Fricciones detectadas:** ver findings F-12-01..05.

## R29 compliance

🟢 **SOSTENIDO fuerte** en todo el flujo frontend: tono "Sin prisa por tu parte" (categorización l.214, mfa l.77-81), congrats ("¡No tienes pendientes!"), NO presión coercitiva, NO admin lingo (categorización R30 inverso explícito, NO DICAT crudo). Única excepción: el **email primer-acceso backend** (`_render_primer_acceso_html`) usa "Plataforma de cumplimiento ENS" sin contexto friendly y estilo ajeno — ver F-12-01.

## R30 inverso (jargon sin TooltipENS)

🟢 Login usa `TooltipENS term="ENS"` correctamente. Categorización oculta DICAT crudo. 🟡 El email primer-acceso menciona "cumplimiento ENS" sin tooltip (medio aceptable: es email, no UI con tooltips), y el tutorial paso 1 dice "proyecto ENS" / "retainer post-cert" sin glosa (F-12-04).

## Conclusión

El onboarding cliente está **production-ready y mayormente hiper-intuitivo** con R29/cliente-mínimo sólidos. Las 5 fricciones son refinamientos de pulido (no bloqueantes): email branding desalineado, MFA no proactivo, saludo no time-of-day, tutorial no persistente server-side, jargon residual en tour. Todas TAGGED para Pasada 16.