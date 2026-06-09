# SAN-D Performance Audit Baseline · MB-19.17

**Fecha**: 2026-05-07
**Status**: Baseline documentado · load test ejecución real diferida SAN-E.4
**Refs**: ADR-043 · ADR-044 · MB-19.17

═══════════════════════════════════════════════════════════════

## Contexto

SAN-D operativo desde dev environment local · cero clientes reales pre-Sesión 12
deploy. Performance audit MB-19.17 documenta:

1. **Baseline metodológico** · escenarios de carga representativos
2. **Acceptance criteria** · p95 < 500ms · p99 < 1s endpoints CRUD · SSE < 2s
3. **Optimizations identificadas** · NO aplicadas · documentadas para SAN-E.4
   (post-baseline cliente real piloto · ajustar prioridades feedback)

Decisión arquitectónica: **NO load testing real pre-cliente piloto**. Sin
datos representativos de uso real · benchmarks artificiales sub-estiman
patterns reales (concurrencia + caching cold/warm + N+1 queries específicas
flow real). Baseline empírico SAN-E.4 con cliente real.

═══════════════════════════════════════════════════════════════

## Metodología

### Stack benchmarking propuesto SAN-E.4

| Tool | Uso | Justificación |
|------|-----|---------------|
| **locust** | Load testing endpoints HTTP | Python-native · usa fixtures pytest existing · scripts Python reutilizables |
| **pytest-benchmark** | Micro-benchmarks unit-level | Detección N+1 queries · regression suite |
| **sqlalchemy_explain** | Query plan analysis | Identificar slow queries Postgres post-baseline |
| **Sentry APM** | Production tracing | Post-deploy Sesión 12 · trace real client flows |

### Escenarios target (acceptance criteria · pendientes ejecución SAN-E.4)

#### Escenario 1 · 10 clientes simultáneos · 5 tasks pending each

```
Setup: 10 ClientUsers + 10 Projects + 50 ClientTasks (5/project · status=pending)
Load: 10 concurrent users hitting /client-portal/tasks endpoint
Duration: 5 min steady-state
Acceptance:
  - p95 < 500ms GET /client-portal/tasks
  - 0 errors 5xx
  - DB query time < 100ms p95
```

#### Escenario 2 · 100 magic-links smoke (firma OTP + descarga)

```
Setup: 100 MagicLinks generated (50 FIRMA_DOCUMENTO + 50 DESCARGA_DOSSIER_FINAL)
Load: 100 sequential consume requests (real OTP correct)
Acceptance:
  - p95 < 800ms POST /magic-links/consume (incluye Ed25519 verify + OTP hash + audit log)
  - 100% success rate
  - 0 OTP rate limit accidental (max_uses respected)
```

#### Escenario 3 · Bulk evidencias upload 200 files

```
Setup: 200 evidencias files 1-5MB each
Load: 50 concurrent uploads (4 workers · 50 files each batch)
Acceptance:
  - p95 < 5s POST /client-portal/evidencias (incluye virus scan + storage write)
  - 0 file corruption (SHA-256 verify post-upload)
  - 0 RLS leaks cross-project
```

#### Escenario 4 · SSE 50 connections concurrent

```
Setup: 50 admin Marcos sessions + 1 project with active SSE stream
Load: 50 concurrent /api/v1/stream/projects/{id} connections
Duration: 60s steady · trigger 10 alerts during window
Acceptance:
  - SSE latency < 2s alert dispatch → all clients receive
  - 0 dropped connections (heartbeat keep-alive)
  - DB connection pool no exhaustion (max_connections respected)
```

#### Escenario 5 · WebSocket chat 20 threads concurrent

```
Setup: 20 ChatThreads with active client+admin participants
Load: 20 concurrent message sends + 20 concurrent reads
Acceptance:
  - p95 < 300ms POST /client-portal/chat/messages
  - Realtime delivery < 500ms (WebSocket push)
  - 0 message ordering issues (causality preserved)
```

═══════════════════════════════════════════════════════════════

## Acceptance criteria global

| Endpoint type | p95 target | p99 target | Notas |
|---------------|:----------:|:----------:|-------|
| CRUD endpoints (`GET /projects/...`) | 500ms | 1s | Cache TanStack 30s mitiga UI |
| Scoring/dashboard (`GET /projects/{id}/dashboard`) | 1s | 2s | Aggregation queries · cache Redis MB-20+ |
| Magic-link consume | 800ms | 1.5s | Incluye Ed25519 + OTP + audit |
| File upload (evidencias) | 5s/MB | 10s/MB | Virus scan + storage |
| SSE alert dispatch | 2s | 3s | Lag aceptable Marcos UX |
| Chat message send | 300ms | 500ms | Realtime cliente |

═══════════════════════════════════════════════════════════════

## Optimizations identificadas (NO aplicadas · diferidas SAN-E.4)

### Optimization 1 · Redis caching layer endpoints frecuentes

**Diferido** · DEC-MB13-CACHING-LAYER-REDIS · MB-20+

Endpoints con alto refetch rate desde frontend:
- `GET /projects/{id}/dashboard` (TanStack refetchInterval 30s)
- `GET /projects/{id}/alerts` (refetchInterval 60s · ActiveAlertsCard)
- `GET /projects/{id}/recent-activity` (refetchInterval 60s · RecentActivityCard MB-19.16)

**Estrategia post-SAN-E.4**: Redis cache 15s TTL keyed by (project_id, client_id) ·
invalidación on mutation. Esperado: -50% DB queries, -30% p95 latency.

### Optimization 2 · N+1 queries detection batch lookup

**Identificado MB-19.16 cosecha A** · `_label_for_action` user_email_map ya
implementa batch lookup ClientUser email · pattern reutilizable.

**Sites a auditar SAN-E.4**:
- ProposalService.list_proposals · puede tener N+1 si itera per project
- LeadService.list_pipeline · lazy loading lead_stage_history (MB-19.A)
- ChatService.list_messages · asocia ClientUser per message

**Estrategia**: sqlalchemy_explain en pytest fixture · detectar queries con
N executes anidados. Convertir a batch lookup con `selectinload`.

### Optimization 3 · Postgres indices avanzados

**Identificado**: queries CRM kanban (`list_pipeline filter estado_contacto`)
beneficiarían de partial index:

```sql
CREATE INDEX ix_leads_active_stage
  ON leads (estado_contacto, fecha_ultima_actualizacion DESC)
  WHERE estado_contacto NOT IN ('ganado', 'descartado', 'no_interesa');
```

**Estrategia post-SAN-E.4**: añadir migration con partial indices después de
EXPLAIN ANALYZE confirme query plan suboptimal con datos reales.

### Optimization 4 · CDN edge caching estáticos frontend

**Diferido** · Cloudflare gratis tier o equivalente

Next.js generated static pages (44+) servidos por nginx en Hetzner CPX21 ·
edge cache reduce TTFB Madrid → cliente Spain ~50-100ms.

**Estrategia Sesión 12+**: configurar Cloudflare proxy + cache static assets ·
NO cache `/api/v1/*` endpoints (auth-sensitive).

### Optimization 5 · Database connection pool tuning

**Identificado**: SQLAlchemy default `pool_size=5 · max_overflow=10` puede ser
insuficiente bajo carga 50+ SSE concurrent (Escenario 4).

**Estrategia SAN-E.4**: ajustar `pool_size=20 · max_overflow=40` post-baseline
real · monitor pool exhaustion via Sentry/Datadog.

### Optimization 6 · Asset images compression + lazy loading

**Identificado MB-17 ProjectCategoryBanner**: iconos lucide rendered sin
lazy loading. NextImage usado para client logos pero sub-óptimo.

**Estrategia post-baseline**: convertir bundle frontend con `next/image`
optimization + Cloudflare image transformations (resize · webp).

### Optimization 7 · Bulk operations evidencias

**Diferido** · DEC-MB14-BULK-OPERATIONS · post-SAN-D

Frontend `/client-portal/evidencias` upload one-at-a-time. Bulk multi-file
upload reduciría overhead virus scan invocation per-file.

**Estrategia post-baseline**: batch endpoint POST /evidencias/batch · 1 virus
scan call con N files · 1 storage transaction.

═══════════════════════════════════════════════════════════════

## Performance baseline actual (dev environment)

### Suite backend execution time (3505 tests)

```
$ time pytest backend/tests --ignore=backend/tests/agents -m "not llm" -q
...
3505 passed, 6 skipped, 8 deselected · ~190s wall time
```

**Análisis**: 190s para 3505 tests = ~54ms per test incluyendo setup/teardown
DB. Coherente con TestRunner estándar SQLAlchemy async + Postgres real.

### Frontend build time

```
$ time npm run build
...
✓ Compiled successfully · 44 pages · ~30s
```

**Análisis**: 30s build time aceptable para CI/CD pipeline · target Sesión 12
deploy < 60s incluyendo Docker build layer.

### tsc check

```
$ time npx tsc --noEmit
...
0 errors · ~5s
```

**Análisis**: tsc strict mode + project references reducen incremental
compile time. Pre-commit hook viable.

═══════════════════════════════════════════════════════════════

## Recomendaciones SAN-E.4

### Prioridad alta · pre-100 clientes

1. **Sentry APM configured** (Sesión 12) · trace real query patterns
2. **Redis caching layer** endpoints `/dashboard` + `/alerts` + `/recent-activity`
3. **N+1 queries audit** via sqlalchemy_explain fixture pytest
4. **Connection pool tuning** post-baseline real

### Prioridad media · 50-100 clientes

5. **Partial indices** Postgres queries CRM kanban + retainer
6. **CDN edge caching** Cloudflare frontend assets
7. **Bundle splitting** frontend (admin vs client-portal · separate chunks)

### Prioridad baja · post-200 clientes

8. **PostgreSQL TDE** (DEC-MB14-ZERO-TRUST · SAN-E.3)
9. **Bulk operations evidencias** (DEC-MB14-BULK · post-SAN-D)
10. **WebSocket chat scaling** Redis pub/sub si concurrent chats > 50

═══════════════════════════════════════════════════════════════

## Conclusión audit MB-19.17

✅ **Baseline metodológico documentado** · 5 escenarios target con acceptance
criteria + 7 optimizations identificadas + recomendaciones priorizadas.

⏳ **Load testing real diferido SAN-E.4** post-cliente piloto · sin datos
representativos benchmarks artificiales sub-estiman patrones reales.

✅ **Acceptance criteria definidos** · p95 < 500ms CRUD · p99 < 1s scoring ·
SSE < 2s · base medición SAN-E.4.

✅ **Performance dev environment aceptable** · suite 190s · build 30s · tsc 5s.

═══════════════════════════════════════════════════════════════

**SIGUIENTE PASO**: SAN-E.4 ejecuta load testing real con cliente piloto
operando · ajusta acceptance criteria + aplica optimizations priorizadas
basadas en data empírica real.
