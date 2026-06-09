# Motor 26 · Backup & Disaster Recovery

Backup automático + disaster recovery: pgBackRest full/incremental/WAL + MinIO mirror snapshots + encryption Fernet AES-128-CBC + offsite replication bucket `backup-vault-fulkro` + integrity verification hash sampling + automated restore tests (monthly) + DR drills (quarterly) + retention policy enforcement. **Built in weeks 4-6 per §9.13** · MUST be operational before ingesting real client data.

## Funcionalidades

- **pgBackRest integration** full + incremental + WAL backups · industry-standard PostgreSQL backup tool.
- **MinIO mirror snapshots** segundo nivel storage (objetos) · usado por M07 evidence + M06 templates + etc.
- **Encryption Fernet AES-128-CBC** (`encryption.py`) pattern reuse `m16_onboarding/token_encryption.py` · `BACKUP_ENCRYPTION_KEY` env transitional (MB-12 Vault/SOPS forward).
- **Offsite replication** (`offsite.py`) MinIO bucket dedicated `backup-vault-fulkro` (`BUCKET_BACKUP_VAULT` constant) · Hetzner Object Storage cutover DEFER MB-11.
- **Integrity verification** hash sampling per backup · scheduled weekly (`verify_integrity`).
- **Automated restore tests** monthly (`monthly_restore_test` beat) · 1st each month 04:00.
- **DR drills** quarterly manual orchestration.
- **Retention policy enforcement** per backup tier (full · incremental · WAL · snapshots).
- **Backup policy 3-2-1** (`backup_policy_3_2_1.py` + `backup_policy_321_api.py`) cement industry-standard (3 copies · 2 media · 1 offsite).
- **Beat schedule** `verify_integrity` weekly Sunday 03:00 · `monthly_restore_test` 1st month 04:00 · `dr_drill` manual.
- **Exit criteria §9.13**: at least one verified full backup + one passed restore test ANTES ingest real client data.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.359 |
| Files | 10 |
| Status | production-grade · MB-10 Atom 10.6 closure cement (ADR-048) |
| Tests | `backend/tests/motors/m26_backup/` · 19/19 PASS |
| API prefix | `/api/v1/backup/*` |
| RBAC | Admin-only · platform-global (no RLS · no tenant context) |

## Key files

- `api.py` · endpoints HTTP Operations dashboard
- `service.py` · `BackupService` core (pgBackRest + MinIO + integrity)
- `tasks.py` · Celery beat scheduled jobs (verify_integrity · monthly_restore_test · dr_drill)
- `encryption.py` · Fernet AES-128-CBC backup encryption
- `offsite.py` · MinIO offsite upload + retention helpers
- `backup_policy_3_2_1.py` + `backup_policy_321_api.py` · 3-2-1 policy compliance
- `exceptions.py` · domain errors (BackupNotFoundError · RestoreTestNotFoundError · DrDrillNotFoundError · IntegrityVerificationNotFoundError)
- `schemas.py` · Pydantic in/out (BackupJobCreate · RestoreTestCreate · DrDrillCreate · etc.)

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `BackupJob` + `RetentionPolicy` (`backend/app/models/backup.py`)
- `RestoreTest` + `DrDrill` + `IntegrityVerification`

NO RLS · platform-global.

## Cross-motor integration

- **Inbound**: ninguno directo (motor infra · consumido vía Operations dashboard admin)
- **Outbound**: ninguno directo (motor self-contained con pgBackRest + MinIO daemons externos)
- **LLM agents**: ninguno (motor infra determinístico)

## Limitaciones conocidas

### Hetzner Object Storage cutover DEFER MB-11

Offsite replication actual usa MinIO bucket dedicated `backup-vault-fulkro` en mismo cluster Hetzner. **Cutover real a Hetzner Object Storage** (3rd region offsite genuino) DEFER MB-11 Hetzner infrastructure cutover.

### BACKUP_ENCRYPTION_KEY env transitional

Key actualmente en `.env` (plain). **Cement MB-12** Vault/SOPS externalization · ADR-048 referenced.

### DR drill manual quarterly

DR drill NO scheduled · manual orchestration trimestral. Stub preserved en code · MB-11 Terraform orchestration forward.

## ADRs referenced

- ADR-034 · cement determinismo
- ADR-048 · Backup Encryption Strategy + Offsite Replication + Restore Drill DEFER MB-11 (MB-10 Atom 10.6 closure)

## Cement OPS

**MUST be operational before ingesting any real client data** per spec §9.13. Exit criteria: at least one verified full backup + one passed restore test. MB-10 Atom 10.6 cumulative closure cement: 4 sub-atoms + ADR-048 · Fernet encryption + MinIO offsite + beat verify/restore + ISMS commitments honored literal · 19/19 tests PASS.
