"""M25 Paso 4 — Backup ZIP builder + Ed25519 signing + MinIO cold storage.

Genera un ZIP firmado con TODO el contenido que el cliente puede necesitar
tras el cierre del proyecto:

  dossier/        — contenido del dossier ENAC (si hay audit run) o fallback
  facturas/       — todas las facturas M15 asociadas al cliente
  documentos/     — metadatos de documentos M6 con contenido firmado
  evidencias/     — metadatos de evidencias M7
  findings/       — findings M8 pentest
  audit_log/      — audit_log completo del proyecto (hash chain verificable)
  manifest.json   — indice + hashes + firmas
  README_LEGAL.md — texto GDPR explicando contenido

La clave Ed25519 se toma de FULKRO_ML_PRIVATE_KEY (prod) o ephemeral (dev).
La public key se guarda junto al backup para permitir verificacion externa
con ``cryptography`` / ``pynacl`` sin acceso a la plataforma.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.storage.minio_client import BUCKET_EXPORTS, put_object
from backend.app.models.commercial import Invoice
from backend.app.models.core import Client, Project
from backend.app.models.documents import Document, Evidence

logger = logging.getLogger(__name__)


README_LEGAL_TEMPLATE = """# Backup de cierre — {project_name}

Cliente: **{client_name}** (CIF {client_cif})
Generado: **{generated_at}** por FULKRO
Proyecto certificado ENS: **{certified_at}**

## Contenido

Este archivo ZIP contiene la totalidad de documentacion generada durante
el proyecto de adecuacion al Esquema Nacional de Seguridad (ENS) del
cliente, tal como existia en la plataforma FULKRO en el momento de la
generacion del backup.

- `dossier/` — estructura 15-carpetas ENAC preparada para auditoria
- `documentos/` — metadatos de todos los documentos firmados
- `evidencias/` — evidencias recogidas durante el proyecto
- `findings/` — hallazgos de verificacion tecnica / pentest
- `facturas/` — copias de facturas emitidas durante el proyecto
- `audit_log/` — cadena de auditoria integridad verificable
- `manifest.json` — indice con hashes SHA-256 por fichero + firma Ed25519

## Portabilidad de datos (GDPR art. 20)

En cumplimiento del derecho a la portabilidad de datos establecido en el
articulo 20 del Reglamento General de Proteccion de Datos, este backup
puede ser entregado a un tercero (nuevo consultor, cliente final, etc.)
para la continuidad del proyecto.

## Verificacion de autenticidad

El fichero `manifest.json` incluye una firma Ed25519 sobre el contenido
del ZIP. La clave publica que verifica la firma esta en
`manifest.json:ed25519_public_key_pem`.

Ejemplo de verificacion con Python:

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    import hashlib, json

    with open("manifest.json") as f:
        manifest = json.load(f)
    pub = serialization.load_pem_public_key(
        manifest["ed25519_public_key_pem"].encode()
    )
    signed_digest = bytes.fromhex(manifest["signed_digest_sha256"])
    signature = bytes.fromhex(manifest["ed25519_signature"])
    pub.verify(signature, signed_digest)
    print("OK: firma valida")

## Retencion

Este backup esta disponible para descarga durante **60 dias** desde la
fecha de generacion. Tras ese plazo, el fichero sera eliminado
permanentemente del almacenamiento. Guarde una copia local si necesita
conservar el contenido mas alla de ese periodo.

Para preguntas: marcosmata@fulkro.es / Marcos Mata Garcia.
"""


# ══════════════════════════════════════════════════════════════════════
# Key management
# ══════════════════════════════════════════════════════════════════════


def _load_backup_signing_key() -> tuple[Ed25519PrivateKey, bytes]:
    """Carga la clave Ed25519 del firmado de backups.

    Preferencia:
      1. FULKRO_BACKUP_SIGNING_KEY (PEM) — dedicada
      2. FULKRO_ML_PRIVATE_KEY (PEM) — reutiliza la del magic link
      3. ephemeral (dev/tests) — valida solo durante el proceso
    """
    pem = (
        os.environ.get("FULKRO_BACKUP_SIGNING_KEY")
        or os.environ.get("FULKRO_ML_PRIVATE_KEY")
    )
    if pem:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise RuntimeError(
                "FULKRO_BACKUP_SIGNING_KEY / FULKRO_ML_PRIVATE_KEY no es Ed25519"
            )
        pub_pem = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return key, pub_pem

    from backend.app.core.signing_keys import is_production

    if is_production():
        raise RuntimeError(
            "FULKRO_BACKUP_SIGNING_KEY (o FULKRO_ML_PRIVATE_KEY) no definida en "
            "producción. La firma de backups requiere una clave Ed25519 estable; "
            "NUNCA se autogenera en producción (fail-fast)."
        )

    logger.warning(
        "Backup signing: usando clave Ed25519 ephemeral (dev/tests)."
    )
    key = Ed25519PrivateKey.generate()
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return key, pub_pem


# ══════════════════════════════════════════════════════════════════════
# Data collection
# ══════════════════════════════════════════════════════════════════════


async def _collect_documents(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    res = await db.execute(
        select(Document).where(Document.project_id == project_id)
    )
    rows = list(res.scalars().all())
    return [
        {
            "id": str(d.id),
            "nombre": d.nombre,
            "content_hash": d.content_hash,
            "storage_path": d.storage_path,
            "clasificacion": d.clasificacion,
            "version_actual": d.version_actual,
            "tipo": getattr(d, "tipo", None),
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]


async def _collect_evidence(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    res = await db.execute(
        select(Evidence).where(Evidence.project_id == project_id)
    )
    rows = list(res.scalars().all())
    return [
        {
            "id": str(e.id),
            "measure_code": e.measure_code,
            "tipo": e.tipo,
            "hash_sha256": e.hash_sha256,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


async def _collect_invoices(db: AsyncSession, client_id: uuid.UUID) -> list[dict]:
    res = await db.execute(
        select(Invoice).where(Invoice.client_id == client_id)
    )
    rows = list(res.scalars().all())
    return [
        {
            "id": str(i.id),
            "numero_correlativo": i.numero_correlativo,
            "tipo": i.tipo,
            "concepto": i.concepto,
            "total": float(i.total) if i.total else None,
            "fecha_emision": i.fecha_emision.isoformat() if i.fecha_emision else None,
            "estado_pago": i.estado_pago,
            "verifactu_hash": i.verifactu_hash,
        }
        for i in rows
    ]


async def _collect_audit_log(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """Extrae audit_log del proyecto (hash chain inmutable).

    audit_log es globalmente owned por ``fulkro`` y no tiene RLS directa,
    pero las politicas de project_id pueden estar en payload_new. Se
    eleva a rol ``fulkro`` por si acaso.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            text(
                "SELECT id::text, tabla, registro_id::text, accion, usuario, "
                "timestamp, payload_old, payload_new, hash_prev, hash_current "
                "FROM audit_log "
                "WHERE (payload_new->>'project_id') = :pid "
                "   OR (payload_old->>'project_id') = :pid "
                "   OR registro_id::text = :pid "
                "ORDER BY timestamp ASC"
            ),
            {"pid": str(project_id)},
        )
        rows = [dict(row._mapping) for row in res.all()]
        for r in rows:
            if isinstance(r.get("timestamp"), datetime):
                r["timestamp"] = r["timestamp"].isoformat()
        return rows
    except Exception as exc:  # pragma: no cover — audit_log puede no existir
        logger.warning("audit_log collection fallo: %s", exc)
        return []
    finally:
        await db.execute(text("RESET ROLE"))


async def _collect_findings(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    try:
        res = await db.execute(
            text(
                "SELECT id::text, fuente, severidad, medida_afectada, "
                "descripcion, estado, asignado_a, fecha_objetivo, created_at "
                "FROM findings WHERE project_id = :pid "
                "ORDER BY created_at ASC"
            ),
            {"pid": str(project_id)},
        )
        rows = [dict(row._mapping) for row in res.all()]
        for r in rows:
            for key in ("fecha_objetivo", "created_at"):
                val = r.get(key)
                if hasattr(val, "isoformat"):
                    r[key] = val.isoformat()
        return rows
    except Exception:  # pragma: no cover
        return []


# ══════════════════════════════════════════════════════════════════════
# ZIP assembly
# ══════════════════════════════════════════════════════════════════════


async def _try_build_dossier(
    db: AsyncSession, project_id: uuid.UUID,
) -> bytes | None:
    """Intenta generar el dossier M9 (15 carpetas ENAC). Best effort.

    Si no hay ``AuditPreparationRun`` o falla, devuelve ``None`` y el
    backup_builder usa un layout alternativo con los documentos sueltos.
    """
    try:
        from backend.app.models.audit_prep import AuditPreparationRun
        from backend.app.motors.m09_audit_prep.dossier_generator import (
            generate_dossier,
        )
        res = await db.execute(
            select(AuditPreparationRun).where(
                AuditPreparationRun.project_id == project_id,
            ).order_by(AuditPreparationRun.created_at.desc().nulls_last()).limit(1)
        )
        run = res.scalar_one_or_none()
        if run is None:
            return None
        return await generate_dossier(
            db, project_id=project_id, run_id=run.id, force=True,
        )
    except Exception as exc:  # pragma: no cover
        logger.info("Dossier M9 no disponible, fallback: %s", exc)
        return None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def build_and_sign_backup_zip(
    db: AsyncSession,
    project: Project,
    client: Client,
    *,
    include_dossier: bool = True,
) -> dict[str, Any]:
    """Construye el ZIP firmado del proyecto.

    Returns dict con:
      - zip_bytes: bytes
      - sha256: str
      - signature: str (hex)
      - public_key_pem: str
      - manifest: dict
    """
    documents = await _collect_documents(db, project.id)
    evidence = await _collect_evidence(db, project.id)
    invoices = await _collect_invoices(db, client.id)
    audit_log = await _collect_audit_log(db, project.id)
    findings = await _collect_findings(db, project.id)

    dossier_bytes: bytes | None = None
    if include_dossier:
        dossier_bytes = await _try_build_dossier(db, project.id)

    generated_at = datetime.now(timezone.utc)

    manifest: dict[str, Any] = {
        "backup_version": "1.0",
        "project_id": str(project.id),
        "project_name": project.nombre,
        "client_id": str(client.id),
        "client_name": client.nombre,
        "client_cif": client.cif,
        "certified_at": (
            project.certified_at.isoformat() if project.certified_at else None
        ),
        "generated_at": generated_at.isoformat(),
        "counts": {
            "documents": len(documents),
            "evidences": len(evidence),
            "invoices": len(invoices),
            "audit_log_entries": len(audit_log),
            "findings": len(findings),
            "dossier_included": dossier_bytes is not None,
        },
        "file_hashes": [],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def _write(path: str, payload: bytes) -> None:
            zf.writestr(path, payload)
            manifest["file_hashes"].append({
                "path": path,
                "sha256": _sha256_bytes(payload),
                "size_bytes": len(payload),
            })

        readme = README_LEGAL_TEMPLATE.format(
            project_name=project.nombre,
            client_name=client.nombre,
            client_cif=client.cif or "—",
            generated_at=generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            certified_at=(
                project.certified_at.isoformat()
                if project.certified_at else "—"
            ),
        )
        _write("README_LEGAL.md", readme.encode("utf-8"))

        if dossier_bytes is not None:
            _write("dossier/dossier_enac.zip", dossier_bytes)

        for d in documents:
            _write(
                f"documentos/{d['id']}.json",
                json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        for e in evidence:
            _write(
                f"evidencias/{e['id']}.json",
                json.dumps(e, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        for inv in invoices:
            _write(
                f"facturas/{inv['id']}.json",
                json.dumps(inv, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        for fnd in findings:
            _write(
                f"findings/{fnd['id']}.json",
                json.dumps(fnd, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        if audit_log:
            _write(
                "audit_log/project_audit_log.json",
                json.dumps(audit_log, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        # Manifest sin firma todavia (se escribe al final con signed_digest)
        partial_manifest_bytes = json.dumps(
            manifest, sort_keys=True, ensure_ascii=False,
        ).encode("utf-8")
        signed_digest = hashlib.sha256(partial_manifest_bytes).hexdigest()

        key, pub_pem = _load_backup_signing_key()
        signature = key.sign(bytes.fromhex(signed_digest)).hex()

        manifest["signed_digest_sha256"] = signed_digest
        manifest["ed25519_signature"] = signature
        manifest["ed25519_public_key_pem"] = pub_pem.decode("utf-8")

        final_manifest = json.dumps(
            manifest, sort_keys=True, ensure_ascii=False, indent=2,
        ).encode("utf-8")
        zf.writestr("manifest.json", final_manifest)

    zip_bytes = buf.getvalue()

    return {
        "zip_bytes": zip_bytes,
        "sha256": _sha256_bytes(zip_bytes),
        "signature": manifest["ed25519_signature"],
        "public_key_pem": manifest["ed25519_public_key_pem"],
        "manifest": manifest,
    }


def verify_backup_signature(manifest: dict, zip_bytes: bytes | None = None) -> bool:
    """Verifica la firma Ed25519 del manifest.

    NOTA (WAVE C2 · 2026-06-16): la comprobación opcional de ``zip_bytes``
    (que el ZIP descargado no se haya alterado post-firma) NO está
    implementada — el parámetro se acepta pero NO se lee. Ningún caller lo
    pasa hoy (demo/tests verifican sólo el manifest). Validar el digest del
    ZIP contra ``manifest['zip_sha256']`` cuando ``zip_bytes`` venga dado es
    una mejora pendiente; se mantiene el parámetro por compatibilidad de firma.
    """
    signed_digest = bytes.fromhex(manifest["signed_digest_sha256"])
    signature = bytes.fromhex(manifest["ed25519_signature"])
    pub = serialization.load_pem_public_key(
        manifest["ed25519_public_key_pem"].encode(),
    )
    if not isinstance(pub, Ed25519PublicKey):
        return False
    try:
        pub.verify(signature, signed_digest)
    except Exception:
        return False
    return True


def upload_backup_to_cold_storage(
    project_id: uuid.UUID,
    zip_bytes: bytes,
    sha256: str,
) -> str:
    """Sube el ZIP a MinIO (BUCKET_EXPORTS, prefijo fulkro/archives/).

    En dev/tests si MinIO no esta disponible se cae en best-effort:
    devuelve un path simulado (prefijo ``local://``) para que los tests
    puedan correr sin MinIO.
    """
    key = f"fulkro/archives/{project_id}_{sha256[:12]}.zip"
    try:
        put_object(
            BUCKET_EXPORTS, key, zip_bytes,
            content_type="application/zip",
            metadata={"fulkro-backup": "1", "project-id": str(project_id)},
        )
        return f"minio://{BUCKET_EXPORTS}/{key}"
    except Exception as exc:  # pragma: no cover — dev/tests sin MinIO
        logger.info("MinIO upload fallo (dev/tests): %s", exc)
        return f"local://{BUCKET_EXPORTS}/{key}"


def delete_backup_from_cold_storage(zip_path: str) -> bool:
    """Elimina el ZIP del almacenamiento en frio (hard delete)."""
    if zip_path.startswith("local://"):
        return True  # best-effort dev
    if zip_path.startswith("minio://"):
        rest = zip_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            from backend.app.core.storage.minio_client import get_minio_client
            get_minio_client().remove_object(bucket, key)
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("MinIO delete fallo: %s", exc)
            return False
    return False
