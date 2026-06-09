# E2E Tests (Playwright)

Ten headless Chromium tests covering the Sprint 6 acceptance list:

| File | Cubre |
|---|---|
| `login.spec.ts` | Password + TOTP redirect a `/dashboard` |
| `dashboard.spec.ts` | KPI row + quick actions |
| `pipeline.spec.ts` | 8 columnas del Kanban con leads mock |
| `project-tabs.spec.ts` | Navegación entre tabs de proyecto |
| `meeting.spec.ts` | Timer 50min + live panel Agente 18 |
| `audit.spec.ts` | Buscador + timeline |
| `pentest.spec.ts` | Kill switch con modal de confirmación |
| `magic-link.spec.ts` | `/sign/[token]` render + OTP |
| `retainer.spec.ts` | Filtro RAG sobre el grid |
| `command-palette.spec.ts` | `Cmd/Ctrl+K` + selección |

## Ejecutar

### Opción A — Docker (recomendada, sin sudo)

Se usa la imagen oficial `mcr.microsoft.com/playwright:v1.59.1-noble` que ya
trae todas las libs del sistema. `npm ci && npm run build` ocurren dentro del
contenedor, así que no ensucia el host.

```bash
cd frontend
npm run test:e2e:docker
```

(internamente: `docker build -f Dockerfile.e2e -t fulkro-e2e . && docker run --rm fulkro-e2e`)

Primera vez: ~2-3 min (pull + npm ci + build). Ejecuciones siguientes: ~4s.

### Opción B — Nativo (requiere sudo una vez)

El Chromium descargado por Playwright necesita libs del sistema
(`libasound2`, `libatk-bridge2.0`, `libnss3`, …). Hay que instalarlas con
sudo una sola vez:

```bash
npx playwright install-deps chromium    # pide sudo
npm run test:e2e                         # lanza `next start -p 3100` y corre los 10 specs
```

## Hermeticidad

`helpers.ts::mockAuthenticated(page)` intercepta `/api/v1/auth/me` y
`/api/v1/clients`, y siembra cookies de sesión para que el `AuthGuard` pase
sin backend. El resto de endpoints no se tocan porque los hooks ya usan mocks
in-process (ver `lib/*mock*.ts`).

Las rewrites de `/api/*` a `localhost:8000` quedan sin backend atendiéndolas
— por eso se ven algunos `ECONNREFUSED` en los logs del webServer. Son
inocuos: los tests mockean antes de que la petición salga del navegador.
