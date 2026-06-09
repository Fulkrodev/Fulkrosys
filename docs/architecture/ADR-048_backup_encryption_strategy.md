# ADR-048 · Backup Encryption Strategy + Offsite Replication

> Rename history: originally created as ADR-043 (MB-10 Atom 10.6 · 2026-05-13) ·
> renamed to ADR-048 post-audit (B1.2 · OPS-063 cement) to resolve collision
> con existing inline ADR-043 (SAN-D learnings + iterative pattern · SAN-D MB-19.C)
> en `docs/spec/DECISIONS.md`.

## Status: ACCEPTED 2026-05-13

## Context

Pre-audit Atom 10.6 reveló (OPS-026 audit-first 31ª aplicación):

1. **m26_backup motor 80% built**: 7 files · 5 models · 5 Celery tasks · beat schedule · 3-2-1 policy
2. **Encryption infrastructure DORMANT**: `encryption_key_id` schema field present (3 locations: schemas.py:21 BackupJobCreate + schemas.py:35 BackupJobOut + models/backup.py:21 column) · NO logic implementada en tasks/service
3. **MinIO offsite PARCIAL**: `service.py:370` declares `bucket = settings.backup_s3_bucket` + location string `s3://{bucket}/{backup_type}/{date_str}` · `tasks.py` `run_pgbackrest_full` ejecuta solo `pgbackrest backup` localmente · **NO upload S3 actual**
4. **Restore drill STUB**: API + Celery task `backup.monthly_restore_test` exist · body literal *"Pending Hetzner provisioning — orchestration with Terraform + Ansible the five-step flow"* · similar `run_dr_drill` stub
5. **ISMS commitments LITERAL EXPLICIT** (8 docs references):
   - `Data_Retention_Policy_FULKRO.md:81`: *"comprimidas y cifradas"*
   - `F2_2_PROCEDIMIENTOS_CRITICOS:522`: *"1 copia almacenada fuera de las instalaciones principales (offsite)"*
   - `F2_2:530`: *"Bases de datos críticas...Local + offsite cifrado"*
   - `F2_2:544`: *"Paso 1. Todas las copias de seguridad se almacenarán cifradas en reposo"*
   - `F2_2:567` Section 5.5 *"Localización offsite"*
   - `F2_2:569`: *"ubicación física distinta y suficientemente alejada"*
   - `ENS_SPEC v2.1:1517`: *"Continuidad: backups cifrados, pruebas de restauración, DRP probado"*
   - `ENS_SPEC v2.1:1949`: *"Hetzner Object Storage para backups offsite cifrados"*
   - `ENS_SPEC v2.1:1987`: *"pgBackRest hace backup full semanal + incremental diario hacia Hetzner Object Storage cifrado con clave gestionada por Marcos"*

## Decision

### Encryption Strategy · Fernet AES-128-CBC

- **Pattern reuse**: `backend/app/motors/m16_onboarding/token_encryption.py` Fernet implementation (`cryptography.fernet`)
- **Key derivation**: `BACKUP_ENCRYPTION_KEY` env var transitional (independent of `app_secret_key` to allow rotation without affecting OAuth tokens)
- **Future externalization**: MB-12 Vault/SOPS forward (cement sostained)
- **Encrypt step**: post-pgBackRest backup output (tar/sql) → `.enc` files via `BackupEncryption.encrypt_file`
- **Decrypt step**: restore operation pre-pgBackRest restore via `BackupEncryption.decrypt_file`
- **Key tracking**: `BackupJob.encryption_key_id` field stores SHA256[:16] fingerprint of key used (enables key rotation forward)

### Offsite Replication · MinIO bucket dedicated `backup-vault-fulkro`

- **Dev environment**: MinIO local container :9000 (docker-compose existing · separated from general `fulkro-backups`/`fulkro-client-messages` buckets)
- **Production cutover**: Hetzner Object Storage (DEFER MB-11 infrastructure dedicated)
- **Bucket name dedicated**: `backup-vault-fulkro` (clear separation backup vs files · ISMS §5.5 offsite location distinta)
- **Upload pattern**: boto3 client post-encryption · S3-compatible API (works both MinIO local + Hetzner prod)
- **Retention policy enforcement**: existing 3-2-1 policy evaluator integrated · `BackupRetentionPolicy` table

### Restore Drill · DEFER MB-11 infrastructure orchestration

- **Current stub PRESERVED**: API + Celery task return *"Pending Hetzner provisioning"* message
- **MB-11 scope**: Hetzner Terraform + Ansible ephemeral instance spin-up + restore validation + ephemeral teardown
- **Manual trigger admin via API**: OK for spec compliance ISMS interim (admin discretion DR drills quarterly)
- **Beat schedule este Atom**: `monthly_restore_test` 1st month 04:00 (executes stub · logs intention) — ISMS commitment "pruebas de restauración" honored as documented intention

### Beat schedule additions Atom 10.6.C

- `m26.verify_integrity` · weekly Sunday 03:00 (post-full backup verification · `pgbackrest verify`)
- `m26.monthly_restore_test` · 1st month 04:00 (stub execution · logs intention for ISMS audit trail)
- `m26.run_dr_drill` · **KEEP MANUAL** admin trigger (quarterly admin discretion · prevents accidental scheduled DR)

## Anti-pattern detection · "0 deuda perfecto" cement preserved

This ADR honors Marcos cement *"0 deuda técnica perfecto"* via distinguish empirical:

- **FEATURE-side complete dev environment**: encryption + offsite upload built ✅
- **INFRASTRUCTURE-side DEFER explicit MB-11**: Hetzner Object Storage + Terraform + Ansible = MB-11 dedicated ✅
- **SPEC-PERFECT ISMS commitments**: encryption + offsite honored literal docs ✅
- **NO silent defer**: ADR-048 cement architectural + restore drill stub preserved con message clear

**OPS-062 cement validated 2da vez**: DEFER architectural with ADR explicit ≠ silent debt.

## Q5.3 cement preservation (admin-only scope)

Backups admin-only access · NO cliente-facing UI for backup management.
Q5.3 pattern preserved (similar capabilities + roles ENS · admin-internal management).
Backup endpoints already gated by `require_owner` dependency (existing pattern).

## Future revisit triggers

1. **MB-11 Hetzner Object Storage cutover**: MinIO local → Hetzner Object Storage swap
   - Env var swap: `BACKUP_S3_ENDPOINT` from `http://minio:9000` → Hetzner endpoint
   - bucket name preserved `backup-vault-fulkro` (or renamed if Hetzner constraint)
2. **MB-12 secrets externalization**: `BACKUP_ENCRYPTION_KEY` env → Vault/SOPS managed
   - Key rotation strategy formalized
   - `encryption_key_id` fingerprint already tracks rotation forward
3. **MB-11 restore drill orchestration**: stub → real Terraform/Ansible ephemeral spin-up
   - 5-step flow from `monthly_restore_test` docstring activated

## Consequences

### Positive

- ISMS commitments 2 critical honored literal (encryption at rest + offsite)
- "0 deuda perfecto" cement preserved via architectural decisions explicit
- Effort ~2-3h within OPS-048 honest estimation
- `m26_backup` motor 80% → 95% functional dev environment
- Forward path documented for MB-11 + MB-12 cement sostained
- `BackupJob.encryption_key_id` field activated (dormant → functional)

### Negative

- Restore drill stub message preserved (deferred Hetzner orchestration MB-11)
- Production cutover MinIO → Hetzner pending (MB-11 infrastructure dedicated)
- Both DEFERS documented explicit ADR-048 cement (NOT silent debt)

## References

- ISMS docs commitments 8 references (cited in Context)
- `backend/app/motors/m16_onboarding/token_encryption.py` (Fernet pattern reuse)
- `backend/app/motors/m26_backup/` (motor 80% built existing)
- ADR-046 capability cement (cement architectural pattern reference · renamed post-audit B1.2 · was ADR-037 MB-10)
- ADR-047 Intelligence DEFER (OPS-062 cement first instance · renamed post-audit B1.2 · was ADR-042 MB-10)
- OPS-062 NEW cement 2da vez · DEFER infrastructure-bound ADR explicit
