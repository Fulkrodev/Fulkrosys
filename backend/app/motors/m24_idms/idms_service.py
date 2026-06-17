"""M24 IDMS Service.

- 15 carpetas estándar del esqueleto §2.15 (idempotent)
- Intake pipeline: SHA-256 + dedupe exacta + auto-classify por nombre
- Búsqueda: ILIKE sobre nombre + full_text_content + filtros
- Tagging manual con confidence=1.0, source=manual
- Versionado via DocumentVersion
- [Sesion 9 Paso 3.1] Workflow status draft/review/approved/archived/deprecated
- [Sesion 9 Paso 3.1] Expiration policy + alertas caducidad
- [Sesion 9 Paso 3.1] Permisos granulares idms_document_permissions
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.storage.minio_client import BUCKET_DOCUMENTS, put_object
from backend.app.models.documents import Document, DocumentVersion
from backend.app.models.idms import (
    DocumentFolder,
    DocumentTag,
    IdmsDocumentPermission,
)


STANDARD_FOLDERS: list[dict[str, str]] = [
    {"code": "00", "name": "00_Contractual", "path": "/00_Contractual/"},
    {"code": "01", "name": "01_Gobierno", "path": "/01_Gobierno/"},
    {"code": "02", "name": "02_Categorizacion", "path": "/02_Categorizacion/"},
    {"code": "03", "name": "03_Analisis_Riesgos", "path": "/03_Analisis_Riesgos/"},
    {"code": "04", "name": "04_Declaracion_Aplicabilidad", "path": "/04_Declaracion_Aplicabilidad/"},
    {"code": "05", "name": "05_Plan_Adecuacion", "path": "/05_Plan_Adecuacion/"},
    {"code": "06", "name": "06_Normativa", "path": "/06_Normativa/"},
    {"code": "07", "name": "07_Procedimientos", "path": "/07_Procedimientos/"},
    {"code": "08", "name": "08_Registros_Operativos", "path": "/08_Registros_Operativos/"},
    {"code": "09", "name": "09_Evidencias", "path": "/09_Evidencias/"},
    {"code": "10", "name": "10_Continuidad", "path": "/10_Continuidad/"},
    {"code": "11", "name": "11_Formacion", "path": "/11_Formacion/"},
    {"code": "12", "name": "12_Proveedores", "path": "/12_Proveedores/"},
    {"code": "13", "name": "13_Informes_Tecnicos", "path": "/13_Informes_Tecnicos/"},
    {"code": "14", "name": "14_Remediacion", "path": "/14_Remediacion/"},
    {"code": "99", "name": "99_Misc", "path": "/99_Misc/"},
]

# Heurística simple de clasificación por nombre → carpeta estándar
CLASSIFICATION_RULES: list[tuple[tuple[str, ...], str, str]] = [
    # (keywords, standard_code, clasificacion)
    (("contrato", "propuesta", "nda", "sla"), "00", "contrato"),
    (("acta", "categori"), "02", "registro"),
    (("riesgo", "magerit", "amenaza"), "03", "informe"),
    (("dda", "aplicabilid"), "04", "registro"),
    (("plan_adecuacion", "plan adecuac"), "05", "informe"),
    (("politic",), "06", "politica"),
    (("procedimiento",), "07", "procedimiento"),
    (("registro", "log"), "08", "registro"),
    (("evidencia",), "09", "evidencia"),
    (("continuidad", "drp", "bia"), "10", "informe"),
    (("formacion", "curso", "training"), "11", "registro"),
    (("proveedor", "vendor"), "12", "registro"),
    (("informe", "e-7", "pentest", "auditoria"), "13", "informe"),
]


class IDMSError(Exception):
    pass


# ══════════════ Workflow status values (Sesion 9 Paso 3.1) ══════════════
STATUS_DRAFT = "draft"
STATUS_REVIEW = "review"
STATUS_APPROVED = "approved"
STATUS_ARCHIVED = "archived"
STATUS_DEPRECATED = "deprecated"

VALID_STATUSES: tuple[str, ...] = (
    STATUS_DRAFT, STATUS_REVIEW, STATUS_APPROVED,
    STATUS_ARCHIVED, STATUS_DEPRECATED,
)

# Transiciones permitidas estado_origen -> {estados_destino}
VALID_TRANSITIONS: dict[str, set[str]] = {
    STATUS_DRAFT:      {STATUS_REVIEW, STATUS_ARCHIVED},
    STATUS_REVIEW:     {STATUS_APPROVED, STATUS_DRAFT, STATUS_ARCHIVED},
    STATUS_APPROVED:   {STATUS_ARCHIVED, STATUS_DEPRECATED},
    STATUS_ARCHIVED:   {STATUS_DRAFT},  # restore_to_draft excepcional
    STATUS_DEPRECATED: {STATUS_DRAFT},
}


# Defaults review_period_months por clasificacion (heuristica)
DEFAULT_REVIEW_PERIOD_MONTHS: dict[str, int] = {
    "politica": 12,
    "procedimiento": 24,
    "contrato": 24,
    "informe": 12,
    "registro": 24,
    # evidencia, otro -> sin caducidad por defecto (None)
}


# ══════════════ Permission roles ══════════════
ROLE_OWNER = "owner"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"

VALID_ROLES: tuple[str, ...] = (ROLE_OWNER, ROLE_EDITOR, ROLE_VIEWER)

# Orden jerarquico: si required=viewer, owner y editor tambien acceden.
_ROLE_HIERARCHY: dict[str, int] = {
    ROLE_VIEWER: 1, ROLE_EDITOR: 2, ROLE_OWNER: 3,
}


class IDMSService:
    """Intelligent Document Management Service."""

    # ══════════════════ FOLDERS ══════════════════

    async def initialize_standard_folders(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        client_id: uuid.UUID | None = None,
    ) -> list[DocumentFolder]:
        """Crea las 15 carpetas estándar del esqueleto §2.15. Idempotente."""
        existing = await self.list_folders(db, project_id, standard_only=True)
        existing_codes = {f.standard_code for f in existing}

        created: list[DocumentFolder] = []
        for idx, spec in enumerate(STANDARD_FOLDERS):
            if spec["code"] in existing_codes:
                continue
            folder = DocumentFolder(
                client_id=client_id,
                project_id=project_id,
                name=spec["name"],
                virtual_path=spec["path"],
                is_standard=True,
                standard_code=spec["code"],
                custom_order=idx,
            )
            db.add(folder)
            created.append(folder)
        await db.flush()
        return existing + created

    async def create_folder(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        name: str,
        parent_folder_id: uuid.UUID | None = None,
        virtual_path: str | None = None,
        client_id: uuid.UUID | None = None,
    ) -> DocumentFolder:
        if parent_folder_id and not virtual_path:
            parent = (await db.execute(
                select(DocumentFolder).where(DocumentFolder.id == parent_folder_id)
            )).scalar_one_or_none()
            if not parent:
                raise IDMSError(f"Parent folder {parent_folder_id} no existe")
            virtual_path = f"{parent.virtual_path.rstrip('/')}/{name}/"
        if not virtual_path:
            virtual_path = f"/{name}/"
        folder = DocumentFolder(
            client_id=client_id,
            project_id=project_id,
            parent_folder_id=parent_folder_id,
            name=name,
            virtual_path=virtual_path,
            is_standard=False,
        )
        db.add(folder)
        await db.flush()
        return folder

    async def list_folders(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        standard_only: bool = False,
    ) -> list[DocumentFolder]:
        stmt = select(DocumentFolder).where(DocumentFolder.project_id == project_id)
        if standard_only:
            stmt = stmt.where(DocumentFolder.is_standard.is_(True))
        stmt = stmt.order_by(DocumentFolder.custom_order, DocumentFolder.name)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_folder(
        self, db: AsyncSession, folder_id: uuid.UUID,
    ) -> DocumentFolder | None:
        res = await db.execute(select(DocumentFolder).where(DocumentFolder.id == folder_id))
        return res.scalar_one_or_none()

    async def get_folder_tree(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> dict[str, Any]:
        folders = await self.list_folders(db, project_id)

        # Counts por carpeta
        counts_stmt = select(
            Document.folder_id, func.count(Document.id),
        ).where(
            Document.project_id == project_id,
            Document.folder_id.isnot(None),
        ).group_by(Document.folder_id)
        counts_rows = (await db.execute(counts_stmt)).all()
        counts = {row[0]: row[1] for row in counts_rows}

        # Build tree
        node_by_id: dict[uuid.UUID, dict] = {}
        for f in folders:
            node_by_id[f.id] = {
                "id": str(f.id),
                "name": f.name,
                "virtual_path": f.virtual_path,
                "is_standard": f.is_standard,
                "standard_code": f.standard_code,
                "parent_folder_id": str(f.parent_folder_id) if f.parent_folder_id else None,
                "documents_count": counts.get(f.id, 0),
                "children": [],
            }

        roots: list[dict] = []
        for f in folders:
            node = node_by_id[f.id]
            if f.parent_folder_id and f.parent_folder_id in node_by_id:
                node_by_id[f.parent_folder_id]["children"].append(node)
            else:
                roots.append(node)

        return {"folders": roots}

    async def move_document_to_folder(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        folder_id: uuid.UUID,
    ) -> Document:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            raise IDMSError(f"Document {document_id} no existe")
        folder = await self.get_folder(db, folder_id)
        if not folder:
            raise IDMSError(f"Folder {folder_id} no existe")
        if folder.project_id != doc.project_id:
            raise IDMSError("Folder y Document de proyectos distintos")
        doc.folder_id = folder_id
        await db.flush()
        return doc

    # ══════════════════ INTAKE PIPELINE ══════════════════

    @staticmethod
    def _persist_to_minio(
        object_key: str,
        contenido: bytes,
        content_type: str | None,
        project_id: uuid.UUID,
    ) -> str:
        """#36 · sube el binario REAL a MinIO (BUCKET_DOCUMENTS) bajo ``object_key``
        y devuelve el ``storage_path`` CANÓNICO ``minio://{bucket}/{key}``.

        Antes de #36 el intake/versionado calculaba la ruta y persistía la metadata
        (Document + DocumentVersion) pero DESCARTABA los bytes: el objeto nunca
        existía en el object store.

        CRÍTICO (review adversarial): ``storage_path`` DEBE llevar el prefijo
        ``minio://{bucket}/`` porque el único consumidor que recupera el binario
        (portal cliente m21 ``portal_document_download`` / ``_preview``) sólo sirve
        rutas que empiezan por ``minio://`` (``rest.partition('/')`` → bucket+key);
        una key desnuda devolvía HTTP 503. Mismo contrato que m25/backup_builder.

        Upload real (no best-effort): si MinIO no está disponible la operación
        falla y la transacción de DB revierte.
        """
        put_object(
            bucket=BUCKET_DOCUMENTS,
            key=object_key,
            data=contenido,
            content_type=content_type or "application/octet-stream",
            metadata={"project-id": str(project_id)},
        )
        return f"minio://{BUCKET_DOCUMENTS}/{object_key}"

    async def intake_document(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        nombre: str,
        contenido: bytes,
        tipo_mime: str = "application/octet-stream",
        folder_id: uuid.UUID | None = None,
        clasificacion: str | None = None,
        tags: list[dict] | None = None,
        subido_por: str = "marcos",
        full_text_content: str | None = None,
    ) -> dict[str, Any]:
        if not contenido:
            raise IDMSError("Contenido vacío no permitido")

        content_hash = hashlib.sha256(contenido).hexdigest()

        # 1) Deduplicación exacta
        duplicate = await self._check_duplicate(db, project_id, content_hash)
        if duplicate:
            return {
                "document": duplicate,
                "version": None,
                "tags": await self.get_tags(db, duplicate.id),
                "duplicate": True,
                "content_hash": content_hash,
            }

        # 2) Clasificar carpeta destino si no especificada
        if not folder_id:
            folder_id = await self._auto_classify_folder(db, project_id, nombre)
            if not clasificacion:
                clasificacion = self._auto_classify_clasificacion(nombre)

        # 3) Crear Document · storage_path canónico minio://{bucket}/{key} (#36)
        object_key = (
            f"fulkro/projects/{project_id}/idms/{content_hash[:12]}_{nombre}"
        )
        storage_path = f"minio://{BUCKET_DOCUMENTS}/{object_key}"
        doc = Document(
            project_id=project_id,
            nombre=nombre,
            tipo=tipo_mime,
            folder_id=folder_id,
            content_hash=content_hash,
            file_size_bytes=len(contenido),
            storage_path=storage_path,
            full_text_content=full_text_content,
            clasificacion=clasificacion,
            estado="active",
            version_actual="1",
            generated_by=subido_por,
            generated_at=datetime.now(timezone.utc),
        )
        db.add(doc)
        await db.flush()

        # 3.5) #36 · subir el binario real a MinIO (antes se descartaba)
        self._persist_to_minio(object_key, contenido, tipo_mime, project_id)

        # 4) Crear DocumentVersion v1
        version = DocumentVersion(
            document_id=doc.id,
            version="1",
            hash_sha256=content_hash,
            contenido_path=storage_path,
            generado_por=subido_por,
            generado_at=datetime.now(timezone.utc),
        )
        db.add(version)

        # 5) Crear tags
        tag_objs: list[DocumentTag] = []
        for tag in (tags or []):
            tag_obj = await self.add_tag(
                db,
                document_id=doc.id,
                project_id=project_id,
                tag_type=tag["type"],
                tag_value=tag["value"],
                source=tag.get("source", "manual"),
                confidence=tag.get("confidence", 1.0),
            )
            tag_objs.append(tag_obj)
        await db.flush()

        return {
            "document": doc,
            "version": version,
            "tags": tag_objs,
            "duplicate": False,
            "content_hash": content_hash,
        }

    async def _check_duplicate(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        content_hash: str,
    ) -> Document | None:
        res = await db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.content_hash == content_hash,
                # un documento borrado no debe eclipsar una re-subida legítima
                Document.deleted_at.is_(None),
            ).limit(1)
        )
        return res.scalar_one_or_none()

    async def _auto_classify_folder(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        nombre: str,
    ) -> uuid.UUID | None:
        lower = nombre.lower()
        for keywords, code, _ in CLASSIFICATION_RULES:
            if any(kw in lower for kw in keywords):
                folder = (await db.execute(
                    select(DocumentFolder).where(
                        DocumentFolder.project_id == project_id,
                        DocumentFolder.standard_code == code,
                    ).limit(1)
                )).scalar_one_or_none()
                if folder:
                    return folder.id
        # Default: 99_Misc si existe
        misc = (await db.execute(
            select(DocumentFolder).where(
                DocumentFolder.project_id == project_id,
                DocumentFolder.standard_code == "99",
            ).limit(1)
        )).scalar_one_or_none()
        return misc.id if misc else None

    @staticmethod
    def _auto_classify_clasificacion(nombre: str) -> str:
        lower = nombre.lower()
        for keywords, _, clas in CLASSIFICATION_RULES:
            if any(kw in lower for kw in keywords):
                return clas
        return "otro"

    # ══════════════════ SEARCH ══════════════════

    async def search_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        query: str | None = None,
        folder_id: uuid.UUID | None = None,
        clasificacion: str | None = None,
        tag_type: str | None = None,
        tag_value: str | None = None,
        limit: int = 50,
    ) -> list[Document]:
        stmt = select(Document).where(Document.project_id == project_id)

        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Document.nombre.ilike(like),
                    Document.full_text_content.ilike(like),
                )
            )
        if folder_id:
            stmt = stmt.where(Document.folder_id == folder_id)
        if clasificacion:
            stmt = stmt.where(Document.clasificacion == clasificacion)

        if tag_type or tag_value:
            # Subquery — documentos con tag que matchea
            tag_stmt = select(DocumentTag.document_id).where(
                DocumentTag.project_id == project_id,
            )
            if tag_type:
                tag_stmt = tag_stmt.where(DocumentTag.tag_type == tag_type)
            if tag_value:
                tag_stmt = tag_stmt.where(DocumentTag.tag_value == tag_value)
            stmt = stmt.where(Document.id.in_(tag_stmt))

        stmt = stmt.order_by(Document.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def search_by_measure(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        measure_code: str,
    ) -> list[Document]:
        return await self.search_documents(
            db, project_id,
            tag_type="measure_ens",
            tag_value=measure_code,
        )

    # ══════════════════ TAGS ══════════════════

    async def add_tag(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        project_id: uuid.UUID,
        tag_type: str,
        tag_value: str,
        source: str = "manual",
        confidence: float = 1.0,
    ) -> DocumentTag:
        tag = DocumentTag(
            document_id=document_id,
            project_id=project_id,
            tag_type=tag_type,
            tag_value=tag_value,
            source=source,
            confidence=confidence,
        )
        db.add(tag)
        await db.flush()
        return tag

    async def remove_tag(
        self,
        db: AsyncSession,
        tag_id: uuid.UUID,
        expected_document_id: uuid.UUID | None = None,
    ) -> None:
        res = await db.execute(select(DocumentTag).where(DocumentTag.id == tag_id))
        tag = res.scalar_one_or_none()
        if not tag:
            raise IDMSError(f"Tag {tag_id} no existe")
        # B5 IDOR fix · el tag DEBE pertenecer al documento de la URL (que a su
        # vez ya está atado al proyecto del caller). Sin esto, un cliente con un
        # documento propio podía borrar un tag de un documento ajeno por tag_id.
        if expected_document_id is not None and tag.document_id != expected_document_id:
            raise IDMSError(f"Tag {tag_id} no existe")
        await db.delete(tag)
        await db.flush()

    async def get_tags(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> list[DocumentTag]:
        res = await db.execute(
            select(DocumentTag)
            .where(DocumentTag.document_id == document_id)
            .order_by(DocumentTag.created_at.asc())
        )
        return list(res.scalars().all())

    # ══════════════════ VERSIONS ══════════════════

    async def create_version(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        contenido: bytes,
        descripcion_cambio: str | None = None,
        subido_por: str = "marcos",
    ) -> dict[str, Any]:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            raise IDMSError(f"Document {document_id} no existe")

        # FIX P2-6: serializar el cálculo del número de versión por document_id
        # (advisory lock transaccional · Pattern #22). Antes len(existing)+1 sin
        # lock → 2 subidas concurrentes producían la misma versión; además len()
        # no filtra borradas (reuso de número). Ahora MAX(numérico)+1 bajo lock,
        # con unique (document_id, version) en BD como red de seguridad
        # (migración document_version_unique_001).
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"idms_doc_{document_id}"},
        )
        max_row = (await db.execute(
            text(
                "SELECT COALESCE(MAX(NULLIF(regexp_replace(version, '[^0-9]', "
                "'', 'g'), '')::int), 0) FROM document_versions "
                "WHERE document_id = :did AND deleted_at IS NULL"
            ),
            {"did": str(document_id)},
        )).scalar()
        next_version_num = int(max_row or 0) + 1
        next_version = str(next_version_num)

        new_hash = hashlib.sha256(contenido).hexdigest()
        object_key = (
            f"fulkro/projects/{doc.project_id}/idms/v{next_version}_{new_hash[:12]}_{doc.nombre}"
        )
        # #36 · sube el binario + storage_path canónico minio://{bucket}/{key}
        storage_path = self._persist_to_minio(
            object_key, contenido, doc.tipo, doc.project_id
        )

        version = DocumentVersion(
            document_id=document_id,
            version=next_version,
            hash_sha256=new_hash,
            contenido_path=storage_path,
            generado_por=subido_por,
            generado_at=datetime.now(timezone.utc),
            firma_data=descripcion_cambio,
        )
        db.add(version)

        # Update document master
        doc.content_hash = new_hash
        doc.storage_path = storage_path
        doc.file_size_bytes = len(contenido)
        doc.version_actual = next_version
        await db.flush()
        return {"version": version, "document": doc}

    async def list_versions(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> list[DocumentVersion]:
        res = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.generado_at.asc().nulls_last())
        )
        return list(res.scalars().all())

    # ══════════════════ STATS ══════════════════

    async def get_project_stats(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> dict[str, Any]:
        total_docs = (await db.execute(
            select(func.count(Document.id)).where(Document.project_id == project_id)
        )).scalar() or 0

        total_folders = (await db.execute(
            select(func.count(DocumentFolder.id)).where(
                DocumentFolder.project_id == project_id,
            )
        )).scalar() or 0

        by_clas_rows = (await db.execute(
            select(Document.clasificacion, func.count(Document.id))
            .where(Document.project_id == project_id)
            .group_by(Document.clasificacion)
        )).all()
        by_clasificacion = {row[0] or "sin_clasificar": row[1] for row in by_clas_rows}

        by_folder_rows = (await db.execute(
            select(DocumentFolder.name, func.count(Document.id))
            .join(Document, Document.folder_id == DocumentFolder.id)
            .where(DocumentFolder.project_id == project_id)
            .group_by(DocumentFolder.name)
        )).all()
        by_folder = {row[0]: row[1] for row in by_folder_rows}

        unclassified = (await db.execute(
            select(func.count(Document.id)).where(
                Document.project_id == project_id,
                Document.clasificacion.is_(None),
            )
        )).scalar() or 0

        # Untagged: documents sin ningún tag
        untagged_stmt = select(func.count(Document.id)).where(
            Document.project_id == project_id,
            ~Document.id.in_(
                select(DocumentTag.document_id).where(
                    DocumentTag.project_id == project_id,
                )
            ),
        )
        untagged = (await db.execute(untagged_stmt)).scalar() or 0

        return {
            "total_documents": total_docs,
            "total_folders": total_folders,
            "by_clasificacion": by_clasificacion,
            "by_folder": by_folder,
            "unclassified": unclassified,
            "untagged": untagged,
        }

    # ══════════════════ Documents wrapper ══════════════════

    async def get_document(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document | None:
        res = await db.execute(select(Document).where(Document.id == document_id))
        return res.scalar_one_or_none()

    async def list_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        folder_id: uuid.UUID | None = None,
        clasificacion: str | None = None,
        status: str | None = None,
    ) -> list[Document]:
        stmt = select(Document).where(Document.project_id == project_id)
        if folder_id:
            stmt = stmt.where(Document.folder_id == folder_id)
        if clasificacion:
            stmt = stmt.where(Document.clasificacion == clasificacion)
        if status:
            stmt = stmt.where(Document.estado == status)
        stmt = stmt.order_by(Document.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    # ══════════════════ WORKFLOW STATUS (Sesion 9 Paso 3.1) ══════════════════

    async def _transition_status(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        target_status: str,
        allow_direct_restore: bool = False,
    ) -> Document:
        """Valida y aplica una transicion de status. Uso interno."""
        if target_status not in VALID_STATUSES:
            raise IDMSError(
                f"Status invalido: {target_status!r}. Validos: {VALID_STATUSES}"
            )
        doc = await self.get_document(db, document_id)
        if doc is None:
            raise IDMSError(f"Documento {document_id} no encontrado")
        current = doc.estado or STATUS_DRAFT
        # Normalizar: si current no es un valor workflow valido, asumir
        # draft (documentos preexistentes generados por M6 con otros
        # estados legacy conviven sin romperse).
        if current not in VALID_STATUSES:
            current = STATUS_DRAFT
        if current == target_status:
            return doc  # idempotente
        allowed = VALID_TRANSITIONS.get(current, set())
        if target_status not in allowed and not allow_direct_restore:
            raise IDMSError(
                f"Transicion no permitida: {current} -> {target_status}. "
                f"Desde '{current}' solo son validos: {sorted(allowed)}"
            )
        doc.estado = target_status
        await db.flush()
        return doc

    async def submit_for_review(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document:
        """draft -> review."""
        return await self._transition_status(db, document_id, STATUS_REVIEW)

    async def approve_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        approver_user_id: uuid.UUID,
    ) -> Document:
        """review -> approved. Persiste approver + timestamp."""
        doc = await self._transition_status(db, document_id, STATUS_APPROVED)
        doc.approved_by_user_id = approver_user_id
        doc.approved_at = datetime.now(timezone.utc)
        await db.flush()
        return doc

    async def archive_document(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document:
        """approved/draft/review -> archived (caducidad o reemplazo)."""
        doc = await self.get_document(db, document_id)
        if doc is None:
            raise IDMSError(f"Documento {document_id} no encontrado")
        # archived es permitido desde draft, review o approved via transicion
        return await self._transition_status(db, document_id, STATUS_ARCHIVED)

    async def deprecate_document(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document:
        """approved -> deprecated (usado cuando nueva version lo reemplaza)."""
        return await self._transition_status(db, document_id, STATUS_DEPRECATED)

    async def restore_to_draft(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document:
        """archived/deprecated -> draft (edge case, requiere audit log externo)."""
        return await self._transition_status(
            db, document_id, STATUS_DRAFT, allow_direct_restore=True,
        )

    async def list_documents_by_status(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        status: str,
    ) -> list[Document]:
        if status not in VALID_STATUSES:
            raise IDMSError(f"Status invalido: {status!r}")
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.estado == status,
                    Document.deleted_at.is_(None),
                )
            )
            .order_by(Document.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    # ══════════════════ EXPIRATION POLICY (Sesion 9 Paso 3.1) ══════════════════

    async def set_expiration(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        expires_at: datetime | None = None,
        review_period_months: int | None = None,
    ) -> Document:
        """Establece caducidad. Si review_period_months se da y expires_at
        no, calcula expires_at = approved_at (o now) + N meses."""
        doc = await self.get_document(db, document_id)
        if doc is None:
            raise IDMSError(f"Documento {document_id} no encontrado")
        if review_period_months is not None and review_period_months <= 0:
            raise IDMSError(
                f"review_period_months debe ser positivo: {review_period_months}"
            )
        if expires_at is None and review_period_months is not None:
            base = doc.approved_at or datetime.now(timezone.utc)
            # Aproximacion: N meses = N*30 dias. Sin dependencia externa.
            expires_at = base + timedelta(days=30 * review_period_months)
        doc.expires_at = expires_at
        doc.review_period_months = review_period_months
        await db.flush()
        return doc

    async def apply_default_expiration(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> Document:
        """Aplica default por clasificacion (politica 12m, procedimiento 24m...).

        No-op si clasificacion no tiene default (evidencia/otro)."""
        doc = await self.get_document(db, document_id)
        if doc is None:
            raise IDMSError(f"Documento {document_id} no encontrado")
        clasif = (doc.clasificacion or "").lower()
        months = DEFAULT_REVIEW_PERIOD_MONTHS.get(clasif)
        if months is None:
            return doc
        return await self.set_expiration(
            db, document_id, review_period_months=months,
        )

    async def list_expiring_soon(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        days_ahead: int = 30,
    ) -> list[Document]:
        """Documentos activos cuya expires_at cae en los proximos N dias."""
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days_ahead)
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.deleted_at.is_(None),
                    Document.expires_at.is_not(None),
                    Document.expires_at >= now,
                    Document.expires_at <= horizon,
                    Document.estado != STATUS_DEPRECATED,
                    Document.estado != STATUS_ARCHIVED,
                )
            )
            .order_by(Document.expires_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def list_expired(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[Document]:
        """Documentos activos cuya expires_at ya paso."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.deleted_at.is_(None),
                    Document.expires_at.is_not(None),
                    Document.expires_at < now,
                    Document.estado != STATUS_DEPRECATED,
                    Document.estado != STATUS_ARCHIVED,
                )
            )
            .order_by(Document.expires_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def auto_deprecate_expired(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[Document]:
        """Marca como deprecated los expired. Cron candidate."""
        expired = await self.list_expired(db, project_id)
        now = datetime.now(timezone.utc)
        deprecated: list[Document] = []
        for doc in expired:
            current = doc.estado or STATUS_DRAFT
            if current not in VALID_STATUSES:
                current = STATUS_DRAFT
            # Solo podemos deprecar si esta approved; si estaba draft/review,
            # lo archivamos directamente (caducidad antes de aprobar es
            # anomalia que merece revision manual).
            if current == STATUS_APPROVED:
                doc.estado = STATUS_DEPRECATED
            else:
                doc.estado = STATUS_ARCHIVED
            deprecated.append(doc)
        if deprecated:
            await db.flush()
        return deprecated

    # ══════════════════ PERMISSIONS (Sesion 9 Paso 3.1) ══════════════════

    async def grant_permission(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        granted_by_user_id: uuid.UUID | None = None,
    ) -> IdmsDocumentPermission:
        if role not in VALID_ROLES:
            raise IDMSError(
                f"Role invalido: {role!r}. Validos: {VALID_ROLES}"
            )
        # Upsert simple: si ya existe, actualiza role + granted_by
        existing = (await db.execute(
            select(IdmsDocumentPermission).where(
                and_(
                    IdmsDocumentPermission.document_id == document_id,
                    IdmsDocumentPermission.user_id == user_id,
                    IdmsDocumentPermission.deleted_at.is_(None),
                )
            )
        )).scalar_one_or_none()
        if existing:
            existing.role = role
            existing.granted_by_user_id = granted_by_user_id
            existing.granted_at = datetime.now(timezone.utc)
            await db.flush()
            return existing
        perm = IdmsDocumentPermission(
            document_id=document_id,
            user_id=user_id,
            role=role,
            granted_by_user_id=granted_by_user_id,
            granted_at=datetime.now(timezone.utc),
        )
        db.add(perm)
        await db.flush()
        return perm

    async def revoke_permission(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Soft delete del permiso. Returns True si habia algo que revocar."""
        perm = (await db.execute(
            select(IdmsDocumentPermission).where(
                and_(
                    IdmsDocumentPermission.document_id == document_id,
                    IdmsDocumentPermission.user_id == user_id,
                    IdmsDocumentPermission.deleted_at.is_(None),
                )
            )
        )).scalar_one_or_none()
        if perm is None:
            return False
        perm.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return True

    async def list_permissions(
        self, db: AsyncSession, document_id: uuid.UUID,
    ) -> list[IdmsDocumentPermission]:
        stmt = (
            select(IdmsDocumentPermission)
            .where(
                and_(
                    IdmsDocumentPermission.document_id == document_id,
                    IdmsDocumentPermission.deleted_at.is_(None),
                )
            )
            .order_by(IdmsDocumentPermission.granted_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def check_access(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        required_role: str = ROLE_VIEWER,
    ) -> bool:
        """Comprueba si `user_id` tiene al menos el role requerido.

        Modelo hibrido:
        - Si el documento tiene 0 registros en idms_document_permissions
          (permisos explicitos ausentes), devuelve True. El acceso se
          controla a nivel RLS project_id (todos los miembros del
          proyecto acceden).
        - Si TIENE registros, solo los usuarios listados en la tabla
          tienen acceso segun su role (con jerarquia owner > editor > viewer).
        """
        if required_role not in VALID_ROLES:
            raise IDMSError(f"required_role invalido: {required_role!r}")
        all_perms = await self.list_permissions(db, document_id)
        if not all_perms:
            return True  # fallback RLS project_id
        user_perm = next(
            (p for p in all_perms if p.user_id == user_id), None,
        )
        if user_perm is None:
            return False
        return (
            _ROLE_HIERARCHY[user_perm.role]
            >= _ROLE_HIERARCHY[required_role]
        )

    async def my_accessible_documents(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[Document]:
        """Documentos del proyecto accesibles por `user_id`.

        Incluye:
        - Documentos sin permisos explicitos (fallback RLS).
        - Documentos con permisos explicitos que incluyen al usuario.
        """
        all_docs = await self.list_documents(db, project_id)
        accessible: list[Document] = []
        for doc in all_docs:
            if await self.check_access(
                db, doc.id, user_id, required_role=ROLE_VIEWER,
            ):
                accessible.append(doc)
        return accessible
