# Sesión 3B-2B.2 Path B · Playwright + axe-core Setup Guide

**Status**: Phase 0 scaffold CREATED · awaiting Marcos empirical execution.
**Architectural decision**: Path B approved · OPS-052 15ª PREVENTED.

## Purpose

REAL empirical 12-criteria verification per admin page via Playwright runtime + axe-core/playwright scanning. Replaces previous "audit-first reveals existing" inference pattern (OPS-045 shortcut) with empirical evidence captured at runtime.

## Files created Phase 0

| Path | Purpose |
|------|---------|
| `frontend/playwright.polish.config.ts` | Dedicated Playwright config (separate from main `playwright.config.ts`) · 6 viewports · HTML reporter to `polish-report/` · output `polish-test-results/` |
| `frontend/tests/polish/_helpers/audit-helpers.ts` | axe scan · screenshot per viewport · horizontal overflow check · Tab order capture · Escape on modal · route intercept (slow/500/empty) · breadcrumb check · focus-visible check |
| `frontend/tests/polish/_helpers/polish-test-fixture.ts` | Custom test fixture · authedPage (loginAsMarcos reuse) · runFullPolishSweep helper aggregating 12 criteria |
| `frontend/tests/polish/probe/01_admin_dashboard.spec.ts` | PROBE 1/5 · /admin/dashboard |
| `frontend/tests/polish/probe/02_admin_projects_selector.spec.ts` | PROBE 2/5 · /admin/projects (mocks 2 clients to bypass auto-redirect) |
| `frontend/tests/polish/probe/03_admin_project_roadmap.spec.ts` | PROBE 3/5 · /admin/projects/[id]/roadmap |
| `frontend/tests/polish/probe/04_admin_project_summary.spec.ts` | PROBE 4/5 · /admin/projects/[id]/summary |
| `frontend/tests/polish/probe/05_admin_project_dda.spec.ts` | PROBE 5/5 · /admin/projects/[id]/dda |
| `frontend/package.json` | Added `@axe-core/playwright` devDependency + 6 npm scripts `test:polish:*` |

## Setup verification commands (Marcos local · WSL native)

### 1. Install dependencies (UNC path fails · must use WSL native context)

```bash
# Open WSL terminal directly · NOT through Windows IDE that mounts UNC
wsl
cd /home/usuario/fulkro/frontend
npm install
```

**Expected**: installs `@axe-core/playwright@^4.10.1` + existing devDeps.

### 2. Install Playwright browsers (if missing)

```bash
npx playwright install --with-deps chromium
```

Per LECCIÓN-OPS-050 + 1.D.H.bis.A: browsers should already be at `~/.cache/ms-playwright/chromium-*` from previous Sesión 1 ADDENDUM setup. Verify:

```bash
ls ~/.cache/ms-playwright/ 2>/dev/null || ls /mnt/c/Users/Usuario/AppData/Local/ms-playwright/ 2>/dev/null
```

### 3. Verify scaffold compiles

```bash
cd /home/usuario/fulkro/frontend
npx playwright test --config=playwright.polish.config.ts --list 2>&1 | head -20
```

**Expected**: lists 5 probe specs · 5 test cases.

### 4. Pre-flight backend + frontend

Per LECCIÓN-OPS-050 mandatory:

```bash
# Backend running port 8000 with APP_ENV != production
curl -fsS -X POST http://localhost:8000/api/v1/_dev/create-test-client > /tmp/test-client.json
cat /tmp/test-client.json
# Should show: {"email": "...", "user_id": "...", "role": "owner"}

# Frontend prod build serving port 3100
# (Playwright config webServer auto-starts but verify locally first)
curl -fsS http://localhost:3100 > /dev/null && echo "frontend OK"
```

#### Port resolution scenarios (post-OPS-052 16ª fix)

**Scenario A · Marcos corre `npm run dev` ya en port 3000**:
```bash
# Playwright reuse-existing-server connects to 3000 · NO spawn
PLAYWRIGHT_PORT=3000 PLAYWRIGHT_SKIP_WEB_SERVER=1 npm run test:polish:probe
```

**Scenario B · Playwright spawn dev server propio (HOT reload friendly · slower compile)**:
```bash
PLAYWRIGHT_PORT=3100 PLAYWRIGHT_USE_DEV=1 npm run test:polish:probe
```

**Scenario C · Playwright spawn prod build (default · `npx next start`)**:
```bash
# Requires .next/ prod build · first run:
npm run build
# Then default:
npm run test:polish:probe   # PORT=3100 · next start
```

**Scenario D · CI typical**:
```bash
npm run build
PLAYWRIGHT_PORT=3100 npm run test:polish:probe
```

### 4.bis Error boundaries verification (post-OPS-052 16ª fix)

5 error boundary files now exist (sin estos "missing required error components, refreshing..." Next.js error):

```bash
ls frontend/app/global-error.tsx                  # root · replaces layout on crash
ls frontend/app/error.tsx                          # within root layout
ls frontend/app/\(admin\)/error.tsx                # admin route group
ls frontend/app/\(client-portal\)/error.tsx        # client portal route group
ls frontend/app/\(radar\)/error.tsx                # ENS Radar route group
ls frontend/app/\(portal\)/error.tsx               # portal route group (pentester · remediation · verify-auth)
```

If `_dev/create-test-client` returns a project_id in the future enhancement,
export it for project-scoped probes:

```bash
export POLISH_TEST_PROJECT_ID="<uuid from globalSetup>"
```

### 5. Run PROBE batch 5 P1 pages

```bash
cd /home/usuario/fulkro/frontend
npm run test:polish:probe
```

**Expected output**:
- Each probe spec runs · captures evidence
- Per spec: 6 screenshots per viewport (mobile-sm/md · tablet/L · laptop · desktop) = 30 screenshots cumulative
- Per spec: axe violations captured (critical+serious must be 0)
- Per spec: Tab order length captured
- Per spec: `criteria-result.json` attached to test info

### 6. View HTML report

```bash
npm run test:polish:report
```

Opens `polish-report/index.html` with:
- Per spec pass/fail status
- Screenshots viewable per viewport
- Trace viewer per failed test
- Attached `criteria-result.json` per spec (raw evidence)

## 12 criteria empirically verified

Per `runFullPolishSweep` in `polish-test-fixture.ts`:

| # | Criterion | Verification method |
|---|-----------|---------------------|
| 1 | Title + breadcrumb | h1/h2 visible + project breadcrumb if scoped |
| 2 | Loading skeleton | render success (data fetched) · structural check |
| 3 | Error retry | retry button presence (post-Sesión-3B-2B retry pattern formalized) |
| 4 | Empty state | structural check · per-page polish refines |
| 5 | Mobile responsive | screenshot + horizontal overflow check per 6 viewports |
| 6 | Keyboard navigation | Tab order length > 0 + focus-visible indicator |
| 7 | WCAG AA | axe-core scan · critical+serious violations = 0 |
| 8 | Tanstack-query | network idle within 5s |
| 9 | CTA visible | button/link with role=button count > 0 |
| 10 | Help tooltip | aria-describedby OR data-tooltip OR aria-label count > 0 |
| 11 | Server feedback | Sonner toast container presence |
| 12 | Project context | ProjectBreadcrumb visible (if scoped) |

## Honest framework limits

- **WCAG AA via axe-core/playwright**: catches ~57% of accessibility issues (axe-core docs). Manual QA still needed for cognitive load · screen reader test · keyboard real device test.
- **Mobile responsive horizontal overflow**: detects scrollWidth > viewport.width. Does NOT detect text truncation · awkward tap targets · poor layout aesthetics.
- **Tab order capture**: 30 max tabs · stops at body return. Does NOT verify logical reading order semantically.
- **NOT replaces manual QA**: empirical regression catch · NOT comprehensive UX evaluation.

## Phase P expected outcome

Per briefing PHASE P:
- If <50% PROBE pages PASS all 12 → 3B-2B claim "production existing" CONFIRMED OVERSTATED · Phase A scope expand
- If >50% violations critical → mayor refactor needed · architect decide
- Marcos reviews HTML report · approves Phase A scope

## Honesty note

**This document confirms scaffold creation only · NOT empirical results.**

The scaffold is structured to produce empirical results when Marcos executes `npm run test:polish:probe` in WSL native context with backend+frontend running. Until that execution happens · ZERO empirical findings have been generated by this session.

OPS-052 15ª PREVENTED: I did NOT fabricate empirical results from static code analysis. The honest deliverable is: runnable scaffold + clear setup guide + explicit gating on Marcos execution.

## Next steps

1. **Marcos**: run setup verification commands #1-#5 above
2. **Marcos**: review HTML report per PROBE results
3. **Architect decision**: if PROBE succeeds → continue Phase A (per-page fix iterations on real gaps). If setup fails → STOP HARD diagnose
4. **DEFER until Marcos verify**: P1+P2 spec creation (40 more specs) + fix iterations + cross-app consistency + CI integration

## OPS-052 16ª manifestación · post-PROBE diagnose history

**Symptom observed**: 5/5 PROBE specs FAIL mobile responsive · trace screenshots reveal:
- URL http://localhost:3100/admin/dashboard (port mismatch · Marcos dev en 3000)
- Next.js "missing required error components, refreshing..." overlay

**Root causes diagnosed**:
1. Port hardcoded 3100 with `npx next start` requires prod build (.next/) · may be stale OR missing
2. NO error boundaries (`app/error.tsx`, `app/(admin)/error.tsx`, etc) → runtime exceptions cascade unprotected
3. Marcos custom dev server on 3000 not reused by config

**Fixes applied this commit**:
1. **5 error boundary files** created (root global · root segment · admin · client-portal · radar · portal route groups)
2. **playwright.polish.config.ts** extended:
   - `PLAYWRIGHT_PORT` env var support
   - `PLAYWRIGHT_USE_DEV=1` → spawn `npm run dev` (NOT `next start`)
   - `PLAYWRIGHT_SKIP_WEB_SERVER=1` → reuse Marcos's existing dev server
   - webServer timeout 120s → 180s (dev compile slower)
   - stdout/stderr piped for diagnosability

**Re-PROBE instructions Marcos**:
```bash
cd /home/usuario/fulkro/frontend
# Option A · reuse Marcos's existing npm run dev on port 3000
PLAYWRIGHT_PORT=3000 PLAYWRIGHT_SKIP_WEB_SERVER=1 npm run test:polish:probe
# Option B · let Playwright spawn dev server
PLAYWRIGHT_PORT=3100 PLAYWRIGHT_USE_DEV=1 npm run test:polish:probe
# Option C · prod build then test (recommended for CI · slower local)
npm run build
npm run test:polish:probe
```

**Architect decision required**: which scenario (A/B/C) does Marcos prefer for empirical PROBE re-execution?

OPS-052 manifestación 16ª PREVENTED: infrastructure gap surfaced honestly · NO fake polish fixes attempted before infrastructure resolved.
