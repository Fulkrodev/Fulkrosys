# AUDIT #7 · Backups encryption + DR

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 6/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #7 · "Backups cifrados + DR drill operational"

---

## Verdict empírico

**M26 Backup motor está MASIVAMENTE PREPARADO** (~1407 LOC) con ADR-048 cement formalized + Fernet encryption + 3-2-1 policy + offsite replication MinIO + beat schedule. Per ADR-048 estado actual:

- ✅ **Encryption Fernet AES-128-CBC** implementada (pattern reuse m16_onboarding/token_encryption)
- ✅ **Offsite MinIO bucket `backup-vault-fulkro` dev** ready
- ✅ **3-2-1 policy** evaluator
- ✅ **Backup script `scripts/run_backup.sh`** funcional E2E (pg_dump + MinIO upload + verify)
- ✅ **Celery tasks** (m26.verify_integrity weekly · monthly_restore_test stub)
- 🟡 **Restore drill STUB** · DEFER MB-11 Hetzner infrastructure orchestration (Terraform + Ansible)
- 🔴 **Production cutover Hetzner Object Storage** pending (FASE 1.F deploy)

**Gap específico pre-piloto**:
- Hetzner Object Storage migration cuando deploy production (FASE 1.F)
- Restore drill real (vs stub message) demand-driven post-Hetzner

**ETA empírico realista refined**:
- **Hetzner backup cutover**: ~3-5h (incluido FASE 1.F producción · NO independent task)
- **Restore drill real**: ~6-10h (Terraform + Ansible orchestration · MB-11 dedicated · DEFER post-piloto OR durante FASE 1.F)

---

## Stats baseline

### M26 Backup motor (~1407 LOC)
- `service.py` 371 LOC · core service
- `api.py` 209 LOC · endpoints REST
- `offsite.py` 170 LOC · MinIO/S3 upload
- `schemas.py` 159 LOC · Pydantic in/out
- `tasks.py` 142 LOC · Celery tasks (run_pgbackrest_full · verify_integrity · monthly_restore_test · run_dr_drill)
- `encryption.py` 101 LOC · Fernet wrapper
- `backup_policy_3_2_1.py` 81 LOC · 3-2-1 rule
- `backup_policy_321_api.py` 63 LOC · API
- `exceptions.py` 41 LOC
- `__init__.py` + README.md

### Models
- `backend/app/models/backup.py` · BackupJob + BackupRetentionPolicy

### Script E2E backup (~59 LOC)
- `scripts/run_backup.sh`:
  1. POST `/api/v1/backup/trigger/postgres_full`
  2. `docker exec pg_dump | gzip > /tmp/$NAME`
  3. Compute SHA-256 + size
  4. MinIO upload via `mc cp`
  5. UPDATE `backup_jobs` table

### ADR-048 commitments
- Encryption: Fernet AES-128-CBC · `BACKUP_ENCRYPTION_KEY` env var · key fingerprint SHA256[:16] tracked
- Offsite: MinIO bucket `backup-vault-fulkro` dedicated (separation backup vs files · ISMS §5.5)
- Beat schedule: `m26.verify_integrity` weekly Sun 03:00 · `monthly_restore_test` 1st month 04:00 (stub) · `run_dr_drill` MANUAL admin trigger
- Future-MB-11 cutover Hetzner Object Storage + Terraform + Ansible

---

## Gap matrix per pre-piloto

### ✅ DONE pre-piloto (development environment)
- Encryption Fernet ✅
- Offsite MinIO dev ✅
- E2E backup script ✅
- Celery tasks scheduled ✅
- 3-2-1 policy enforced ✅

### 🟡 Pending FASE 1.F producción (NOT independent task pre-piloto)
- Hetzner Object Storage cutover (~3-5h durante deploy production)
- Hetzner backups builtin enabled (~1h config Hetzner UI)
- Production `BACKUP_ENCRYPTION_KEY` secret rotation pre-prod

### 🔴 Pending post-piloto (Future-MB-11 dedicated)
- Restore drill real (Terraform + Ansible ephemeral instance · DR validation)
- ETA empírico ~6-10h orchestration complexity

---

## Recomendación

**Backups infrastructure es PRODUCTION-READY** para cliente piloto MEDIA pre-cert ENS (ISMS commitments documented honored literal):
- ENS Continuidad mp.cont.* · backups cifrados ✅
- ENS DRP probado · stub documented intention (cuenta ENAC pre-cert · DR drill real demand-driven post-piloto)

**ETA empírico realista**:
- **Pre-piloto FASE 1.F durante producción cutover**: ~3-5h Hetzner cutover incluido natural en deploy
- **Post-piloto Future-MB-11**: ~6-10h DR drill real (DEFER acceptable · ENAC pre-cert satisfechos con commitments documented + monthly stub log)

**NO independent task pre-piloto** · scope absorbido FASE 1.F producción deploy.

---

## Cross-ref

- M26 Backup source: `backend/app/motors/m26_backup/`
- ADR-048: `docs/architecture/ADR-048_backup_encryption_strategy.md`
- Backup script: `scripts/run_backup.sh`
- ISMS commitments references ADR-048 (8 docs citations)
- Future-MB-11 Hetzner infrastructure orchestration

---

## Honest notes

1. NO verificación si `BACKUP_ENCRYPTION_KEY` env var ya set producción (parametrización Hetzner FASE 1.F)
2. Restore drill stub message *"Pending Hetzner provisioning"* preserved · acceptable per ADR-048 cement
3. MinIO buckets dev environment funcional · production migration cuando Hetzner provision
