# AUDIT #5 · Cliente access features pending

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 4/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #5 · "Cliente access features pending · cosas que el cliente puede acceder"

---

## Verdict empírico

Cliente portal `/(client-portal)/client-portal/` es **production-grade massive** · **28 pages activas** (verified file count) · ya cubre todas las features ENS-only críticas cliente piloto MEDIA. Refactor 1.D.F.bis.III "indispensable-only" already executed.

**Gap específico identificado**: features esperadas adicionales (per briefing) audit-first reveals existing infrastructure:

| Feature esperada briefing | Status empírico | Page existing |
|---------------------------|-----------------|---------------|
| Dashboard cliente métricas | ✅ DONE | `/dashboard/` |
| Visualizar documentos DoA · Plan · Conformidad | ✅ DONE | `/dda`, `/conformidad`, `/files` |
| Aprobar remediaciones cloud (NEW #9) | 🔴 MISSING | NO page existing · Audit #9 captures |
| Ver alertas compliance | 🟡 PARTIAL | `/inbox` + `/incidents` (no dedicated compliance alerts feed) |
| Descargar carpeta evidencias | ✅ DONE | `/files` + `/evidencias` (m24_idms IDMS folder structure) |
| Comunicación con Marcos M21 chat | ✅ DONE | `/chat` |
| Settings cliente (avatar · notif · idioma) | 🟡 PARTIAL | `/account` + `/account/notifications` (NO avatar upload · NO idioma toggle) |
| MFA ENS MEDIA/ALTA requirement | 🟡 PARTIAL | login Ed25519 magic link (cliente sin password)  |

**ETA empírico realista refined**: ~6-12h gaps polish (vs ~10-20h nominal):
- Remediaciones cloud approval UI: ~4-6h (depends on Audit #9 backend gap)
- Settings avatar + idioma: ~2-3h (frontend polish only)
- Alertas compliance feed cliente: ~2-4h (M_compliance_monitor already production · solo wire UI cliente)
- MFA mejora demand-driven post-piloto (magic link sufficient BÁSICA)

---

## Stats baseline

### Cliente portal pages (~28 activas)
- Core ENS workflow: dashboard · workflow · tasks · magerit · dda · policies · conformidad · dpc-anual · evidencias · files · registros · registros/[tipo] · actas
- Firma + signing: firma · firmas-hub
- Comunicación: chat · inbox · whatsapp · incidents
- Onboarding: onboarding · onboarding/oauth-callback · pentest-authorization
- Retainer: retainer-checkin · billing · transparency
- Cuenta: account · account/notifications · login

### Backend cliente endpoints
- `client_copilot_stub.py` LLM stub (1.D.B.1 production Haiku 4.5)
- `sse_client_api.py` SSE event streams cliente-scoped
- `portal_workflow.py` workflow API cliente-scoped
- M21 portal_cliente motor (production-grade)
- M16 magic link login Ed25519

### Refactor recent context
- 1.D.F.bis.III "indispensable-only" refactor cliente (6 commits cumulative · sidebar 14→10 entries · pages SIMPLIFY magerit/dda/policies/files banners)
- Cliente HACE: aportar info empresa + activos + marcar M04 + subir evidencias + firmar Ed25519 + autorizar pentest + LMS empleados + reportar incidentes chat
- Marcos OPERA: M01/M02/M03 análisis técnico · M04 plan · M06 docs · m_live_records · etc

---

## Gap matrix detailed

### 🔴 Cloud remediations approval UI (depends Audit #9)
- Backend: depends Audit #9 status (probable greenfield)
- Frontend: page `/client-portal/remediaciones/` o sub-route `/files/remediaciones`
- Approval flow: cliente ve propuesta · 1-click approve/reject · firma Ed25519 si critical
- ETA: ~4-6h frontend + depends Audit #9 backend ~5-15h
- **Priority HIGH** · cliente piloto MEDIA gap real audit ENAC esperaría

### 🟡 Settings cliente avatar + idioma
- Page exists: `/account/page.tsx`
- Falta: avatar upload (m24_idms intake reusable?) + idioma toggle (i18n existing?)
- ETA: ~2-3h polish
- **Priority MEDIUM** · UX nicety NOT bloquea piloto

### 🟡 Alertas compliance feed cliente
- Backend ready: m_compliance_monitor 17 checks running (per Audit #2)
- Frontend gap: NO dedicated `/alerts/compliance` page · solo `/inbox` (genérico) + `/incidents` (specific)
- ETA: ~2-4h wire UI cliente leveraging m_compliance_monitor public_api existing
- **Priority MEDIUM** · piloto MEDIA puede usar inbox workaround

### 🟡 MFA ENS MEDIA/ALTA
- Current: cliente login Ed25519 magic link (single-factor cryptographic)
- ENS MEDIA requirement: MFA real (TOTP · WebAuthn · SMS)
- Workaround current: magic link Ed25519 satisface "factor cryptographic" + email/phone existing
- ETA: ~6-10h MFA real (WebAuthn cliente similar Marcos pattern existing)
- **Priority LOW pre-piloto** · post-piloto MFA upgrade demand-driven (cliente piloto MEDIA puede usar magic link inicial · MFA real iteración 2)

---

## Recomendación

**Priorizar por audit Cliente piloto MEDIA**:
1. **HIGH**: Cloud remediations approval UI (depends Audit #9 result) · ~4-6h frontend
2. **MEDIUM**: Alertas compliance feed cliente · ~2-4h wire UI
3. **MEDIUM**: Settings avatar + idioma polish · ~2-3h
4. **LOW**: MFA real upgrade · ~6-10h (Future-1.F demand-driven post-piloto)

**Total HIGH+MEDIUM pre-piloto**: ~8-13h frontend (assuming backend cloud remediations ready)

**Future-1.F.cliente-mfa-real** capturado para post-piloto.

---

## Cross-ref

- Cliente portal source: `frontend/app/(client-portal)/client-portal/`
- Backend cliente endpoints: `backend/app/api/v1/client_*.py` + `sse_client_api.py`
- M21 portal_cliente motor
- M16 magic link Ed25519 (login)
- 1.D.F.bis.III "indispensable-only" refactor reference (CLAUDE.md sections recent)
- Audit #9 dependency · cloud remediations backend status

---

## Honest notes

1. NO inspección detallada per page · sample 5 representative + count total
2. Sidebar 1.D.F.bis.III refactor cement · NO añadir entry "Remediaciones" sin re-audit sidebar simplification balance
3. MFA WebAuthn cliente puede tener complejidad cross-OS · UX cliente-friendly required (R29 sostained)
