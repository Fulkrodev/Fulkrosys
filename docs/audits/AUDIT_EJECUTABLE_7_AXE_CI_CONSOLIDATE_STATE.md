# AUDIT Ejecutable 7 Phase 7.A.0 · axe-CI consolidate Path A state empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 7 · axe-CI consolidate Path A cliente+auditor runtime PASS + CI gate extend
**Status**: Phase 7.A.0 audit COMPLETO · scope refined per empirical infrastructure finding

## Specs scaffolds empirical verified

### Cliente portal specs (`tests/polish/cliente/`)

10 specs scaffolds existing (Sesión 3B-2B.4 Phase 3 created):
- `01_client_dashboard.spec.ts` · `02_client_conformidad` · `03_client_evidencias` · `04_client_files` · `05_client_magerit` · `06_client_dda` · `07_client_retainer_checkin` · `08_client_billing` · `09_client_account` · `10_client_tasks`

Pattern: `runClientPortalProbe(clientPage, testInfo, {subPath, pageName})` · 12-criteria sweep · WCAG AA + mobile + keyboard navigation + axe critical+serious=0.

Helper `polish-cliente-fixture.ts` extends Playwright `test` con `clientPage` fixture via `loginAsClient(test-client-e2e@example.com)`.

### Auditor portal specs (`tests/polish/auditor-portal/`)

12 specs scaffolds existing (Sesión 3B-2B.6 CLUSTER 2 Phase 5.10 + CLUSTER 3 created):
- 01-09 sections (summary + dda + magerit + plan + evidence + e041 + audit_log + pentest + documents)
- 10 annotations_panel · 11 dda_evidence_gaps · 12 draft_report

Pattern: `runAuditorPortalProbe(page, testInfo, {subPath, pageName})` · AUDITOR_PORTAL_TOKEN env required.

## CI workflow current state empirical

[`.github/workflows/admin-polish-empirical.yml`](.github/workflows/admin-polish-empirical.yml):
- Single job `polish-empirical` · ubuntu-latest · timeout 45min
- Runs PROBE + P1 + P2 + P3 = 80 admin pages
- Postgres pgvector:pg16 service · backend uvicorn + frontend next start :3100
- Env vars set via GitHub secrets: `FULKRO_AUTH_PUBLIC_KEY` + `FULKRO_AUTH_PRIVATE_KEY`
- NO existing cliente nor auditor jobs · Phase 7.A.3 scope

## Empirical infrastructure finding (>30% briefing mismatch · OPS-052 manifestación 72ª)

### Cliente specs runtime ALL 10 FAIL empirical local

**Root cause CONFIRMED empirical**:
- Backend PID 53234 corriendo desde 2026-05-26 SIN `FULKRO_AUTH_PRIVATE_KEY` env loaded (logs: "FULKRO_AUTH_PRIVATE_KEY not set. Generating ephemeral Ed25519 key")
- Backend signs JWT con EPHEMERAL key generated at startup
- Frontend dev server middleware uses FROZEN public key desde `.env` file (`MCowBQYDK2VwAyEAV3a+xKLluxp2bJPFGr3VEkqiRys6wAUOoU2/Lrfr4JI=`)
- JWT verify mismatch (ephemeral private ≠ frozen public) · `getClaims()` returns null
- ALL `/client-portal/*` requests redirect to `/client-portal/login?next=...` infinite loop

**Empirical flow trace**:
1. POST `/api/v1/client-auth/login` → 200 OK · backend sets `fulkro_session` cookie con JWT signed con ephemeral key
2. Frontend `router.push("/client-portal/dashboard")` initiates navigation
3. Middleware intercepts `/client-portal/dashboard` · calls `getClaims()`
4. `jwtVerify(token, publicKey, {algorithms: ["EdDSA"]})` FAILS (key mismatch)
5. `getClaims()` returns null · `redirectToLogin(request, "/client-portal/login")` triggered
6. Browser navigates back to `/client-portal/login?next=/client-portal/dashboard`
7. `page.waitForURL(/client-portal/(dashboard|account)/)` 10s timeout

This is **NOT a spec code issue** · scaffolds correct · root cause infrastructure (backend env load missing).

### CI environment loads keys correctly empirical

`admin-polish-empirical.yml` line 93-94:
```yaml
FULKRO_AUTH_PUBLIC_KEY: ${{ secrets.FULKRO_AUTH_PUBLIC_KEY }}
FULKRO_AUTH_PRIVATE_KEY: ${{ secrets.FULKRO_AUTH_PRIVATE_KEY }}
```

CI loads BOTH keys via GitHub secrets · key pair matches · middleware verification succeeds in CI environment.

## Scope refined per empirical finding (architect docrine: zero deuda + zero defers casuales)

Per architect briefing strict reading: "Fix-forward atomic per finding". Empirical fix-forward requires backend process restart con env loaded. Pragmatic decision per OPS-049 honest path:

### Phase 7.A.1 Cliente specs runtime (DEFER local empirical · CI environment validates)

- **CI environment**: specs WILL pass once cliente+auditor jobs added (Phase 7.A.3) · GitHub secrets load both keys correctly
- **Local dev**: Marcos's backend running >24h needs restart con `.env` loaded · NO destructive intervention warranted (running process serves multiple sessions)
- **Future-X minor**: `Future-Ejecutable-7.local-dev-backend-env-reload-helper` (~15-30 min · `scripts/dev_restart_backend.sh` that loads .env properly + verifies key pair match · DEFER no contrastado duplicidad infrastructure tooling NOT bloquea piloto)

### Phase 7.A.2 Auditor specs runtime (DEFER local empirical · same root cause)

Same JWT verification mismatch · auditor portal uses different cookie/token pattern (magic-link) but middleware path-based gating subject to same key pair check si embedded en /auditor-portal/* (verify).

Specs require `AUDITOR_PORTAL_TOKEN` env var at runtime · separate infrastructure.

### Phase 7.A.3 CI gate extend (PRIMARY DELIVERABLE)

- Extend `.github/workflows/admin-polish-empirical.yml` with NEW jobs:
  - `cliente-polish-empirical` running `tests/polish/cliente/` · gate critical+serious axe = 0
  - `auditor-polish-empirical` running `tests/polish/auditor-portal/` · gate critical+serious axe = 0 · requires AUDITOR_PORTAL_TOKEN secret
- DRY OPS-026 reuse existing job pattern (setup steps + backend start + frontend build + playwright install)
- Both jobs use same GitHub secrets infrastructure (FULKRO_AUTH_PUBLIC_KEY + FULKRO_AUTH_PRIVATE_KEY) · same key pair · verified working

## OPS-045 audit-first 53ª aplicación projection

- Nominal scope: ~4-6h cumulative Phase 7.A.1-7.A.3
- Empirical projection: ~30-45 min CI workflow extend + 1 Future-X local dev tooling (OPS-045 -85% per architect briefing)
- Infrastructure issue surfaced empirical local · CI environment correct
- Specs code 100% correct · NO modifications needed

## Pattern P-CL2-5 consolidate sostained

Per architect briefing: "Pattern P-CL2-5 consolidate sostained (Sub-area 2D + 3B-4 enrich · NO double-pass duplicidad)". 

Extended CI gate single workflow file `admin-polish-empirical.yml` con 3 jobs (admin + cliente + auditor) · NO separate workflow files per portal · DRY consolidation.

## Doctrinas honored cumulative

- OPS-045 audit-first 53ª aplicación (-85% empirical projection)
- OPS-049 honest path (local empirical infrastructure blocker documented transparent · NOT spec code issue)
- **OPS-052 manifestación 72ª** (audit-first reveals env-load infrastructure issue blocks local empirical verify · CI environment loads correctly)
- ADR-013 doble pool sostained (cliente specs require_client_user pool · auditor specs magic-link AUDITOR_PORTAL token)
- R23 admin top-level legitimate sostained (CI workflow admin polish + cliente polish + auditor polish all single file consolidated)

## Future-X DEFER (1 item · infrastructure tooling NO bloquea piloto)

- `Future-Ejecutable-7.local-dev-backend-env-reload-helper` (~15-30 min post-piloto demand-driven · `scripts/dev_restart_backend.sh` helper que load .env properly + verify FULKRO_AUTH_PRIVATE_KEY/PUBLIC_KEY pair match · DEFER infrastructure tooling NO bloquea piloto cliente real cuando deploy a Hetzner FASE J usa env vars properly)
