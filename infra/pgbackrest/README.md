# pgBackRest · FULKRO (Hetzner producción)

Capa de **backup físico del cluster PostgreSQL** (full / diff / WAL / PITR).
Complementa — no sustituye — el **Motor 26** (`backend/app/motors/m26_backup/`),
que registra los jobs a nivel aplicación y sube artefactos lógicos cifrados
(dumps, exports `audit_log`) al vault offsite MinIO/Hetzner Object Storage.

| Capa | Qué respalda | Cifrado | Dónde |
|------|--------------|---------|-------|
| **pgBackRest** | cluster físico (PITR byte-exacto) | AES-256-CBC nativo | repo1 disco + repo2 S3 |
| **m26 offsite** | artefactos lógicos (dump, audit export) | Fernet (`BACKUP_ENCRYPTION_KEY`) | `backup-vault-fulkro` |

> **Frontera honesta.** `pgbackrest.conf` y los comandos de abajo SOLO son
> operativos **en el servidor Hetzner**, con un PostgreSQL accesible localmente
> y `pgbackrest` instalado. **No** se ejecutan ni validan en el entorno de
> desarrollo Windows/WSL (no hay cluster prod local). Aquí sólo se versiona la
> plantilla de configuración.

---

## 0 · Instalación (Debian/Ubuntu del servidor Hetzner)

```bash
apt-get update && apt-get install -y pgbackrest
install -d -m 750 -o postgres -g postgres /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest
cp infra/pgbackrest/pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
chown postgres:postgres /etc/pgbackrest/pgbackrest.conf && chmod 640 /etc/pgbackrest/pgbackrest.conf
```

La passphrase de cifrado del repo se inyecta por entorno (NO en el `.conf`):

```bash
# deploy-hetzner.sh ya exporta esto desde BACKUP_ENCRYPTION_KEY (.env.prod):
export PGBACKREST_REPO1_CIPHER_PASS="$BACKUP_ENCRYPTION_KEY"
# y, si repo2 S3 activo:
export PGBACKREST_REPO2_CIPHER_PASS="$BACKUP_ENCRYPTION_KEY"
```

## 1 · Wiring del cluster (`postgresql.conf`) — WAL archiving

pgBackRest necesita que el cluster archive WAL hacia él. Añadir al
`postgresql.conf` del servidor (requiere `restart`, no sólo reload):

```conf
archive_mode = on
archive_command = 'pgbackrest --stanza=fulkro archive-push %p'
max_wal_senders = 3
wal_level = replica
```

> Si Postgres corre en contenedor, estas líneas van en el `command:` del
> servicio postgres de `docker-compose.prod.yml` (Tarea A) o en un
> `postgresql.conf` montado. `archive_command` invoca el binario `pgbackrest`,
> que debe estar **dentro** del contenedor de Postgres o accesible vía
> `pg1-host`. La opción más simple en Hetzner: PostgreSQL **en el host** (no en
> contenedor) para que pgBackRest y el cluster compartan filesystem.

## 2 · Crear stanza (una sola vez, primer deploy)

```bash
sudo -u postgres pgbackrest --stanza=fulkro stanza-create
sudo -u postgres pgbackrest --stanza=fulkro check     # valida archive + repo
```

## 3 · Backups

```bash
# Full (semanal recomendado · domingo)
sudo -u postgres pgbackrest --stanza=fulkro --type=full backup

# Incremental (diario)
sudo -u postgres pgbackrest --stanza=fulkro --type=incr backup

# Estado
sudo -u postgres pgbackrest --stanza=fulkro info
```

Programación recomendada (cron del usuario `postgres`):

```cron
# full domingo 03:00, incr resto de días 03:00
0 3 * * 0  pgbackrest --stanza=fulkro --type=full backup
0 3 * * 1-6 pgbackrest --stanza=fulkro --type=incr backup
```

## 4 · Restore / PITR

```bash
# Restore del último backup a un data dir limpio (cluster PARADO):
sudo -u postgres pgbackrest --stanza=fulkro restore

# PITR a un instante concreto:
sudo -u postgres pgbackrest --stanza=fulkro \
  --type=time "--target=2026-06-08 14:00:00" restore
```

## 5 · Test de restore mensual (R8)

Usar `scripts/backup-restore-test.sh` — restaura a una **BD throwaway** y
verifica integridad sin tocar producción. Ese script tiene dos modos:

- **Modo lógico** (validable también fuera de Hetzner): `pg_dump` → restore a
  DB throwaway → verifica conteos + cadena hash `audit_log`. Es el smoke
  ejecutable en dev/CI.
- **Modo pgBackRest** (`--pgbackrest`, Hetzner-only): restaura un backup físico
  pgBackRest a un cluster sandbox.

## 6 · Retención

Definida en `pgbackrest.conf` (`repo*-retention-full/diff`) y reflejada en las
políticas de m26 (`BackupService.seed_default_policies`): full 30d/12w/12m/3y.
pgBackRest aplica `expire` automáticamente tras cada backup según la retención
configurada; forzar manualmente:

```bash
sudo -u postgres pgbackrest --stanza=fulkro expire
```
