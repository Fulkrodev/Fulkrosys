# Ejecutable 8 · Pasada 4 · Database + Migrations Deep Dive

## 1. Recuento de migraciones (REAL, empírico)

- **`find backend/migrations/versions -name '*.py' | wc -l` → 210 ficheros** (incluye `__init__`? NO — no hay; cuenta directa de revisiones, excluye `__pycache__`).
- CLAUDE.md declara **160 migraciones** → **discrepancia: +50 ficheros reales (210 vs 160, +31%)**. Cifra stale.

### Nomenclatura observada (dos convenciones coexisten)
- **Hash-prefijo autogenerado** (las más antiguas / SAN-*): `1350b2466202_initial_schema_69_tables.py`, `03fe02eea2ef_*`, `d4f8b2a90001_audit_log_hash_chain_trigger.py`, `e41cd7163c02_add_rls_policies_*`, etc.
- **Slug descriptivo + `_001`** (las más recientes, sesiones 3B / radar-v9): `radar_v9_perfect_f_001_pliego_defectuoso.py`, `audit_log_rls_001.py`, `esignature_canvas_tier1_001.py`, `cluster6_client_mfa_001.py`, `sub_atom_5b_magerit_child_rls_001.py`, `merge_heads_radar_magerit_001_*.py`, `radar_widen_llm_freetext_text_001_*.py`.

### Cronología (extremos reales por Create Date en cabecera)
- **Más antigua**: `1350b2466202_initial_schema_69_tables` — `Create Date: 2026-04-11` · `down_revision = None` · raíz del árbol · crea audit_log, backup_jobs, etc. Se autodescribe "69 tables".
- **Más reciente**: `radar_widen_llm_freetext_text_001` — `Create Date: 2026-05-30` (head único actual) · ensancha `radar_leads.persona_contacto_sugerida`/`canal_sugerido` + `companies.sector` de String(N)→Text por crash StringDataRightTruncation en run a3897135 paso dossier.
- Rango temporal: **~2026-04-11 → 2026-05-30** (≈7 semanas).

## 2. Configuración Alembic (`backend/migrations/env.py`)

- `target_metadata = Base.metadata`, importando `backend.app.models` (paquete) y `backend.app.models.base.Base`.
- Usa `DATABASE_MIGRATE_URL` (rol privilegiado p/ migraciones · convierte `postgresql+asyncpg://`→sync `postgresql://`).
- `include_object` excluye del autogenerate: 3 índices FTS GIN (`ix_client_contacts_notes_fts`, `ix_client_messages_body_fts`, `ix_exploratory_meetings_notes_fts`) y 2 tablas sin ORM (`audit_schedules`, `ens_iso27001_mapping` — creadas solo por SQL raw, no en Base.metadata).

## 3. Estado del árbol Alembic (heads / merges)

**Verificado con `alembic heads` vía venv WSL (`/home/usuario/fulkro/.venv/bin/python -m alembic heads`):**

```
radar_widen_llm_freetext_text_001 (head)   ← UN SOLO HEAD
```

El árbol de SCRIPTS ya está **consolidado a head único**. Estructura del tangle resuelta (de `alembic history`):

- **Mergepoint 1** — `merge_heads_radar_magerit_001` (DDL vacío, merge puro):
  `Revises: radar_recert_001, sub_atom_5b_magerit_child_rls_001`
- **Mergepoint 2** — `sub_atom_5b_magerit_child_rls_001` consolida **3 heads previos**:
  `Revises: cluster6_client_mfa_001, radar_v9_perfect_f_001, remediation_enhancement_b35_e_001`
- **Branchpoints**: `copilot_rls_client_isolation_001` (→ audit chain + radar_v9_perfect_c) y `s3b2b4_copilot_client_id_001`.
- `alembic history | grep -ciE 'mergepoint|branchpoint'` → **5** puntos de bifurcación/merge.

Tras el merge: `…sub_atom_5b… → merge_heads_radar_magerit_001 → radar_widen_sector_text_001 → radar_widen_llm_freetext_text_001 (head)`.

### Deuda documentada en los propios merge files
Revision ids de hasta **33 chars** (`sub_atom_5b_magerit_child_rls_001`, `remediation_enhancement_b35_e_001`) superan el **VARCHAR(32) por defecto** de `alembic_version.version_num`. El merge resuelve la ambigüedad de cabezas pero **NO el ancho**; un `alembic upgrade head` limpio (Hetzner) requiere primero ensanchar la columna → `Future-1.E.radar.alembic-version-num-widen`. En dev los cambios radar_widen se aplicaron por **DDL directo** (docstrings lo afirman explícitamente), no vía Alembic.

## 4. Estado BD live (REAL · docker `fulkro-postgres-1`, puerto 5433)

`docker ps` → contenedores: `fulkro-postgres-1`, `fulkro-redis-1`, `fulkro-minio-1`, `fulkro-clamav-1`, `fulkro-fulkro-scanner-1`.

**`SELECT version_num FROM alembic_version;` → 3 FILAS (estado multi-head EN LA BD):**
```
cluster6_client_mfa_001
radar_v9_perfect_f_001
radar_recert_001
```

> **DESALINEACIÓN clave**: el árbol de scripts tiene 1 head consolidado, pero la BD live sigue stampeada en **3 revisiones pre-merge antiguas**. La BD va POR DETRÁS: ni los 2 mergepoints ni la cadena `radar_recert_001 → … → radar_widen_llm_freetext_text_001` están aplicados vía Alembic (los ALTER radar_widen se metieron por DDL directo). Tercer head BD `radar_recert_001` no coincide con ningún tip esperado de los 3 que consolidó sub_atom_5b — confirma drift histórico del tangle.

- **Tablas públicas**: `SELECT count(*) … table_schema='public'` → **248 tablas** (incluye `alembic_version`).
- **Columnas públicas**: `SELECT count(*) … information_schema.columns` → **3645 columnas**.
- CLAUDE.md declara **~184 tablas live** → **discrepancia: +64 tablas (248 vs ~184, +35%)**. Cifra stale.

### Muestra de tablas live (248 total, orden alfabético, extracto)
`a21_discrepancies, a21_scan_runs, admin_settings, aepd_notifications, ai_act_transparency_events, alembic_version, alert_queue, applied_safeguards, archived_projects, assets, audit_accompaniment_{artifacts,state,transitions}, audit_log, auditor_annotations, auditor_clarification_requests, auth_users, auth_webauthn_credentials, ccn_certificados, chat_messages, chat_threads, client_users, cloud_connectors, cloud_gaps, cloud_resources, companies, copilot_conversations, dda_entries, evidence, evidence_requests, leads, magerit_assets (+11 magerit_*), notification_events, projects, providers, radar_leads, radar_pipeline_runs, signing_events, signing_intents, tenders, whatsapp_messages, workspace_chat_messages, …`

## 5. Modelos ORM (REAL)

- **`find backend/app -name 'models.py'` → 11 ficheros** dispersos por motor:
  m30_client_contacts, m_observability, m_cloud_connectors, m29_client_messaging, m05_signing, m08_verification, m31_whatsapp, m10_ens_radar/db, m02_magerit, m_audit_accompaniment, core/feature_flags.
- **`backend/app/models/*.py` → 58 ficheros** (paquete central que env.py importa): a21_discrepancies, admin, aepd, alerts, audit_log, auth, base, bia, billing_milestones, change_governance, client_portal, commercial, communication, copilot, core, diagnosis, discovery, documents, ens, evidence_request, findings, governance, idms, invoices_aapp, knowledge, lifecycle, live_record, lms, m14_providers, m25_exit_checklist, m27_renewal_milestone, m28_role_assignment, notifications, onboarding, operations, pkg, planning, retainer, ropa_treatments, … (+más).
- **Total ficheros model-related** (`-path '*models*'`): **76**.
- CLAUDE.md declara **52 archivos modelos ORM** → cercano a los 58 de app/models pero no exacto; con los 11 dispersos por motor el total real difiere. Cifra parcialmente stale.

## 6. Discrepancias vs cifras stale CLAUDE.md

| Métrica | CLAUDE.md (stale) | REAL empírico | Δ |
|---|---|---|---|
| Migraciones Alembic | 160 | **210** | +50 (+31%) |
| Tablas live PostgreSQL | ~184 | **248** | +64 (+35%) |
| Archivos modelos ORM | 52 | **58** en app/models / **76** model-related / **11** models.py | +6 a +24 |
| Heads Alembic (scripts) | n/d | **1** (`radar_widen_llm_freetext_text_001`) | — |
| alembic_version en BD | n/d | **3 filas** (pre-merge) | drift |
| Columnas públicas | n/d | **3645** | — |

## 7. Conclusión empírica

El esquema de producción local es **considerablemente mayor** que lo declarado (248 tablas / 210 migraciones vs 184/160 en CLAUDE.md → ambas cifras stale ~+30/35%). El árbol de migraciones **YA fue saneado a un head único** mediante 2 mergepoints (`merge_heads_radar_magerit_001` + `sub_atom_5b_magerit_child_rls_001`), pero la **BD live no refleja ese estado**: permanece stampeada en 3 revisiones pre-merge y la cadena radar más reciente se aplicó por DDL directo. Persiste la deuda `alembic_version VARCHAR(32)→≥64` que bloquea un `upgrade head` limpio en deploy nuevo (Hetzner). Recomendación implícita confirmada por los docstrings: en deploy limpio hay que (a) ensanchar `version_num`, (b) `alembic upgrade head` desde cero contra BD vacía para reproducir los ALTER aplicados manualmente en dev.