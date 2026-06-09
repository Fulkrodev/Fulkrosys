"""Storage helpers admin_settings — logo upload + URL building.

API expuesta:
- ``upload_logo(file_bytes, content_type)`` → ``(path_relativo, url_absoluta)``
- ``build_logo_url(path)`` construye URL absoluta desde path relativo
- ``delete_logo(path)`` cleanup logo previo (idempotente)

Decisiones arquitectónicas (sub-bloque 4.A.3.a):

- **MIME types restringidos a PNG + JPG**. SVG **excluido** por
  vector XSS: SVG admite ``<script>`` tags inline que se ejecutan
  cuando renderizan en context del dominio (Marcos's panel admin +
  proposals/invoices). Defensa front-line.
- **Tamaño máximo 2MB**: logos típicos < 100KB (PNG optimizado);
  margen 20× para PNG no optimizado. Rechaza uploads accidentales
  de imágenes alta resolución.
- **Path UUID-based**: ``admin-settings/branding/logo-<uuid>.<ext>``.
  Evita cache stale del browser/CDN tras update (URL diferente =
  recarga forzada).
- **Public bucket** (``fulkro-admin-assets``): logo renderiza en
  panel admin + proposals/invoices generados (server-side) +
  public site potencial. Signed URL complica refresh y caching.
  Asumimos logo NO contiene info confidencial (es brand identity).
- **Path relativo en `branding.logo_url`**: storage decoupled de
  URL absoluta. ``build_logo_url(path)`` aplica ``minio_public_url``
  config según env (dev http://localhost:9000, staging/prod CDN
  o nginx proxy).

Ver plan v4.2 sección FASE 4 + sub-bloque 4.A.3.a.
"""
from __future__ import annotations

import logging
import uuid

from backend.app.config import get_settings
from backend.app.core.storage.minio_client import (
    BUCKET_ADMIN_ASSETS,
    put_object,
    remove_object,
)


logger = logging.getLogger(__name__)


ALLOWED_LOGO_MIME = frozenset({"image/png", "image/jpeg"})
MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2MB


_MIME_TO_EXT: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
}


def _build_logo_path(extension: str) -> str:
    """Genera path UUID-based para evitar cache stale del browser."""
    logo_id = uuid.uuid4()
    return f"admin-settings/branding/logo-{logo_id}.{extension}"


def build_logo_url(path: str) -> str:
    """Construye URL pública absoluta desde path relativo.

    Args:
        path: ej ``"admin-settings/branding/logo-<uuid>.png"``

    Returns:
        ej ``"http://localhost:9000/fulkro-admin-assets/admin-settings/..."``
    """
    settings = get_settings()
    base = settings.minio_public_url.rstrip("/")
    return f"{base}/{BUCKET_ADMIN_ASSETS}/{path}"


def upload_logo(file_bytes: bytes, content_type: str) -> tuple[str, str]:
    """Sube logo a MinIO y devuelve (path_relativo, url_absoluta).

    Args:
        file_bytes: contenido binario del logo.
        content_type: MIME type (validado contra ALLOWED_LOGO_MIME).

    Returns:
        Tuple ``(path_relativo, url_absoluta)``. ``path_relativo`` se
        almacena en ``branding.logo_url`` (decoupled storage),
        ``url_absoluta`` se devuelve al frontend para preview.

    Raises:
        ValueError: si MIME no permitido o size excedido. Endpoint
                    layer mapea a HTTP 422.
    """
    if content_type not in ALLOWED_LOGO_MIME:
        raise ValueError(
            f"MIME type '{content_type}' no permitido. "
            f"Solo: {', '.join(sorted(ALLOWED_LOGO_MIME))}."
        )
    if len(file_bytes) > MAX_LOGO_SIZE_BYTES:
        raise ValueError(
            f"Logo excede tamaño máximo "
            f"{MAX_LOGO_SIZE_BYTES // (1024 * 1024)}MB "
            f"({len(file_bytes)} bytes recibidos)."
        )

    extension = _MIME_TO_EXT[content_type]
    path = _build_logo_path(extension)

    put_object(
        bucket=BUCKET_ADMIN_ASSETS,
        key=path,
        data=file_bytes,
        content_type=content_type,
    )

    return path, build_logo_url(path)


def delete_logo_by_url(url: str) -> None:
    """Elimina logo previo identificado por URL absoluta.

    Idempotente: si el path no existe, log warning + continúa.
    Tolerante a URLs malformadas (logo ya eliminado, URL externa
    legacy, etc.).

    Usa el separador canónico ``/{BUCKET_ADMIN_ASSETS}/`` para
    extraer el path relativo. Si la URL no contiene ese segmento,
    skip silent (probable URL externa pre-bucket-dedicated).
    """
    if not url:
        return
    marker = f"/{BUCKET_ADMIN_ASSETS}/"
    if marker not in url:
        # URL externa o malformada — no nuestro bucket, skip
        return
    path = url.split(marker, 1)[1]
    remove_object(BUCKET_ADMIN_ASSETS, path)
