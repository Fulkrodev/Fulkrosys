# Playwright Setup · FULKRO E2E Testing

Documentación reproducible para configurar Playwright E2E execution local. Mitigación LECCIÓN-OPS-050 (pre-flight environment validation obligatorio).

## Pre-requisitos

- **Node 18+ + npm** (Windows native OR WSL Ubuntu native)
- **Backend dev server running** puerto 8000 con `APP_ENV != production`
- **Frontend dev server running** puerto 3100 (Playwright config default · `PLAYWRIGHT_PORT` env override)
- **Endpoint env-gated accessible**: `POST /api/v1/_dev/create-test-client` retorna JSON test client (globalSetup requirement)
- **Playwright browsers installed** (~290MB chromium + headless-shell · ver Install paso 1)

## Install · One-time setup

### Paso 1 · Browsers

```bash
cd frontend
npx playwright install chromium          # ~179MB Chrome for Testing + ~111MB Headless Shell
# Opcional · adds firefox + webkit:
npx playwright install
```

Verify instalación correcta:

```bash
npx playwright install --dry-run chromium
# Debe mostrar "Install location: $LOCALAPPDATA/ms-playwright/chromium-XXXX" + "already installed"
```

### Paso 2 · WSL/Windows interop (si aplica)

El repo FULKRO vive en el filesystem de WSL (sustituye `<RAIZ_DEL_REPO>` por la ruta de tu clon; `git rev-parse --show-toplevel` la imprime) pero el shell de desarrollo puede ser:

**Opción A · WSL native node** (recomendado long-term):

```bash
# En Ubuntu WSL:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
which node node npx          # debe mostrar /usr/bin/node
cd "$(git rev-parse --show-toplevel)/frontend"
npm install                  # re-install para Linux binaries
npx playwright install chromium
```

Ventaja: zero-overhead · binaries nativos Linux · CI parity.

**Opción B · Windows interop (current setup)**:

```bash
# Desde WSL bash invocar Windows node.exe:
wsl -d Ubuntu --cd <RAIZ_DEL_REPO>/frontend -- \
  bash -c "'/mnt/c/Program Files/nodejs/node.exe' node_modules/@playwright/test/cli.js install chromium"
```

Limitación: browsers se instalan Windows-side (`$LOCALAPPDATA/ms-playwright/`) · Playwright launches Windows chrome-headless-shell.exe · funciona pero overhead interop por test.

## Execute specs

### Pre-flight check obligatorio (LECCIÓN-OPS-050)

```bash
# Verify Playwright browsers installed
[ -d ~/.cache/ms-playwright/ ] || \
  [ -d "$LOCALAPPDATA/ms-playwright/" ] || \
  { echo "⚠ run 'npx playwright install chromium' primero"; exit 1; }

# Verify backend endpoint accessible
curl -fsS -X POST http://localhost:8000/api/v1/_dev/create-test-client > /dev/null || \
  { echo "⚠ backend _dev endpoint NOT accessible · check APP_ENV + port 8000"; exit 1; }

# Verify frontend serving Playwright-expected port
curl -fsS http://localhost:3100 > /dev/null || \
  { echo "⚠ frontend NOT on port 3100 · check playwright.config.ts"; exit 1; }

# Verify spec files exist (avoid OPS-049 phantom)
SPEC_COUNT=$(find frontend/tests/e2e/fase_* -name "*.spec.ts" 2>/dev/null | wc -l)
echo "✅ pre-flight OK · $SPEC_COUNT specs encontrados"
```

### Run specs

```bash
cd frontend

# Single fase:
npx playwright test tests/e2e/fase_33 --reporter=list

# Cumulative all fases sub-bloque 1.D:
npx playwright test tests/e2e/fase_31 tests/e2e/fase_32 tests/e2e/fase_33 tests/e2e/fase_34 tests/e2e/fase_35 \
  --reporter=list --workers=2

# JSON summary for CI reporting:
npx playwright test --reporter=json > /tmp/playwright_summary.json

# Single spec debug:
npx playwright test tests/e2e/fase_33/admin/admin_cloud_connectors_dashboard.spec.ts --debug
```

### Common flags

| Flag | Effect |
|------|--------|
| `--reporter=list` | Linear list output (recomendado terminal) |
| `--reporter=json` | JSON summary for CI/scripts |
| `--reporter=html` | Interactive HTML report (open post-run) |
| `--workers=2` | Parallel workers (config default `fullyParallel: false`) |
| `--debug` | Pause + inspect (PWDEBUG=1) |
| `--ui` | Interactive UI mode |
| `--retries=1` | Retry flaky tests (default 0) |
| `--list` | List tests sin ejecutar (verify spec discoverable) |
| `--grep "pattern"` | Run only matching test names |

## Troubleshooting

### `Executable doesn't exist at .../chromium_headless_shell-XXXX/...`

Playwright version updated · old browsers expired. Fix:

```bash
npx playwright install chromium
```

### `_dev/create-test-client devolvió 404`

Backend running con `APP_ENV=production`. Endpoint env-gated. Fix env y restart backend:

```bash
export APP_ENV=development
cd backend && uvicorn app.main:app --reload --port 8000
```

### `webServer timeout · port already in use`

Playwright tries to start `npx next start -p 3100` pero algo ya escucha 3100. Fix:

```bash
# Option A · kill existing
pkill -f "next start"

# Option B · let Playwright reuse (config tiene reuseExistingServer: !process.env.CI)
# Verify config: frontend/playwright.config.ts:25
```

### WSL/Windows tests fallan timeout silenciosamente

Suele ser interop overhead. Probar:

```bash
# Increase timeout:
PLAYWRIGHT_TIMEOUT=60000 npx playwright test ...

# Or use Linux native node (Opción A install)
```

### `globalSetup failed`

`_helpers/global-setup.ts` no pudo crear test client. Common causes:
1. Backend NO running
2. APP_ENV=production (endpoint gated)
3. DB migrations stale (run `alembic upgrade head`)
4. Port 8000 redirigido por proxy

Override backend URL si necesario:

```bash
export PLAYWRIGHT_BACKEND_URL=http://localhost:18000
npx playwright test ...
```

## Cross-ref

- LECCIÓN-OPS-049 · ARTIFACT notation aspirational debt risk (specs vs reality)
- LECCIÓN-OPS-050 · E2E validation requires environment setup completo
- `frontend/playwright.config.ts` · canonical config
- `frontend/tests/e2e/_helpers/global-setup.ts` · pre-test test client creation
