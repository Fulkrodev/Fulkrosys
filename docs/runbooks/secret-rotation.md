# Secret Rotation Runbook · FULKRO

> Ejecutable 3 Phase 5.4 SUPER MEGA PROMPT re-architected · Sesión 5 base.
> Last updated: 2026-05-27 · Marcos único admin Fulkro 1.0
> Audit baseline: `docs/audits/SUPER_MEGA_PROMPT_AUDIT_BASELINE_2026-05-27.md`

## Purpose

Procedimientos empíricos paso-a-paso para rotación de secretos críticos en producción Hetzner pre-piloto MEDIA cliente. Cubre:
1. Inventario secretos cross-motor
2. Cadencia rotación per categoría (quarterly / immediate post-incident)
3. Procedimiento rotation per categoría (step-by-step empirical)
4. Verificación post-rotation (smoke tests + audit log integrity)
5. Emergency rotation (incident response 1h SLA)

## Doctrinas honored

- ADR-013 doble pool · admin + cliente + auditor portals separate secret scopes
- R6 audit_log inmutable hash chain · NO truncate rotation events
- OPS-049 honest defer · automation Future-X (rotation manual procedure base)

---

## 1. Inventario secretos cross-motor

| Categoría | Secret | Ubicación | Cadencia base | Auto-rotation Future-X? |
|-----------|--------|-----------|---------------|-------------------------|
| **LLM Provider** | `ANTHROPIC_API_KEY` | `.env` + Hetzner secrets | Quarterly | ❌ Manual (Anthropic console) |
| **Database** | `DATABASE_URL` (fulkro_app password) | `.env` | Quarterly | ❌ Manual (psql ALTER USER) |
| **Database** | `DATABASE_MIGRATE_URL` (fulkro_migrate password) | `.env` | Quarterly | ❌ Manual (psql ALTER USER) |
| **Database** | `fulkro` superuser password | `.env` (deployment-only) | Yearly | ❌ Manual · raro usado |
| **Auth** | `APP_SECRET_KEY` (JWT secret · Ed25519 EdDSA) | `.env` | Yearly · OR post-incident immediate | ❌ Manual · breaking change |
| **Signing (M05)** | Ed25519 keypair signing manifests | `keys/ed25519_*.pem` | Yearly · OR post-incident immediate | ⏳ Future-S5.3.secret-rotation-automation-ed25519-keypair-grace-period |
| **WhatsApp (M_whatsapp)** | Dialog360 API key | `.env` `DIALOG360_API_KEY` | Quarterly | ❌ Manual (Dialog360 dashboard) |
| **Email (M20)** | SMTP credentials | `.env` `SMTP_USERNAME` + `SMTP_PASSWORD` | Quarterly | ❌ Manual (mail provider console) |
| **MinIO** | MinIO access/secret keys | `.env` `MINIO_ACCESS_KEY` + `MINIO_SECRET_KEY` | Quarterly | ❌ Manual (MinIO admin console) |
| **Magic Links (M12)** | Ed25519 EC P-256 keypair magic links | `keys/magic_link_*.pem` | Yearly · OR post-incident immediate | ⏳ Same Future-S5.3 |
| **OAuth Cloud** | M365 + Google Workspace OAuth client secrets | `.env` per provider | When provider rotates | ❌ Manual (provider console) |

---

## 2. Cadencia rotación per categoría

### Quarterly (cada 3 meses · default cadencia base)

- LLM provider keys (ANTHROPIC_API_KEY)
- Database role passwords (fulkro_app · fulkro_migrate)
- WhatsApp Dialog360 API key
- SMTP credentials
- MinIO access keys

**Calendar trigger**: First Monday del trimestre (enero · abril · julio · octubre · 09:00 UTC Marcos local).

### Yearly (cada 12 meses · low-rotation cadencia base)

- APP_SECRET_KEY (JWT secret)
- Ed25519 keypair signing (M05)
- Magic link Ed25519 EC P-256 (M12)
- `fulkro` superuser password

**Calendar trigger**: Primer aniversario producción Hetzner deploy (Marcos calendar reminder).

### Immediate (post-incident)

Rotar TODOS los secretos categoría afectada cuando:
- Posible exposure (secret leaked en commit · log · screenshot · DM · email)
- Personal acceso terminated (Marcos único · NO aplica · pero collaborator futuro)
- Provider breach disclosed (Anthropic · Dialog360 · etc post-CVE)
- Audit log gaps detected (Sub-atom 5.A 3-way OR integrity check fails)

---

## 3. Procedimiento rotation per categoría (step-by-step)

### 3.1 ANTHROPIC_API_KEY (LLM provider)

```bash
# Step 1 · Generate NEW key en Anthropic console
# https://console.anthropic.com/settings/keys
# Marcos clicks "Create Key" · copia NEW key (NO close window aún)

# Step 2 · Update .env local (development)
sed -i 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=<NEW_KEY>/' .env

# Step 3 · Verify local backend smoke test
.venv/bin/python -m pytest backend/tests/agents/test_a14_rag.py::test_llm_router_smoke -v

# Step 4 · Deploy update Hetzner (production)
# ssh marcos@hetzner-prod
# cd /opt/fulkro && sudo systemctl edit fulkro-backend.service
# Update Environment="ANTHROPIC_API_KEY=<NEW_KEY>"
# sudo systemctl daemon-reload && sudo systemctl restart fulkro-backend

# Step 5 · Verify production health
curl -fsS https://fulkro.com/api/v1/health
# Trigger 1 LLM call e2e (via copilot smoke endpoint OR Marcos chat)

# Step 6 · Revoke OLD key Anthropic console
# Console settings → Keys → OLD key → Revoke
```

### 3.2 DATABASE_URL (fulkro_app password)

```bash
# Step 1 · Generate strong random password (32 chars · alphanum + symbols)
NEW_PASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
echo "NEW fulkro_app password: $NEW_PASS"

# Step 2 · Apply en Postgres
docker exec fulkro-postgres-1 psql -U fulkro -d fulkro -c \
    "ALTER USER fulkro_app PASSWORD '$NEW_PASS';"

# Step 3 · Update .env local + production deploy ENV
sed -i "s/fulkro_app:[^@]*@/fulkro_app:$NEW_PASS@/" .env

# Step 4 · Restart backend (consume new connection pool)
docker compose restart backend  # OR systemctl restart fulkro-backend prod

# Step 5 · Verify connection pool reconnected
curl -fsS https://fulkro.com/api/v1/health
# Check audit_log latest insert ok (RLS authenticated as fulkro_app)
```

### 3.3 Ed25519 signing keypair (M05)

```bash
# CRITICAL · breaking change · grace-period strategy required Future-X
# Current procedure (manual · post-incident immediate):

# Step 1 · Generate NEW keypair
.venv/bin/python -m backend.app.motors.m05_signing.tools.generate_keypair \
    --output keys/ed25519_new

# Step 2 · DEPLOY old + new keypairs concurrent (grace-period verify)
# Backend reads NEW for sign, OLD + NEW for verify (2-week grace)
# Manual Future-X automation pending

# Step 3 · Re-sign critical artifacts post-grace (DdA documents · MANIFEST.json)
# Use sign-rotation script (manual run · Marcos approve cada batch)
.venv/bin/python -m backend.app.motors.m05_signing.tools.resign_all \
    --old-key keys/ed25519_old --new-key keys/ed25519_new \
    --dry-run  # remove --dry-run after Marcos verify counts match

# Step 4 · Verify hash chain integrity post-rotation
.venv/bin/python -m backend.app.motors.m05_signing.tools.verify_chain
```

### 3.4 Resto categorías (WhatsApp · SMTP · MinIO · OAuth · APP_SECRET_KEY)

Patrón similar quarterly:
1. Generate NEW credential en provider console
2. Update `.env` local + production deploy ENV (systemd Environment OR Hetzner secrets manager)
3. Restart backend service consume new credential
4. Smoke test endpoint relevant (whatsapp send test · smtp send test · minio upload test)
5. Revoke OLD credential provider console

**APP_SECRET_KEY rotation special**: ALL active JWT tokens invalidated post-rotation · cliente sessions logout forced · communicate downtime ventana 5min email cliente pre-rotation.

---

## 4. Verificación post-rotation

Cada rotation debe completarse con verify cumulative:

### 4.1 Smoke tests minimum (5 min)

```bash
# Backend health
curl -fsS https://fulkro.com/api/v1/health

# Auth endpoint (verify APP_SECRET_KEY OK)
curl -fsS -X POST https://fulkro.com/api/v1/auth/csrf-token

# DB connection (verify fulkro_app password OK)
.venv/bin/python -c "from backend.app.database import engine; import asyncio; asyncio.run(engine.connect())"

# LLM smoke (verify ANTHROPIC_API_KEY OK)
.venv/bin/python -m backend.app.core.ai.llm_router --smoke "Hello"
```

### 4.2 Audit log integrity check (R6 sostained)

```sql
-- Verify hash chain inviolable post-rotation
SELECT fn_audit_log_verify_chain();
-- Expected: (valid=TRUE, broken_index=NULL)
```

### 4.3 Rotation event audit_log emit

Cada rotation Marcos debe emit canonical event:

```sql
INSERT INTO audit_log (
    actor_email, tabla, registro_id, accion, payload, timestamp
) VALUES (
    'marcosmata@fulkro.es',
    'security_secrets',
    '<secret-category-id>',
    'rotated',
    jsonb_build_object(
        'category', '<ANTHROPIC_API_KEY|DB_PASSWORD|Ed25519|...>',
        'reason', '<quarterly|post-incident|provider-breach>',
        'verified_smoke_tests', true
    ),
    now()
);
```

---

## 5. Emergency rotation (incident response 1h SLA)

Trigger: secret exposure confirmed (commit leak · log screenshot · DM · email).

### 5.1 Immediate actions (first 15 min)

1. **Revoke leaked secret** en provider console FIRST (NO rotation aún · just kill access)
2. **Audit log emit** incident event:
   ```sql
   INSERT INTO audit_log (...) VALUES (
       '...', 'security_incidents', '...',
       'secret_exposure_detected',
       jsonb_build_object('category', '...', 'exposure_channel', '...'),
       now()
   );
   ```
3. **Notify** stakeholders (if collaborator: email · if cliente impact: Marcos direct call)

### 5.2 Rotation completion (next 45 min)

Follow procedimiento section 3 per categoría · MAX 1h SLA total since detection.

### 5.3 Post-incident actions (24h SLA)

1. **Root cause analysis** docs/incidents/INC-YYYYMMDD-<short-desc>.md
2. **Process improvement** Future-X actionable items (e.g. pre-commit hook block secrets · git-secrets · etc)
3. **Audit log emit** incident closure event

---

## Future-X automation roadmap

Post-piloto demand-driven:

- `Future-S5.4.A.secret-rotation-scheduler-cron-quarterly-reminders` (~1h · Marcos calendar integration)
- `Future-S5.4.B.ed25519-grace-period-dual-key-sign-verify` (~3-4h · keypair rotation no-breaking)
- `Future-S5.4.C.secrets-vault-integration-hashicorp-or-aws-secrets-manager` (~6-8h · centralized secrets)
- `Future-S5.4.D.pre-commit-secrets-leak-detection-git-secrets` (~30 min · prevent leaks at commit time)
- `Future-S5.4.E.smtp-credentials-rotation-automation-provider-specific` (~2-3h · per-provider API)

---

## Doctrinas inviolables sostained

- R6 audit_log hash chain inviolable durante rotation (NO truncate · ONLY append)
- Sub-atom 5.A audit_log 3-way OR · rotation events emit con project_id=NULL + client_id=NULL (platform-global event)
- ADR-013 doble pool separate · admin secrets independent de cliente secrets
- OPS-049 honest defer · automation Future-X explicit (manual procedure baseline)
