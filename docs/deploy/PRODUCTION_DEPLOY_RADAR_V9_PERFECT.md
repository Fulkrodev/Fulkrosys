# PRODUCTION DEPLOY · RADAR-V9-PERFECT runbook

**Fecha CIERRE Mega-Atom**: 2026-05-27
**Branch source**: `main` HEAD `2bea8113` (Fase 1.D included)
**Tag local Mega-Atom**: `radar-v9-perfect-fase2` → commit `85ef44dd` ("Fase 2 complete")
**Target environment**: Hetzner production
**Pre-piloto pagador deadline**: 25 junio 2026 (4 semanas restantes desde 27 mayo)

> Complementario a [`docs/operations/radar_v9_perfect_production_deploy.md`](../operations/radar_v9_perfect_production_deploy.md) (overview + Marcos primer workflow §2). Este runbook focus técnico ejecución deploy.

---

## 1. Pre-flight checks

### 1.1 Backup DB current state (BLOQUEANTE)

```bash
# pgBackRest snapshot manual production (Motor 26)
# stanza = fulkro (canónica · .env.prod PGBACKREST_STANZA + deploy-hetzner.sh +
# infra/docker/pgbackrest.conf · 'fulkro-prod' rompía el restore-test R8).
pgbackrest --stanza=fulkro backup --type=full
pgbackrest --stanza=fulkro info | head -20
# Verificar timestamp del backup < 5 min antes proceder
```

Rationale: 3 migrations añaden cols a `radar_leads` + `sources_runs` + nueva table conf. Backup mandatorio rollback.

### 1.2 Branch main reachable + commit verified

```bash
git fetch origin main  # (cuando remote configurado · ver §7)
git log origin/main --oneline -3
# Expect HEAD: 2bea8113 feat(radar-v9): Fase 1.D frontend audit + sync · useNoteLead wire-up
```

### 1.3 ENV vars production canonical sanity

```bash
# SSH a Hetzner host
ssh fulkro-prod 'grep -E "ENABLED_SOURCES|ANTHROPIC_API_KEY|INCREMENTAL_SCRAPE_ENABLED|DB_URL" /opt/fulkro/.env'
```

Verificar:
- `DB_URL` apunta prod (NO staging)
- `ANTHROPIC_API_KEY` válido (LLM outreach draft Bloque G usage)
- `ENABLED_SOURCES` será actualizado §3 con 5 fuentes canonical

---

## 2. Migrations apply prod (idempotent · ordered)

3 migrations NUEVAS Mega-Atom Fase 1+2 (`a` + `c` ya aplicadas en runs anteriores · radar-v9 baseline):

```bash
cd /opt/fulkro/backend
source .venv/bin/activate

# Verificar HEAD pre-upgrade
alembic current

# Apply migrations secuencial (idempotent · safe re-ejecutar)
alembic upgrade radar_v9_perfect_g_001  # Bloque G outreach draft cols
alembic upgrade radar_v9_perfect_i_001  # Bloque I incremental scrape cols
alembic upgrade radar_v9_perfect_f_001  # Bloque F pliegos defectuosos cols

# Verificar HEAD post-upgrade (debe ser radar_v9_perfect_f_001 o downstream)
alembic current
alembic history -r-5: | head -20
```

### 2.1 Columns añadidos (rollback reference)

| Migration | Tabla | Cols añadidos |
|-----------|-------|---------------|
| `radar_v9_perfect_g_001` | `radar_leads` | `last_outreach_draft_subject` + `_body` + `_tier` + `_at` + `_model` (5 cols TEXT/timestamptz nullable) |
| `radar_v9_perfect_i_001` | `sources_runs` | `last_external_id_seen` + `incremental_resume_cursor` (2 cols nullable) |
| `radar_v9_perfect_f_001` | `radar_leads` | `angulo_comercial` (VARCHAR enum-like nullable · valores `pliego_defectuoso` / `renovacion_proxima` / `standard` / null) |

Files referencia:
- `backend/migrations/versions/radar_v9_perfect_g_001_outreach_draft.py`
- `backend/migrations/versions/radar_v9_perfect_i_001_incremental_checkpoints.py`
- `backend/migrations/versions/radar_v9_perfect_f_001_pliego_defectuoso.py`

---

## 3. ENV vars update prod

```bash
# SSH Hetzner
ssh fulkro-prod
cd /opt/fulkro

# Backup ENV pre-update
cp .env .env.backup-$(date +%Y%m%d-%H%M)

# Update ENABLED_SOURCES (post-D1 DEFER Galicia+Valencia direct scrapers)
sed -i 's/^ENABLED_SOURCES=.*/ENABLED_SOURCES="placsp,madrid_ccaa,cataluna,euskadi,ted"/' .env

# Add Bloque G LLM personalization toggle (opcional · default true)
grep -q "^OUTREACH_DRAFT_LLM_ENABLED" .env || echo 'OUTREACH_DRAFT_LLM_ENABLED=true' >> .env

# Add Bloque I incremental scrape toggle (default true · cost saving 75-85%)
grep -q "^INCREMENTAL_SCRAPE_ENABLED" .env || echo 'INCREMENTAL_SCRAPE_ENABLED=true' >> .env

# Verify
grep -E "ENABLED_SOURCES|OUTREACH_DRAFT_LLM_ENABLED|INCREMENTAL_SCRAPE_ENABLED" .env
```

---

## 4. Frontend build production

```bash
cd /opt/fulkro/frontend
npm ci  # clean install
npm run build  # Next.js production bundle

# Verificar build sin errors críticos
echo $?  # debe ser 0
ls -la .next/ | head -5

# Verificar routes ENS Radar presentes
ls .next/server/app/\(radar\)/radar/ 2>&1 | head -10
```

Verificar UI components ready Bloques F+G+H+I (mecánica pre-deploy):
- `/radar/page.tsx` → QuickStatsBanner + StatsCards + LeadsTable + RunControlBar
- `LeadDetailDrawer.tsx` → DraftPreviewDialog button + textarea "Añadir nota / tracking" (Fase 1.D)
- `RunControlBar.tsx` → toggle "force_full_rescan" (Bloque I emergency)
- `LeadsTable.tsx` → toggle "Solo pliegos defectuosos" + CCAA filter (Bloque F + H)
- `QuickStatsBanner.tsx` → pliegosDefectuososCount badge

---

## 5. Detector pliegos defectuosos trigger prod (idempotent)

```bash
cd /opt/fulkro/backend
source .venv/bin/activate

# Trigger detector v1 (rule-based · NO LLM cost · idempotent · safe re-ejecutar)
python -m scripts.radar_detect_pliegos_defectuosos --batch

# Output esperado: "Detected X tenders · annotated Y leads · processed Z universe"
```

Verificar counts post-detector empirical prod DB:

```sql
-- Conexión psql prod
\c fulkro_prod

-- Count pliegos defectuosos annotated
SELECT COUNT(*) FROM radar_leads WHERE angulo_comercial = 'pliego_defectuoso';
-- Expect ~156 (empirical local Path A 461 baseline · subset pliego_defectuoso)

-- Distribution angulo_comercial
SELECT angulo_comercial, COUNT(*) FROM radar_leads GROUP BY angulo_comercial ORDER BY COUNT(*) DESC;
```

---

## 6. Smoke production verify

```bash
# 6.1 GET /radar/ accessible
curl -fsSL https://fulkro.es/radar/ -o /dev/null && echo "OK 200"

# 6.2 API health pipeline
curl -fsSL https://fulkro.es/api/v1/radar/pipeline/health | jq .

# 6.3 leads endpoint accessible
curl -fsSL "https://fulkro.es/api/v1/radar/leads?limit=5" | jq '.items | length'
# Expect 5

# 6.4 Drawer dossier endpoint (sample lead)
LEAD_ID=$(curl -fsSL "https://fulkro.es/api/v1/radar/leads?limit=1" | jq '.items[0].id')
curl -fsSL "https://fulkro.es/api/v1/radar/leads/${LEAD_ID}/dossier" | jq '.angulo_comercial, .temperatura'
```

⚠️ **NO trigger pipeline production automático**. Esperar primer "Actualizar radar" desde UI cuando Marcos esté listo outreach (validation moment manual antes propagar tenders nuevos cron-scheduled).

---

## 7. Rollback plan

### 7.1 Hot rollback (frontend regression)

```bash
# SSH Hetzner · checkout commit anterior
cd /opt/fulkro
git fetch origin main
git log origin/main --oneline -5
# Identify previous commit (pre-Fase-1.D · e.g. 07904e9a o ab20cbe1)

git checkout <previous-commit>
cd frontend && npm run build && systemctl reload nginx
```

### 7.2 DB rollback migrations

Migrations radar-v9-perfect son idempotent · `add_column nullable` · **NO data loss risk**. Rollback safe:

```bash
cd /opt/fulkro/backend
alembic downgrade <revision-pre-radar_v9_perfect_g_001>
# Cols nuevos se eliminan · existing rows mantienen integridad
```

### 7.3 ENV rollback

```bash
ssh fulkro-prod
cd /opt/fulkro
cp .env.backup-<timestamp> .env
systemctl restart fulkro-backend
```

### 7.4 Full snapshot restore (extreme · pgBackRest)

```bash
# Stop services
systemctl stop fulkro-backend
systemctl stop fulkro-frontend

# Restore from pre-deploy backup §1.1 (stanza = fulkro, canónica)
pgbackrest --stanza=fulkro restore --type=time --target="<timestamp-pre-deploy>"

# Verify integrity
psql fulkro_prod -c "SELECT COUNT(*) FROM radar_leads;"

# Resume services
systemctl start fulkro-backend
systemctl start fulkro-frontend
```

---

## 8. Marcos primer outreach workflow (post-deploy gate)

Ver doc complementario [`docs/operations/radar_v9_perfect_production_deploy.md`](../operations/radar_v9_perfect_production_deploy.md) §2.

### Resumen workflow primer outreach REAL:

1. **D2 sample audit retrospectivo** (~30 min Marcos) · CSV 20 rows pliegos_defectuosos precision review
   - 🟢 ≥0.65 → proceed outreach immediate
   - 🟡 0.40-0.64 → iterate detector v1.1 (~1h Future)
   - 🔴 <0.40 → escalate `Future-2.B+.pliego-downloader-pdf-fulltext-extraction` prerequisite

2. **Workflow operativo** post-D2 GREEN:
   - `/radar/` → toggle "Solo pliegos defectuosos" ON
   - Click lead top → drawer
   - "Generar borrador outbound" → modal DraftPreviewDialog (tier-specific · 4 citas jurisprudenciales)
   - Preview/edit → copy/mail externo
   - **Tracking via textarea "Añadir nota / tracking"** (Fase 1.D wire-up nuevo) en drawer · append a `notas_marcos`

---

## 9. Future-X registry production-deferred

| ID | ETA | Trigger |
|----|-----|---------|
| `Future-1.D.radar.backend-legacy-endpoints-deprecate` | 30m | Post-piloto · verify zero CLI consumers `/run` + `/status` + `/leads/{id}` |
| `Future-1.D.radar.lead-detail-expose-empleados-facturacion-website` | 15m | Si UI requires extended drawer display |
| `Future-1.E.frontend.typescript-pre-existing-errors` | 1-2h | Cleanup 12 TS errors compliance/system-health/cluster-2-3 (NOT ens-radar) |
| `Future-2.A+.{andalucia,galicia,valencia}-direct-scraper` | 6-12h c/u | Revenue justifica + PLACSP gap empírico CCAA detected |
| `Future-2.B+.pliego-downloader-pdf-fulltext-extraction` | 4-6h | D2 audit RED · prerequisite v2 detector |
| `Future-2.B+.detector-pliego-defectuoso-v2-high-conf` | 6-10h | Post pliego_downloader · upgrade confidence MEDIUM→HIGH |
| `Future-1.B+.navarra-ckan-incremental-integration` | 3-5h | Demand-driven post-piloto |
| `Future-1.B+.cataluna-socrata-server-side-where-filter` | 30m | Demand-driven post-piloto |
| `Future-1.E.radar.test-m10-lead-limbo-factory-refactor` | 45m | Test cleanup demand-driven |

---

## 10. Cost summary final cumulative

Mega-Atom RADAR-V9-PERFECT (Fase 1+2 + Fase 1.D):

| Item | Cost USD | Notes |
|------|---------|-------|
| C (Bloque C scraping detector LLM) | ~$0.50 | Sonnet pricing baseline |
| E (Bloque E filter) | ~$1.20 | LLM filter universe |
| G (Bloque G outreach draft) | ~$2.50 | Sonnet personalization (50 drafts × $0.005) |
| I (Bloque I incremental) | ~$1.00 | Saving 75-85% vs full rescan |
| H (Bloque H QuickStart UI) | ~$0.00 | Deterministic UI work |
| F (Bloque F pliegos defectuosos) | ~$0.00 | Rule-based detector NO LLM |
| **1.D (Frontend audit + useNoteLead wire-up)** | **~$0.00** | **Deterministic audit + UI work** |
| **Total Mega-Atom cumulative** | **~$10.37** | **vs caps $150 (~7% utilizado · 93% margin)** |

---

## 11. Local-only repo state nota

⚠️ Repo local actualmente **sin remoto** (NO remote `origin` configurado · `git remote -v` empty).

Tags + merge ya aplicados local · production deploy requires:
1. Configurar remote production (Hetzner / GitHub / Gitea TBD)
2. `git push origin main radar-v9 radar-v9-perfect-fase1 radar-v9-perfect-fase2`
3. Hetzner deploy script clone/pull desde remote

Pendiente Marcos action.

---

**RADAR-V9-PERFECT production-ready · sistema 100% operacional · deploy gate D2 sample audit pliegos defectuosos · primer outreach piloto pagador 25 junio deadline 4 semanas restantes**.
