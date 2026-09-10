# RADAR-V9-PERFECT · Production Deploy Checklist + Marcos Primer Workflow

**Fecha cierre**: 2026-05-27
**Mega-Atom CIERRE**: tag local `radar-v9-perfect-fase2` → commit `85ef44dd`
**Branch merged**: `radar-v9` (hasta `7852d045` cement) → `main` (merge commit `ab20cbe1`)
**Pre-piloto pagador deadline**: 25 junio 2026 (4 semanas desde 27 mayo)

---

## 1. Production deploy checklist (Hetzner)

### 1.1 Pre-flight

- [ ] `main` branch en remote production (esperando configuración remote · ver §4)
- [ ] Verificar tag `radar-v9-perfect-fase2` apunta commit `85ef44dd` ("Fase 2 complete")
- [ ] CI/CD pipeline verde (tests + lint + typecheck)
- [ ] Backup DB pre-deploy (Motor 26 pgBackRest snapshot manual antes apply migrations)

### 1.2 Migrations Alembic a aplicar prod DB

Aplicar en orden secuencial (3 migrations NUEVAS Mega-Atom Fase 1+2 · `a` y `c` son anteriores ya aplicadas):

```bash
# Desde backend/, asegurar DB_URL apuntando prod
alembic upgrade radar_v9_perfect_g_001  # Bloque G outreach draft cols
alembic upgrade radar_v9_perfect_i_001  # Bloque I incremental scrape cols
alembic upgrade radar_v9_perfect_f_001  # Bloque F pliegos defectuosos cols
```

Verificar HEAD post-upgrade:

```bash
alembic current  # debe mostrar radar_v9_perfect_f_001 (head)
```

Files referencia:
- `backend/migrations/versions/radar_v9_perfect_g_001_outreach_draft.py`
- `backend/migrations/versions/radar_v9_perfect_i_001_incremental_checkpoints.py`
- `backend/migrations/versions/radar_v9_perfect_f_001_pliego_defectuoso.py`

### 1.3 ENV vars production canonical

```bash
# Fuentes radar habilitadas (5 fuentes post-D1 DEFER Galicia+Valencia direct)
ENABLED_SOURCES="placsp,madrid_ccaa,cataluna,euskadi,ted"

# Opcional · LLM outreach draft Bloque G (Sonnet 4.6 personalization ~$0.005/draft)
ANTHROPIC_API_KEY=<existing>
OUTREACH_DRAFT_LLM_ENABLED=true  # set false para skip LLM personalization

# Incremental scrape Bloque I (default true · 75-85% cost saving vs full rescan)
INCREMENTAL_SCRAPE_ENABLED=true
# FORCE_FULL_RESCAN=true  # emergency override flag ONLY si Marcos lo solicita explícito
```

### 1.4 Frontend build deploy

- [ ] Next.js production bundle: `npm run build` en frontend/
- [ ] Verify routes ENS Radar: `/radar/`, `/radar/[id]`
- [ ] Verify drawer outreach: "Generar borrador outbound" CTA presente
- [ ] Verify filter UI: toggle "Solo pliegos defectuosos" + badge `pliego_defectuoso` + stat counter

### 1.5 Post-deploy NO trigger automático

⚠️ **NO trigger pipeline production automático**. Esperar primer "Actualizar radar" desde UI cuando Marcos esté listo outreach (validation moment manual antes propagar tenders nuevos).

### 1.6 Trigger detect_batch pliegos defectuosos prod (idempotent)

```bash
# Ejecutar UNA vez post-deploy para anotar universe existente con detector v1
python -m backend.scripts.radar_detect_pliegos_defectuosos --batch
# Idempotent · safe re-ejecutar · NO LLM cost (rule-based detector)
```

---

## 2. Marcos primer workflow operativo (step-by-step)

### 2.1 Sample audit retrospectivo pliegos_defectuosos (D2 gate · ~30 min)

**ANTES de outreach REAL**, Marcos revisa CSV 20 rows detector v1 sample para validar precision empírica:

```bash
# CSV ya generado en branch radar-v9-perfect-fase2
# Marcos abre · review · score precision
ls -la out/radar_v9_pliego_defectuoso_sample_*.csv
```

**Threshold action post-audit**:

| Precision | Color | Acción |
|-----------|-------|--------|
| ≥ 0.65 | 🟢 GREEN | Outreach immediate · capture audit results |
| 0.40 – 0.64 | 🟡 YELLOW | Iterate detector v1.1 (tighten criteria · ~1h) |
| < 0.40 | 🔴 RED | Escalate · revisit `pliego_excerpt` expansion (requires `Future-2.B+.pliego-downloader-pdf-fulltext-extraction` prerequisite) |

### 2.2 Primer outreach REAL workflow (post-D2 GREEN)

1. Abrir `/radar/` (production URL Hetzner)
2. Filter "Solo pliegos defectuosos" toggle **ON** (filtra universe ~156 leads → subset pliego_defectuoso candidates)
3. Click lead top scoring → abre drawer detalle lead
4. Click CTA "Generar borrador outbound" → opens `DraftPreviewDialog`
5. Preview/edit template generado (tier-specific · 7 templates por tier · 4 citas canonical embedded)
6. Copy → mail client externo (gmail/outlook) → primer outreach REAL al lead
7. Tracking via campo `notas_marcos` en lead detail (workaround pre-piloto · sin tracking automated todavía)

### 2.3 Métricas a observar primeras semanas

- Response rate primer outreach batch (target ≥5% piloto pagador conversión)
- Cost LLM acumulado mes (banner UI Future-X · workaround manual: monitoring usage Anthropic dashboard)
- Detector v1 precision retroactivo (Marcos puede ajustar threshold confidence MEDIUM→HIGH si data warrants)

---

## 3. Future-X registry final (consolidated post-piloto)

### Fase 2 deferred (~32-49h cumulative · demand-driven post-piloto)

| Future-X ID | Estimación | Trigger condition |
|-------------|-----------|-------------------|
| `Future-2.A+.andalucia-junta-direct-scraper-angular-spa` | 6-9h | Revenue justifica + PLACSP gap empírico Andalucía detectado |
| `Future-2.A+.galicia-xunta-direct-scraper` | 8-12h | Same pattern Andalucía + Marcos demand |
| `Future-2.A+.valencia-gva-direct-scraper` | 8-12h | Same pattern Andalucía + Marcos demand |
| `Future-2.B+.pliego-downloader-pdf-fulltext-extraction` | 4-6h | Prerequisite v2 detector · si Marcos D2 audit → RED |
| `Future-2.B+.detector-pliego-defectuoso-v2-high-conf` | 6-10h | Post pliego_downloader · upgrade confidence MEDIUM→HIGH |

### Fase 1 deferred (radar-v9-perfect baseline post-cierre)

- `Future-1.B+.navarra-ckan-incremental-integration` (~3-5h)
- `Future-1.B+.cataluna-socrata-server-side-where-filter` (~30 min)
- `Future-1.E.radar.test-m10-lead-limbo-factory-refactor` (~45 min)

### Operational missing (workarounds primer-outreach)

- Marcar contactado tracking automated (workaround actual: `notas_marcos` manual)
- Cost banner mes UI Anthropic LLM (workaround actual: dashboard Anthropic manual)
- Multi-select filters radar UI (workaround actual: single-select toggle)

---

## 4. NOTA: Repo state local-only (2026-05-27)

⚠️ Repo local **sin remoto** (NO remote `origin` configurado). Plan D3 paso 4 `git push origin ...` NO ejecutable hasta configurar remote production (Hetzner / GitHub / Gitea TBD).

Tags + merge ya aplicados local:
- ✅ Tag `radar-v9-perfect-fase1` (local · commit `10bb96f7`)
- ✅ Tag `radar-v9-perfect-fase2` (local · commit `85ef44dd` · re-pointed from 064571f9 per Marcos opt 2)
- ✅ Merge `radar-v9` → `main` (merge commit `ab20cbe1` · hasta `7852d045` cement)
- ⏳ Push remote pending configuración

Cuando Marcos configure remote:

```bash
git remote add origin <production-remote-url>
git push origin main
git push origin radar-v9-perfect-fase1
git push origin radar-v9-perfect-fase2
git push origin radar-v9  # preserve branch · contains CLUSTER 6 WIP cont.
```

---

## 5. CLUSTER 6 Cliente Portal (parallel scope · NO merged main)

Durante el proceso Mega-Atom CIERRE, sesión paralela Claude Code committed Phases 6B+6C+6D+6E + cluster-6 PATH A CERRADO en `radar-v9` branch tip (post-cement `7852d045`).

**Estado actual radar-v9 tip** (NO merged main · separate scope lifecycle):
- `e0d70833` CLUSTER 6 PATH A CERRADO · cumulative validation 5/5 phases
- `40e424eb` CLUSTER 6 Phase 6E · settings consolidated cliente + admin
- `567d8993` CLUSTER 6 Phase 6D · supervision_mode MINIMAL/SUPERVISED
- `ba06c806` CLUSTER 6 Phase 6C · per-phase task curation R29 friendly
- `b12ef703` CLUSTER 6 Phase 6B · chronological 10-fase timeline sidebar

Próxima sesión CLUSTER 6 puede continuar normal en branch `radar-v9` sin interferir Mega-Atom merged a main. Cuando CLUSTER 6 Cliente Portal Path C complete su propio cierre, merge separado a main.

---

**Mega-Atom RADAR-V9-PERFECT CIERRE FORMAL** · sistema production-ready · operational next phase outreach piloto pagador 25 junio deadline.
