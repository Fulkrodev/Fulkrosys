"""Motor 6 -- Document Factory -- service.

Manages templates, generates documents from DOCX templates with Jinja2,
signs with Ed25519, converts to PDF. Commits delegated to caller.

Pattern: consistent with M4 Gap Analysis and M19 Project Risks.
- async methods with AsyncSession
- raise specific exceptions from exceptions module
- no internal commits (delegate to caller)
- RLS enforced via set_tenant_context in middleware/endpoint
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_factory import Template
from backend.app.models.documents import Document
from backend.app.motors.m06_document_factory.catalog_loader import (
    load_catalog,
    get_catalog_version,
    get_total_templates,
)
from backend.app.motors.m06_document_factory.enums import DocumentEstado
from backend.app.motors.m06_document_factory.exceptions import (
    TemplateNotFoundError,
    TemplateInactiveError,
    TemplateFileMissingError,
    DocumentNotFoundError,
    PDFConversionError,
    SigningError,
    CatalogLoadError,
)
from backend.app.motors.m06_document_factory.rendering import (
    render_docx,
    convert_docx_to_pdf,
)
from backend.app.motors.m06_document_factory.signing import sign_document

_VAR_DIR = Path(__file__).resolve().parents[4] / "var"
_DOCUMENTS_DIR = _VAR_DIR / "documents"
_TEMPLATES_DOCX_DIR = _VAR_DIR / "templates_docx"
# service.py → m06_document_factory → motors → app → backend  (parents[3] = app)
_BRAND_DIR = Path(__file__).resolve().parents[2] / "assets" / "brand"
# F-14-02: logo consultor = marca Fulkro (no "logo_marcos.png"). Raster PNG
# generado desde frontend/public/brand/fulkro-logo-light.svg (DOCX/docxtpl
# requiere raster · el SVG no se embebe). Ejecutable 8 Pasada 16.
_CONSULTOR_LOGO = _BRAND_DIR / "fulkro-logo.png"


async def _emit_audit_log(
    db: AsyncSession,
    *,
    project_id: str,
    client_id: Optional[str],
    accion: str,
    registro_id: str,
    payload: Optional[dict] = None,
    usuario: str = "system",
) -> None:
    """Sub-atom 5.A 3-way OR audit_log emit · best-effort try/except.

    F-14-03 (Ejecutable 8 Pasada 16): trazabilidad ENAC de generación documental.
    El trigger PL/pgSQL preserva la hash chain inmutable (R6); aquí solo INSERT.
    """
    try:
        await db.execute(
            text(
                "INSERT INTO audit_log "
                "(id, tabla, registro_id, accion, usuario, "
                "project_id, client_id, payload_new, timestamp) "
                "VALUES (gen_random_uuid(), 'documents', "
                ":rid, :accion, :usuario, :pid, :cid, :payload, now())"
            ),
            {
                "rid": registro_id,
                "accion": accion,
                "usuario": usuario[:255],
                "pid": project_id,
                "cid": client_id,
                "payload": json.dumps(payload or {}),
            },
        )
        await db.flush()
    except Exception:  # pragma: no cover · best-effort, NO bloquea generación
        logger.exception("audit_log %s emit failed · rid=%s", accion, registro_id)


class DocumentFactoryService:
    """Service for document generation (Motor 6).

    All methods are async. Commits delegated to caller.
    RLS enforced via tenant context set before calling service.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ================================================================
    # Brand asset helpers
    # ================================================================

    async def _materialise_client_logo(self, project_id: UUID) -> Path | None:
        """Download the client's logo from MinIO to a temp file so it can
        be embedded by docxtpl ``InlineImage``.

        Returns ``None`` if the client has no logo configured or if the
        download fails (non-fatal — the template uses the text
        fallback). Looks up the client via the project's ``client_id``.
        """
        from sqlalchemy import text as sa_text
        row = await self.db.execute(sa_text(
            "SELECT c.logo_path, c.logo_mime_type "
            "FROM clients c JOIN projects p ON p.client_id = c.id "
            "WHERE p.id = :pid"
        ), {"pid": str(project_id)})
        hit = row.first()
        if not hit or not hit[0]:
            return None
        logo_ref, mime = hit[0], hit[1] or "image/png"
        try:
            bucket, _, key = logo_ref.partition("/")
            from backend.app.core.storage.minio_client import get_object
            payload = get_object(bucket, key)
        except Exception as exc:  # pragma: no cover — non-fatal fallback
            logger.warning("Could not fetch client logo {}: {}", logo_ref, exc)
            return None
        import tempfile
        ext = {"image/png": ".png", "image/jpeg": ".jpg",
               "image/svg+xml": ".svg", "image/webp": ".webp"}.get(mime, ".png")
        tmp = Path(tempfile.mkstemp(prefix="fulkro_logo_", suffix=ext)[1])
        tmp.write_bytes(payload)
        return tmp

    # ================================================================
    # Template management
    # ================================================================

    async def list_templates(
        self,
        categoria: str | None = None,
        familia_ens: str | None = None,
        aplica_desde: str | None = None,
        is_active: bool | None = None,
    ) -> list[Template]:
        """List templates with optional filters."""
        conditions = [Template.deleted_at.is_(None)]
        if categoria is not None:
            conditions.append(Template.categoria == categoria)
        if familia_ens is not None:
            conditions.append(Template.familia_ens == familia_ens)
        if aplica_desde is not None:
            conditions.append(Template.aplica_desde == aplica_desde)
        if is_active is not None:
            conditions.append(Template.is_active == is_active)

        result = await self.db.execute(
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.codigo)
        )
        return list(result.scalars().all())

    async def get_template_by_codigo(self, codigo: str) -> Template:
        """Get a template by its codigo. Raises TemplateNotFoundError."""
        result = await self.db.execute(
            select(Template).where(
                Template.codigo == codigo,
                Template.deleted_at.is_(None),
            )
        )
        tpl = result.scalar_one_or_none()
        if tpl is None:
            raise TemplateNotFoundError(f"Template '{codigo}' not found")
        return tpl

    async def get_template_by_id(self, template_id: UUID) -> Template:
        """Get a template by its UUID. Raises TemplateNotFoundError."""
        tpl = await self.db.get(Template, template_id)
        if tpl is None or tpl.deleted_at is not None:
            raise TemplateNotFoundError(f"Template {template_id} not found")
        return tpl

    async def load_template_metadata_from_catalog(
        self,
        catalog_path: Path | None = None,
    ) -> dict[str, Any]:
        """Load/upsert templates from YAML catalog into DB.

        Returns summary dict with counts.
        """
        catalog = load_catalog(catalog_path)
        catalog_version = get_catalog_version(catalog)
        total = get_total_templates(catalog)

        created = 0
        updated = 0

        for entry in catalog.get("templates", []):
            codigo = entry["codigo"]

            # Check if template already exists
            result = await self.db.execute(
                select(Template).where(Template.codigo == codigo)
            )
            existing = result.scalar_one_or_none()

            docx_path = _TEMPLATES_DOCX_DIR / f"{codigo}.docx"
            docx_path_str = str(docx_path) if docx_path.exists() else None

            if existing is None:
                tpl = Template(
                    codigo=codigo,
                    nombre=entry["nombre"],
                    categoria=entry["categoria"],
                    familia_ens=entry.get("familia_ens"),
                    aplica_desde=entry.get("aplica_desde"),
                    version_actual=entry.get("version_actual", "1.0"),
                    docx_path=docx_path_str,
                    placeholders_requeridos=entry.get("placeholders_requeridos"),
                    is_active=entry.get("is_active", True),
                    fuente_md=entry.get("fuente_md"),
                )
                self.db.add(tpl)
                created += 1
            else:
                existing.nombre = entry["nombre"]
                existing.categoria = entry["categoria"]
                existing.familia_ens = entry.get("familia_ens")
                existing.aplica_desde = entry.get("aplica_desde")
                existing.version_actual = entry.get("version_actual", "1.0")
                existing.placeholders_requeridos = entry.get(
                    "placeholders_requeridos"
                )
                existing.is_active = entry.get("is_active", True)
                existing.fuente_md = entry.get("fuente_md")
                if docx_path_str:
                    existing.docx_path = docx_path_str
                # Restore soft-deleted templates on sync
                if existing.deleted_at is not None:  # pragma: no cover — edge: restore deleted on re-sync
                    existing.deleted_at = None
                updated += 1

        await self.db.flush()
        logger.info(
            "Catalog sync: {} created, {} updated (catalog v{})",
            created,
            updated,
            catalog_version,
        )
        return {
            "catalog_version": catalog_version,
            "total_in_catalog": total,
            "created": created,
            "updated": updated,
        }

    # ================================================================
    # Document generation
    # ================================================================

    async def generate_document(
        self,
        project_id: UUID,
        template_codigo: str,
        context: dict[str, Any],
        generate_pdf: bool = True,
        sign: bool = True,
        generated_by: str | None = None,
        enforce_gates: bool = True,
    ) -> dict[str, Any]:
        """Generate a document from a template.

        1. Resolve template by codigo
        2. Validate workflow prerequisites (DdA frozen for policy /
           procedure / deliverable categories)
        3. Render DOCX with context
        4. Hash + sign (optional)
        5. Convert to PDF (optional)
        6. Persist Document record

        Returns a response dict. Commits delegated to caller.
        """
        # 1. Resolve template
        tpl = await self.get_template_by_codigo(template_codigo)
        if not tpl.is_active:
            raise TemplateInactiveError(
                f"Template '{template_codigo}' is inactive"
            )
        if not tpl.docx_path or not Path(tpl.docx_path).exists():  # pragma: no cover — stubs always present in dev
            raise TemplateFileMissingError(
                f"Template DOCX file not found for '{template_codigo}'"
            )

        # 1b. Workflow gate: políticas / procedimientos / entregables
        # require a frozen DdA. Commercial docs bypass.
        if enforce_gates:
            from backend.app.core.workflow_gates import (
                require_frozen_dda_if_needed,
            )
            await require_frozen_dda_if_needed(
                self.db, project_id, tpl.categoria
            )

        template_path = Path(tpl.docx_path)
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d_%H%M%S")

        # Output directory
        out_dir = _DOCUMENTS_DIR / str(project_id) / template_codigo
        out_dir.mkdir(parents=True, exist_ok=True)
        docx_out = out_dir / f"{template_codigo}_{ts}.docx"

        # 2. Render DOCX — M6-G1/G2: required_vars extraidos del dict
        # {name: {"description", "required"}} normalizado via catalog_loader.
        required_vars = None
        if tpl.placeholders_requeridos and isinstance(
            tpl.placeholders_requeridos, dict,
        ):
            required_vars = [
                k for k, v in tpl.placeholders_requeridos.items()
                if isinstance(v, dict) and v.get("required", False)
            ] or None
        # 2b. Resolve brand assets: download client logo from MinIO
        # if present, always include consultant wordmark.
        cliente_logo_tmp = await self._materialise_client_logo(project_id)

        # Sesión 3B-2B.4 Phase 4 · inject cliente branding extras (colors +
        # footer_text) en context para templates que los usen. Logo continúa
        # via cliente_logo_path param (existing _inject_brand pattern). Esta
        # adición es additive · templates existing 96 que NO usan colors/footer
        # render unchanged · OPS-026 DRY firmísimo.
        from backend.app.core.branding import build_branding_pdf_context
        branding_extras = await build_branding_pdf_context(self.db, project_id)
        context = {**context, "branding": branding_extras.template_dict()}
        # R14 · contexto de gobernanza org.2 (roles art.11 + comité + DPO +
        # numero_empleados + proxima_revision) como BASE: rellena huecos para que
        # E-002/E-003 y el anexo de roles de E-100 (R13) sean siempre rendibles,
        # sin sobreescribir lo que el caller ya provee (deep-merge · caller gana).
        # best-effort: build_governance_context NUNCA lanza.
        from backend.app.motors.m06_document_factory.governance_context import (
            build_governance_context,
            merge_governance_base,
        )
        gov_ctx = await build_governance_context(self.db, project_id)
        # P2 · `codigo_documento_base` es POR DOCUMENTO, asi que se pone aqui y
        # no en el contexto de gobernanza, que es por proyecto. 27 plantillas lo
        # declaran obligatorio y su valor es, sencillamente, el codigo de la
        # plantilla que se esta renderizando.
        gov_ctx.setdefault("proyecto", {}).setdefault(
            "codigo_documento_base", template_codigo,
        )
        context = merge_governance_base(gov_ctx, context)
        # Discard logo_path from branding helper (M06 ya tiene su propio
        # _materialise_client_logo · evita duplicate temp file).
        if branding_extras.logo_path and branding_extras.logo_path.exists():
            try:
                branding_extras.logo_path.unlink()
            except OSError:
                pass

        render_docx(
            template_path=template_path,
            context=context,
            output_path=docx_out,
            required_vars=required_vars,
            cliente_logo_path=cliente_logo_tmp,
            consultor_logo_path=_CONSULTOR_LOGO if _CONSULTOR_LOGO.exists() else None,
        )

        # 3. Sign
        rendered_hash = None
        signature_hex = None
        if sign:
            try:
                rendered_hash, signature_hex = sign_document(docx_out)
            except SigningError as exc:  # pragma: no cover — key missing in test env handled
                logger.warning("Signing failed (non-fatal): {}", exc)
                from backend.app.motors.m06_document_factory.signing import (
                    hash_sha256,
                )
                rendered_hash = hash_sha256(docx_out.read_bytes())
        else:
            from backend.app.motors.m06_document_factory.signing import (
                hash_sha256,
            )
            rendered_hash = hash_sha256(docx_out.read_bytes())

        # 4. Convert to PDF (optional)
        pdf_path = None
        pdf_warning = None
        if generate_pdf:
            try:
                pdf_result = convert_docx_to_pdf(docx_out, out_dir)
                pdf_path = str(pdf_result) if pdf_result else None
            except PDFConversionError as exc:
                pdf_warning = str(exc)
                logger.warning("PDF conversion failed (non-fatal): {}", exc)

        # 5. Persist Document record
        doc = Document(
            project_id=project_id,
            tipo=tpl.categoria,
            nombre=f"{tpl.codigo} - {tpl.nombre}",
            version_actual=tpl.version_actual,
            plantilla_id=tpl.id,
            estado=DocumentEstado.GENERADO.value,
            template_codigo=template_codigo,
            docx_path=str(docx_out),
            pdf_path=pdf_path,
            rendered_hash=rendered_hash,
            signature_ed25519=signature_hex,
            context_snapshot=context,
            generated_by=generated_by,
            generated_at=now,
        )
        self.db.add(doc)
        await self.db.flush()

        # 5b. #31 (G4 · FRENTE B): copia DURABLE en MinIO. Los docx_path/pdf_path
        # son rutas LOCALES efímeras (en prod un restart del contenedor las borra
        # → el cliente/auditor recibían 503 "Archivo no disponible (local://)").
        # Subimos el binario (PDF firmado si existe · DOCX si no) y fijamos el
        # storage_path canónico minio://{bucket}/{key} que m21/m24 saben servir.
        # Best-effort: si MinIO no está disponible (dev), la generación NO falla
        # (degradación graceful · OPS-049 honest path).
        try:
            durable_src = Path(pdf_path) if pdf_path else docx_out
            durable_bytes = durable_src.read_bytes()
            durable_ext = ".pdf" if pdf_path else ".docx"
            durable_mime = (
                "application/pdf" if pdf_path
                else "application/vnd.openxmlformats-officedocument."
                     "wordprocessingml.document"
            )
            object_key = (
                f"fulkro/projects/{project_id}/m06/"
                f"{(rendered_hash or 'nohash')[:12]}_{template_codigo}_{ts}"
                f"{durable_ext}"
            )
            from backend.app.core.storage.minio_client import (
                BUCKET_DOCUMENTS,
                put_object,
            )
            put_object(BUCKET_DOCUMENTS, object_key, durable_bytes, durable_mime)
            doc.storage_path = f"minio://{BUCKET_DOCUMENTS}/{object_key}"
            await self.db.flush()
        except Exception as exc:  # noqa: BLE001 — copia durable best-effort
            logger.warning(
                "m06 MinIO durable persist failed (non-fatal) · doc={} · {}",
                doc.id, exc,
            )

        # F-14-03: audit_log canónico de generación documental (Sub-atom 5.A
        # 3-way OR · best-effort · hash chain R6 preservada por trigger).
        await _emit_audit_log(
            self.db,
            project_id=str(project_id),
            client_id=None,
            accion="document.generated",
            registro_id=str(doc.id),
            usuario=generated_by or "system",
            payload={
                "template_codigo": template_codigo,
                "nombre": doc.nombre,
                "version": tpl.version_actual,
                "rendered_hash": rendered_hash,
                "signed": bool(signature_hex),
            },
        )

        return {
            "document_id": doc.id,
            "template_codigo": template_codigo,
            "nombre": doc.nombre,
            "docx_path": str(docx_out),
            "pdf_path": pdf_path,
            "storage_path": doc.storage_path,  # #31 · minio:// durable (o None)
            "rendered_hash": rendered_hash,
            "signature_ed25519": signature_hex,
            "estado": doc.estado,
            "generated_at": now,
            "pdf_warning": pdf_warning,
        }

    async def preview_render(
        self,
        template_codigo: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Preview which placeholders are filled/missing (ephemeral).

        Does NOT render the document. Just checks placeholder coverage.
        Trabaja sobre el dict {key: {description, required}} normalizado.
        """
        tpl = await self.get_template_by_codigo(template_codigo)

        required_keys: list[str] = []
        if tpl.placeholders_requeridos and isinstance(
            tpl.placeholders_requeridos, dict,
        ):
            required_keys = [
                k for k, v in tpl.placeholders_requeridos.items()
                if isinstance(v, dict) and v.get("required", False)
            ]

        context_top_keys = set(context.keys())
        provided = []
        missing = []

        for ph in required_keys:
            top_key = ph.split(".")[0]
            if top_key in context_top_keys:
                provided.append(ph)
            else:
                missing.append(ph)

        preview_ok = len(missing) == 0

        return {
            "template_codigo": template_codigo,
            "nombre": tpl.nombre,
            "placeholders_provided": provided,
            "placeholders_missing": missing,
            "preview_ok": preview_ok,
            "message": (
                "All required placeholders present"
                if preview_ok
                else f"Missing {len(missing)} required placeholder(s)"
            ),
        }

    # ================================================================
    # Document CRUD
    # ================================================================

    async def list_documents(
        self,
        project_id: UUID,
        estado: str | None = None,
        template_codigo: str | None = None,
    ) -> list[Document]:
        """List generated documents for a project."""
        conditions = [
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        ]
        if estado is not None:
            conditions.append(Document.estado == estado)
        if template_codigo is not None:
            conditions.append(Document.template_codigo == template_codigo)

        result = await self.db.execute(
            select(Document)
            .where(and_(*conditions))
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(self, document_id: UUID) -> Document:
        """Get a document by id. Raises DocumentNotFoundError."""
        doc = await self.db.get(Document, document_id)
        if doc is None or doc.deleted_at is not None:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return doc

    async def soft_delete_document(self, document_id: UUID) -> None:
        """Soft delete a document."""
        doc = await self.get_document(document_id)
        doc.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def mark_as_delivered(self, document_id: UUID) -> Document:
        """Mark a document as delivered."""
        doc = await self.get_document(document_id)
        doc.estado = DocumentEstado.ENTREGADO.value
        await self.db.flush()
        return doc

    # ================================================================
    # Dashboard
    # ================================================================

    async def get_dashboard(self, project_id: UUID) -> dict[str, Any]:
        """Document factory dashboard.

        Returns dashboard structure even if no documents exist (zeros, not 404).
        """
        docs = await self.list_documents(project_id)

        by_estado: dict[str, int] = {}
        by_template: dict[str, int] = {}
        latest_generation: datetime | None = None

        for d in docs:
            est = d.estado or "generado"
            by_estado[est] = by_estado.get(est, 0) + 1

            tc = d.template_codigo or "unknown"
            by_template[tc] = by_template.get(tc, 0) + 1

            if d.generated_at is not None:
                if latest_generation is None or d.generated_at > latest_generation:
                    latest_generation = d.generated_at

        # Template stats
        all_templates = await self.list_templates()
        active_templates = [t for t in all_templates if t.is_active]
        with_docx = [
            t
            for t in active_templates
            if t.docx_path and Path(t.docx_path).exists()
        ]

        # Catalog total
        try:
            catalog = load_catalog()
            total_catalog = get_total_templates(catalog)
        except CatalogLoadError:  # pragma: no cover — catalog always present in deployment
            total_catalog = 0

        return {
            "project_id": str(project_id),
            "total_documents": len(docs),
            "by_estado": by_estado,
            "by_template": by_template,
            "total_templates_catalog": total_catalog,
            "total_templates_active": len(active_templates),
            "templates_with_docx": len(with_docx),
            "latest_generation": latest_generation,
            "generated_at": datetime.now(timezone.utc),
        }
