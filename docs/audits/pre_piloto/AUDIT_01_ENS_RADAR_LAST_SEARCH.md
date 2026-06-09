# AUDIT #4 · ENS Radar última búsqueda fallida

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 1/11
**Date**: 2026-05-24
**Methodology**: find/cat/wc/head/tail/ls (NO grep)
**Scope item**: pre-piloto #4 · "ENS Radar última búsqueda fallida · retry visibility"

---

## Verdict empírico

ENS Radar es **infrastructure massive production-grade** (~5000 LOC backend + 9 components frontend portal separado). Pipeline tiene `CancellableRunner` con `PipelineRun` history persisted + UI `RunHistoryTable` muestra histórico runs con metadata cost/status. **Gap específico**: NO existe botón "retry búsqueda fallida" en UI · cada nuevo intento es lanzamiento completo nuevo (no resume from failed step).

**ETA empírico realista refined**: ~2-4h (vs ~5-8h nominal) si se decide implementar retry. Pero **PROBABLE SCOPE-OUT** demand-driven post-piloto: cliente piloto MEDIA NO bloquea con re-launch full · cost $80/run aceptable para retry full.

---

## Stats baseline

### Backend ENS Radar (~5000 LOC)
- `api.py` 815 LOC · 11+ endpoints production
- `orchestrator/pipeline.py` 1622 LOC · pipeline 8 pasos + CancellableRunner
- `orchestrator/runner.py` 196 LOC · cancellation cooperativa
- `service.py` 226 LOC · facade
- `cli.py` 534 LOC · CLI ops
- `schemas.py` 280 LOC · Pydantic in/out
- `sources/*.py` 943 LOC · 6 sources (placsp · madrid · cataluna · euskadi · navarra · ccn_certificates)
- `db/models.py` (PipelineRun + Tender + Lead + RadarLead + SourceRun + ...)

### Frontend ENS Radar portal SEPARADO `/(radar)/`
- `layout.tsx` standalone (NO /admin nested)
- `radar/page.tsx` dashboard
- `radar/runs/page.tsx` histórico paginado (~50 LOC)
- `radar/leads/page.tsx` listado leads
- `radar/clusters/page.tsx` clusters analysis
- Components 9 archivos en `components/ens-radar/`:
  - RunControlBar (lanzar new run + stale aviso 30 días)
  - RunHistoryTable 188 LOC (histórico runs · click row → RunStatusBanner inline)
  - RunStatusBanner (status detail)
  - LeadsTable + LeadDetailDrawer + StatsCards + EmailPreview + TemperatureBadge

### Endpoints existing relevantes failed search
- `POST /api/v1/motors/m10/run` (RunAcceptedResponse 202 · background_task)
- `GET /api/v1/motors/m10/status` (last_run + totals)
- `PATCH /api/v1/motors/m10/leads/{id}/approve|discard|note`
- `GET /api/v1/motors/m10/runs` (likely existing per RunHistoryTable consume)
- **CANCEL**: `PipelineCancelRequest` / `PipelineCancelResponse` schemas existing
- **RETRY**: NO endpoint dedicated retry-from-failed-step empírico

---

## Gap específico identificado

### Failed search visibility (READ)
- ✅ `RunHistoryTable` muestra runs con status (running · pending · completed · failed · cancelled)
- ✅ `RunStatusBanner` inline expand muestra detalle + métricas + cost
- ✅ `PipelineRun` model persists run metadata + per-step state
- 🟡 NO detalle "qué step falló · qué error" surfaced UI explícito (probable backend log only)

### Failed search retry (ACTION)
- 🟡 RunControlBar default "Lanzar nuevo run" desde scratch · NO "Retry failed run X"
- 🟡 NO endpoint `POST /runs/{id}/retry` empírico
- 🟡 NO endpoint `POST /runs/{id}/resume-from-step/N` empírico
- 🟢 Workaround existing: re-launch full run con flags `skip_ingest`/`skip_ens` para skip pasos completados

### Cancellation (ACTION)
- ✅ CancellableRunner backend production
- ✅ PipelineCancelRequest/PipelineCancelResponse schemas
- 🟡 UI cancel button status NOT verified · probable existente RunStatusBanner

---

## Scope refinement post-audit

### Opción A · scope-out PERMANENT (RECOMMENDED pre-piloto)
- Cliente piloto MEDIA NO bloquea con re-launch full
- Cost $80/run aceptable (Marcos approve antes cada launch)
- Workaround `skip_ingest`/`skip_ens` cubre 80% casos
- **ETA: 0h** · Future-1.E.ens-radar-retry-failed-step (post-piloto)

### Opción B · UI polish básico (~2h)
- Add "Status detail" link RunHistoryTable con error message + failed step name
- Add "Re-launch with skip_ingest=true" button shortcut (1-click pre-fill)
- NO new backend endpoint · solo UI improvements
- **ETA: ~2h** post-piloto MEDIA si gap real detected dogfooding

### Opción C · Retry dedicated (~4-6h)
- Backend: NEW `POST /runs/{id}/retry-from-step/{step_name}` endpoint
- ResolverPattern: load PipelineRun state · resume from failed step preserving prior step outputs
- Frontend: NEW retry button RunHistoryTable + step picker
- **ETA: ~4-6h** · scope creep significant · NOT bloquea piloto

---

## Recomendación

**Scope-out PERMANENT pre-piloto** · Opción A · Future-1.E.ens-radar-retry-failed-step capturado para evaluation post-dogfooding cuando Marcos confirma frecuencia real failed runs (probable < 1/mes con sources stable).

**Justification**:
- 0 cliente piloto MEDIA blocker
- Marcos retry workaround existing
- ETA economy ~2-6h vs higher-priority items pre-piloto (cloud remediation #9 · backups #7)

---

## Cross-ref

- M10 source: `backend/app/motors/m10_ens_radar/`
- Frontend portal: `frontend/app/(radar)/radar/`
- Components: `frontend/components/ens-radar/`
- ADR-015 ENS Radar owner-only access
- Cost limit: `utils/cost_limit.py` hard cap $80/run

---

## Honest notes

1. Bash UNC path limita execution real test ENS Radar pipeline · audit static read-only files
2. Falta verify si UI cancel button existe (probable RunStatusBanner pero NO confirmed file-level)
3. PipelineRun model schema NOT inspected en detalle (mtime ago 30 days · audit más profundo demand-driven)
