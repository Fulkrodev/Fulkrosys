# FULKRO MinIO Buckets

Inventario y provisión de buckets MinIO/S3 para FULKRO.

## Arquitectura

Cada bucket se aprovisiona vía `mc` en deploy time. El backend hace `ensure_*_bucket()` lazy-create defensive donde aplique, pero entornos staging/prod con permisos restrictivos requieren provisión manual previa.

Algunos buckets (`fulkro-evidence-worm`) requieren Object Lock activado en el momento de creación, lo que el SDK Python no soporta — esos **deben** provisionarse manualmente.

## Buckets canónicos

| Bucket | Uso | Política lectura | Provisión |
|---|---|---|---|
| `fulkro-documents` | Documentos cliente (proposals, invoices, contratos firmados) | Private (signed URLs) | manual `mc mb` |
| `fulkro-evidence` | Evidencias auditoría ENS | Private | manual `mc mb` |
| `fulkro-evidence-worm` | Evidencias inmutables (Object Lock) | Private + Object Lock | manual con `--with-lock` |
| `fulkro-exports` | Exports temporales (CSV, ZIP backups) | Private | manual |
| `fulkro-admin-assets` | Logos + assets brand admin panel | **Public read** | manual O lazy-create defensive |

## Provisión `fulkro-admin-assets`

```bash
# Desde container minio o cliente mc local apuntando a la instancia
mc alias set local http://localhost:9000 fulkro changeme123
mc mb --ignore-existing local/fulkro-admin-assets
mc anonymous set download local/fulkro-admin-assets
```

Verificación:

```bash
mc ls local/                                    # debe listar fulkro-admin-assets
mc anonymous get local/fulkro-admin-assets      # debe imprimir 'download'
```

### Defensive lazy-create

`backend/app/core/storage/minio_client.py::ensure_admin_assets_bucket()` intenta crear el bucket + aplicar la public policy si no existe. En dev funciona automáticamente al primer upload; en staging/prod con permisos restrictivos podría fallar (logs WARNING) — provisión manual previa preferida.

### MIME types permitidos para logos

Validados en `backend/app/admin_settings/storage.py::ALLOWED_LOGO_MIME`:

- `image/png`
- `image/jpeg`

**`image/svg+xml` NO se acepta**. SVG admite `<script>` tags inline que se ejecutan al renderizar dentro del dominio, vector XSS reconocido. Defensa front-line en el endpoint upload.

### Tamaño máximo

2 MB (`MAX_LOGO_SIZE_BYTES`). Logos típicos optimizados pesan < 100KB; el cap deja margen 20× para PNGs no optimizados sin permitir upload de imágenes alta resolución por error.

## URL pública

`Settings.minio_public_url` (env `MINIO_PUBLIC_URL`) controla el base URL para construir links a assets en buckets con public read.

- Dev: `http://localhost:9000` (coincide con `minio_endpoint`)
- Staging/prod: típicamente CDN (`https://assets.fulkro.es`) o nginx proxy delante de MinIO

`backend/app/admin_settings/storage.py::build_logo_url(path)` construye la URL absoluta a partir del path relativo almacenado en `admin_settings.branding.logo_url`. Storage decoupled de URL absoluta — al rotar dominio público no hay que actualizar paths en BD.

## Cleanup logos previos

Cada upload nuevo dispara `delete_logo_by_url(previous_url)` (best-effort, idempotente). Si la URL previa no apunta a `fulkro-admin-assets` (legacy, externa) skip silent.

## Referencias

- Plan v4.2 sección FASE 4 sub-bloque 4.A.3.a (logo upload backend)
- `backend/app/core/storage/minio_client.py` — abstraction
- `backend/app/admin_settings/storage.py` — helpers logo
- Endpoint: `POST /api/v1/admin/settings/branding/logo` (multipart)
