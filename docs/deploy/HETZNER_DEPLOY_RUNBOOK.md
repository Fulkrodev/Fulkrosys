# HETZNER DEPLOY RUNBOOK · FULKRO end-to-end

> Despliegue de FULKRO como **producto cerrado** en un servidor Hetzner.
> Stack: FastAPI + PostgreSQL 16 (pgvector + Apache AGE + pgAudit + pgBackRest)
> + Redis 7 + Celery + Next.js 14 + MinIO + Caddy + ClamAV + fastembed.
>
> Este runbook es **turnkey**: de servidor recién aprovisionado a producto
> verificado. Las piezas de infra como código que lo soportan:
>
> | Pieza | Fichero |
> |-------|---------|
> | Compose de producción | `docker-compose.prod.yml` |
> | Plantilla de secretos | `.env.prod.template` |
> | Generador de secretos | `scripts/generate-prod-secrets.sh` |
> | Provisión one-shot (orden inviolable) | `infra/docker/provision-entrypoint.sh` |
> | Bootstrap buckets MinIO (incl. WORM) | `infra/docker/minio-init.sh` |
> | Deploy turnkey | `scripts/deploy-hetzner.sh` |
> | Gate post-deploy | `scripts/verify-deploy.sh` |
> | pgBackRest (backup físico/PITR) | `infra/pgbackrest/pgbackrest.conf` + `README.md` |
> | Test de restore mensual (R8) | `scripts/backup-restore-test.sh` |
> | Reverse proxy / TLS | `infra/caddy/Caddyfile.prod` |

---

## QUICKSTART (turnkey · de servidor limpio a producto verificado)

Servidor Hetzner aprovisionado (Ubuntu LTS + Docker + `docker compose` v2), DNS de
`fulkro.es` ya apuntando a la IP, repo clonado en `/opt/fulkro`. Desde ahí:

```bash
# 0 · Prerrequisitos que pone Marcos a mano (ver §0): servidor, DNS, Yubikey,
#     ANTHROPIC_API_KEY, SMTP. El resto lo hacen los scripts.

# 1 · Secretos de producción (claves frescas · NO reutiliza las dev)
bash scripts/generate-prod-secrets.sh            # genera .env.prod (gitignored)
#     ...rellenar a mano en .env.prod: ANTHROPIC_API_KEY, SMTP_*, dominio (ver §1)
grep -nE 'CHANGE_?ME|REPLACE_?ME|XXXXX' .env.prod   # debe salir VACÍO

# 2 · Build frontend con la pública de producción + deploy turnkey
#     (deploy-hetzner.sh hace build de backend+frontend, provision en orden
#      inviolable, buckets MinIO WORM y up -d de todo el stack)
bash scripts/deploy-hetzner.sh

# 3 · Gate post-deploy (roles endurecidos · 1 head Alembic · ENS 52/68/73 · R6 · WORM)
bash scripts/verify-deploy.sh                    # exit 0 sólo si TODO PASS

# 4 · Backups: pgBackRest (físico/PITR) + restore-test mensual R8 (ver §5)
sudo -u postgres pgbackrest --stanza=fulkro stanza-create
sudo -u postgres pgbackrest --stanza=fulkro --type=full backup
FULKRO_SRC_DB=fulkro bash scripts/backup-restore-test.sh
```

El resto del documento desarrolla cada paso, el detalle de pgBackRest/cron y el
troubleshooting. Empieza por la **frontera honesta** (qué se valida dónde) y por
**§0 · lo que pone Marcos**.

---

## FRONTERA HONESTA (qué se valida dónde)

La validación **plena** de producción (stack entero arriba, TLS real, dominio,
MinIO WORM real con Object Lock, ClamAV con firmas, fastembed con modelo
cargado, pgBackRest contra el cluster) **SÓLO ocurre en el servidor Hetzner**.

En el entorno de desarrollo (Windows/WSL) se ha validado empíricamente:

- ✅ `docker-compose.prod.yml` **parsea** (`docker compose config -q` OK · 12 servicios).
- ✅ `scripts/backup-restore-test.sh` (modo lógico) restaura a una BD throwaway
  y verifica integridad (242 tablas · ENS 52/68/73 · cadena hash `audit_log` R6
  intacta · RTO ~8 s · 8/8 PASS) **sin tocar la BD live `fulkro`**.
- ✅ `scripts/verify-deploy.sh` (modo `dev`) valida la **lógica del gate** SQL
  contra `fulkro_test` (9/9 checks DB/Alembic/ENS/R6 PASS · 4 Hetzner-only SKIP).
- ✅ Sintaxis (`bash -n`) de los 4 scripts.

Lo que **SÓLO** corre en Hetzner (marcado `Hetzner-only` en cada paso):

- Provisión real del cluster prod (servicio `provision`).
- Buckets MinIO con Object Lock real (servicio `minio-init` / `mc mb --with-lock`).
- TLS automático Let's Encrypt (Caddy · requiere DNS `fulkro.es` → IP servidor).
- pgBackRest `stanza-create` + backups físicos + PITR.
- Endpoints HTTP 200 (`/api/v1/health` + frontend).

---

## 0 · LO QUE PONE MARCOS · Prerrequisitos MANUALES (antes de tocar el servidor)

Estas piezas **no las puede hacer un script** · son responsabilidad de Marcos
(servidor Hetzner, DNS de `fulkro.es`, Yubikey, `ANTHROPIC_API_KEY`, SMTP):

| # | Prerrequisito | Detalle |
|---|---------------|---------|
| 0.1 | **Servidor Hetzner** | Cloud server (CPX31+ recomendado: 4 vCPU / 8 GB / 160 GB · o dedicado). Ubuntu 22.04/24.04 LTS. Docker + `docker compose` v2 instalados. |
| 0.2 | **DNS `fulkro.es`** | Registros A/AAAA de `fulkro.es` y `www.fulkro.es` apuntando a la IP del servidor. **Imprescindible ANTES del deploy** o Caddy no podrá emitir el certificado TLS. |
| 0.3 | **Yubikey enroll** | WebAuthn-only para Marcos en prod (R4). Registrar la Yubikey tras el primer login admin (el `APP_ENV=production` desactiva el fallback de sesión dev de ADR-003). |
| 0.4 | **`ANTHROPIC_API_KEY`** | Clave real de Anthropic (Motor 11 copiloto + agentes). Sin ella, los copilotos no responden. |
| 0.5 | **SMTP** | Host/puerto/usuario/password de un relay SMTP (magic links a clientes · R5 · notificaciones M20). |
| 0.6 | **Object Storage offsite (opcional pero recomendado)** | Hetzner Object Storage (S3-compatible) para el repo2 de pgBackRest + vault m26 offsite (3-2-1). Bucket + access/secret key. |
| 0.7 | **Hardening del host** | Firewall (sólo 80/443 públicos · 22 restringido), `fail2ban`, usuario no-root con Docker, backups del propio host. Fuera del alcance de este repo. |

---

## 1 · Generar secretos de producción

> Hetzner-only en intención (genera material criptográfico real). Correr EN el
> servidor (o en una máquina segura y copiar `.env.prod` por canal cifrado).

```bash
bash scripts/generate-prod-secrets.sh          # Tarea B · genera .env.prod
```

Genera **frescas** (NO reutiliza las claves dev): `APP_SECRET_KEY`,
`FULKRO_AUTH_PRIVATE_KEY` (Ed25519) + su pública para el frontend,
`FULKRO_ML_PRIVATE_KEY`, `FULKRO_BACKUP_SIGNING_KEY`, `BACKUP_ENCRYPTION_KEY`,
passwords de `POSTGRES`/`MINIO`/`fulkro_app`/`fulkro_migrate`.

> ⚠️ **NO rotar las claves DEV** del `.env` local: romperían el entorno de
> desarrollo. `.env.prod` es un fichero **aparte**, **gitignored**.

Tras generarlo, **rellenar a mano** los prerrequisitos manuales (paso 0):

```ini
ANTHROPIC_API_KEY=sk-ant-api03-...        # real (0.4)
SMTP_HOST=... SMTP_USER=... SMTP_PASSWORD=...   # real (0.5)
APP_BASE_URL=https://fulkro.es
ALLOWED_HOSTS=fulkro.es,www.fulkro.es
WEBAUTHN_RP_ID=fulkro.es
WEBAUTHN_RP_NAME=FULKRO
# offsite opcional (0.6):
# BACKUP_S3_ENDPOINT=https://nbg1.your-objectstorage.com
# BACKUP_S3_BUCKET=... BACKUP_S3_ACCESS_KEY=... BACKUP_S3_SECRET_KEY=...
```

Verificar que NO quedan placeholders:

```bash
grep -nE 'CHANGE_?ME|REPLACE_?ME|XXXXX' .env.prod   # debe salir vacío
```

---

## 2 · Build del frontend con la pública de producción

El frontend Next.js (`frontend/Dockerfile`) se construye dentro del compose. La
clave pública de auth (`FULKRO_AUTH_PUBLIC_KEY`) que valida los JWT de sesión la
genera el paso 1 emparejada con la privada del backend. Asegurar que el frontend
la recibe (server-side · **NO** prefijo `NEXT_PUBLIC_`):

```bash
# El generador la deja en .env.prod; el servicio `frontend` del compose la
# inyecta vía env_file. Verificar que existe:
grep -q '^FULKRO_AUTH_PUBLIC_KEY=' .env.prod && echo "pubkey OK" || echo "FALTA pubkey"
```

> **Gotcha env-key mismatch** (OPS-052 72ª): si la privada del backend y la
> pública del frontend NO son el par correcto, `getClaims()` devuelve null y
> TODO `/client-portal/*` entra en bucle de login. El generador del paso 1 las
> emite emparejadas; no editarlas a mano por separado.

El build ocurre en el paso 3 (`deploy-hetzner.sh` hace `docker compose build`).
Para construir sólo el frontend de forma aislada:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod build frontend
```

---

## 3 · Deploy turnkey

> **Hetzner-only.** Orquesta el compose de producción de principio a fin.

```bash
bash scripts/deploy-hetzner.sh
```

Secuencia (idempotente · re-ejecutable):

1. Valida `.env.prod` + `docker-compose.prod.yml` + secretos mínimos + `compose config`.
2. `docker compose build` (backend + frontend + postgres prod).
3. `up -d postgres` + espera a que acepte conexiones.
4. `run --rm provision` → **orden inviolable** vía
   `infra/docker/provision-entrypoint.sh`:
   `init-extensions → init-functions → init-roles → alembic upgrade head
   (1 head: **`client_mfa_email_code_001`**) → grants → seed → REVOKE
   UPDATE,DELETE ON audit_log (R6 append-only por privilegio)`.
5. `up -d minio` + `run --rm minio-init` → buckets, incl.
   **`fulkro-evidence-worm`** con Object Lock COMPLIANCE 7 años.
6. `up -d` (todos los servicios).
7. Espera healthy (ClamAV/fastembed tardan en cold-start · ~2-5 min).

Flags: `--skip-build` · `--skip-seed` · `--dry-run`.

> **El orden importa.** `init-roles.sql` (endurecimiento NOSUPERUSER + BYPASSRLS
> dedicado + REVOKE escalada superuser) **NO** vive en ninguna migración Alembic:
> vive en `infra/docker/init-roles.sql` y se ejecuta ANTES de `alembic upgrade
> head`. Un PG limpio al que sólo se le aplica `alembic upgrade head` **no** sale
> endurecido. El servicio `provision` lo garantiza.

---

## 4 · Verificar el gate post-deploy

> **Hetzner-only** (algunos checks). Correr EN el servidor tras el deploy.

```bash
bash scripts/verify-deploy.sh
```

Comprueba (PASS/FAIL por check · `exit 0` sólo si TODO PASS):

| Check | Qué valida |
|-------|------------|
| DB-1 | `fulkro_app` NOSUPERUSER |
| DB-2 | `fulkro_app_bypassrls` existe (NOSUPERUSER + BYPASSRLS) |
| DB-3 | `fulkro_migrate` NOSUPERUSER + BYPASSRLS |
| DB-4 | `fulkro_app` **NO** es miembro de `fulkro` (sin escalada a superuser) |
| AL-1 | 1 head Alembic = `client_mfa_email_code_001` |
| ENS-1 | medidas por nivel = **52 / 68 / 73** (BÁSICA/MEDIA/ALTA) |
| ENS-2 | `op.exp.10` = "Protección de claves criptográficas" |
| R6-1 | `fn_audit_log_verify_chain().ok = TRUE` (cadena hash intacta) |
| R6-2 | `fulkro_app` SIN UPDATE/DELETE sobre `audit_log` (append-only por privilegio) |
| MIO-1 | bucket `fulkro-evidence-worm` con Object Lock/WORM activo |
| SVC-1 | todos los servicios compose healthy |
| API-1 | `/api/v1/health` → 200 |
| FE-1 | frontend → 200 (o 3xx redirect a login) |

> Modo dev (probar la lógica SQL del gate contra `fulkro_test`, sin stack prod):
> `FULKRO_VERIFY_MODE=dev bash scripts/verify-deploy.sh` → 9 PASS + 4 SKIP
> (MIO/SVC/API/FE son Hetzner-only).

Si algún check bloqueante FAILa, **no continuar**: ir a Troubleshooting.

---

## 5 · Backups · pgBackRest + restore-test (R8)

> **Hetzner-only.** Requiere `pgbackrest` instalado y el cluster prod accesible.
> Ver `infra/pgbackrest/README.md` para el detalle. Dos capas complementarias:
> pgBackRest (físico/PITR del cluster) + Motor 26 (artefactos lógicos cifrados
> offsite).

### 5.1 · Instalar + configurar pgBackRest

```bash
apt-get install -y pgbackrest
install -d -m 750 -o postgres -g postgres /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest
cp infra/pgbackrest/pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
export PGBACKREST_REPO1_CIPHER_PASS="$(grep ^BACKUP_ENCRYPTION_KEY= .env.prod | cut -d= -f2-)"
```

### 5.2 · WAL archiving en el cluster (`postgresql.conf` · requiere restart)

```conf
archive_mode = on
archive_command = 'pgbackrest --stanza=fulkro archive-push %p'
wal_level = replica
max_wal_senders = 3
```

### 5.3 · Crear stanza + primer backup

```bash
sudo -u postgres pgbackrest --stanza=fulkro stanza-create
sudo -u postgres pgbackrest --stanza=fulkro check          # valida archive + repo
sudo -u postgres pgbackrest --stanza=fulkro --type=full backup   # PRIMER backup
sudo -u postgres pgbackrest --stanza=fulkro info
```

### 5.4 · Test de restore (R8 · mensual)

```bash
# Modo lógico (rápido · valida integridad sin tocar prod · restaura a throwaway):
FULKRO_SRC_DB=fulkro bash scripts/backup-restore-test.sh
#   → dump → restore a fulkro_restoretest → verifica tablas/ENS/cadena-hash → limpia

# Modo físico pgBackRest (Hetzner-only · restaura a un cluster sandbox):
bash scripts/backup-restore-test.sh --pgbackrest
```

Registrar el resultado en m26 (`BackupRestoreTest`) vía la API de operaciones.
Salud objetivo: `green` (último full < 7 días + último restore-test PASS < 35 días).

### 5.5 · Cron recomendado (usuario `postgres`)

```cron
0 3 * * 0   pgbackrest --stanza=fulkro --type=full backup
0 3 * * 1-6 pgbackrest --stanza=fulkro --type=incr backup
# restore-test mensual (día 1, 04:00):
0 4 1 * *   cd /opt/fulkro && FULKRO_SRC_DB=fulkro bash scripts/backup-restore-test.sh
```

---

## Troubleshooting

### env-key mismatch (bucle de login en `/client-portal/*`)
**Síntoma**: el portal cliente redirige a login en bucle; `getClaims()` null.
**Causa**: `FULKRO_AUTH_PRIVATE_KEY` (backend) y `FULKRO_AUTH_PUBLIC_KEY`
(frontend) NO son el par Ed25519 correcto, o el backend generó una clave
efímera por no tener la privada en el entorno (warning en logs del backend).
**Fix**: regenerar el par con `scripts/generate-prod-secrets.sh` (las emite
emparejadas), reconstruir frontend, `docker compose up -d --force-recreate
backend frontend`. NO editar las claves por separado a mano.

### Extensiones (`CREATE EXTENSION ... requires superuser`)
**Síntoma**: el `provision` falla en `init-extensions.sql`.
**Causa**: la imagen de Postgres no es `fulkro/postgres:pg16` (no trae pgvector/
AGE/pgAudit) o se conecta con un rol no-superuser.
**Fix**: confirmar `build: infra/docker/Dockerfile.postgres`; `init-extensions`
debe correr como el superuser `fulkro` (`POSTGRES_USER`). Apache AGE exige
`LOAD 'age'` con superuser real para el KG → el seed lo omite con `--skip-age-kg`
si no hay superuser local sobre TCP.

### `permission denied to set role fulkro_app_bypassrls` (seed rc=1)
**Causa**: `fulkro_migrate` no es miembro de `fulkro_app_bypassrls` (REPRO GAP 2).
**Fix**: re-ejecutar `init-roles.sql` (idempotente · contiene el
`GRANT fulkro_app_bypassrls TO fulkro_migrate`). El servicio `provision` lo hace.

### >1 head Alembic
**Síntoma**: `verify-deploy.sh` AL-1 FAIL con varios `version_num`.
**Causa**: ramas Alembic sin merge. El árbol DEBE tener **1 head**:
`client_mfa_email_code_001`.
**Fix**: NO usar `alembic stamp` para "arreglarlo" (enmascara drift · prohibido
por la doctrina de gate DB). Resolver con una migración de merge real.

### MinIO WORM · `mc mb --with-lock` falla
**Causa**: el servidor MinIO/Object Storage no tiene versioning/Object Lock
habilitado, o el bucket ya existía sin lock (NO modificable post-creación).
**Fix**: el Object Lock SÓLO se activa al CREAR el bucket. Si existe sin lock,
hay que recrearlo (`mc rb` + `mc mb --with-lock`) — con cuidado si ya tiene
objetos. El servicio `minio-init` lo crea correcto en un MinIO limpio.

### ClamAV/fastembed unhealthy temporal
**Normal en cold-start**: ClamAV descarga firmas (~200 MB · 2-3 min) y fastembed
carga el modelo de embeddings. Esperar el `start_period` del healthcheck. Si
persiste >10 min, revisar logs (`docker compose logs clamav fastembed`).

### fastembed · imagen placeholder
El servicio `fastembed` del compose lleva una imagen **placeholder** (ver nota
honesta en `docker-compose.prod.yml`). Fijar la imagen real del micro-servicio
de embeddings antes del deploy productivo (p.ej. HuggingFace
`text-embeddings-inference` con `BAAI/bge-m3` sirviendo en `:8080`).

---

## Anexo · checklist de verificación SQL (manual, si hace falta)

```sql
-- Roles endurecidos
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles
WHERE rolname IN ('fulkro_app','fulkro_app_bypassrls','fulkro_migrate');
--   fulkro_app            | f | f
--   fulkro_app_bypassrls  | f | t
--   fulkro_migrate        | f | t

-- fulkro_app NO miembro de fulkro (sin escalada superuser) → esperado: f
SELECT EXISTS (SELECT 1 FROM pg_auth_members m
  JOIN pg_roles r ON m.roleid=r.oid JOIN pg_roles g ON m.member=g.oid
  WHERE r.rolname='fulkro' AND g.rolname='fulkro_app');

-- 1 head Alembic
SELECT count(*) AS heads, string_agg(version_num,',') FROM alembic_version;  -- 1 · client_mfa_email_code_001

-- ENS por nivel
SELECT count(*) FILTER (WHERE aplica_basica) AS basica,
       count(*) FILTER (WHERE aplica_media)  AS media,
       count(*) FILTER (WHERE aplica_alta)   AS alta
FROM ens_measures;                 -- 52 / 68 / 73

-- op.exp.10
SELECT nombre FROM ens_measures WHERE codigo='op.exp.10';  -- Protección de claves criptográficas

-- Cadena hash audit_log (R6)
SELECT ok FROM fn_audit_log_verify_chain();                -- t

-- audit_log append-only por privilegio (R6)
SELECT has_table_privilege('fulkro_app','audit_log','UPDATE')
    OR has_table_privilege('fulkro_app','audit_log','DELETE');  -- f
```

---

## Atajo dev · reconstrucción reproducible de la BD de test

`scripts/build_test_db.sh` ejecuta la misma secuencia inviolable (extensiones →
funciones → roles → `alembic upgrade head` → grants → seed → REVOKE audit_log)
sobre `fulkro_test`. Es la **referencia ejecutable del orden** y el smoke local.
**Nunca apuntar a la BD live `fulkro`** · usar `fulkro_test`.
