"""Sub-atom 1.B.7.1.3 · Servicio de generación automática de adenda contractual E-604.

Cierra OPCION C hibrida del AMEND-014: dado un provider con sus
``normativas_aplicables`` (parametro · NO columna ORM existente · ver LECCION-OPS-029),
renderiza la plantilla E-604 con bloques condicionales (ENS siempre · RGPD/NIS2/DORA
segun flags), persiste el DOCX firmable a MinIO bucket fulkro-documents y crea fila
en provider_addendums con trazabilidad completa.

Adaptaciones audit-first vs architect VERBATIM (LECCION-OPS-029):
- Provider real ORM tiene: name + type + scope + criticality (NO razon_social/nif/
  normativas_aplicables/es_encargado_rgpd/metadata_). Service mapea name->razon_social,
  scope->servicio_descripcion, criticality->nivel_criticidad y acepta normativas_aplicables,
  nif, domicilio, representante, categoria_servicio_ens como parametros explicitos
  (provider_extras kwarg) en lugar de leerlos de columnas inexistentes.
- Client real ORM tiene: nombre + cif (NO razon_social/nif/domicilio/metadata_).
  Service mapea client.nombre->cliente.razon_social y client.cif->cliente.nif +
  acepta domicilio + representante + contacto_compliance como kwargs (client_extras).
- render_template_to_docx NO existe en m06 (solo render_docx file->file). Service
  resuelve template_path via deliverables/E604_*.md -> var/templates_docx/E-604.docx
  + escribe a tmp file + lee bytes.
- generate_signed_url NO existe. Service usa get_minio_client().presigned_get_object
  directo (patron heredado de m29_client_messaging/attachments.py).

Diseno:
- Servicio puro async · sin logica HTTP (eso vive en providers_api.py endpoint)
- Reusa m06_document_factory.render_docx existing
- MinIO object_key formato: corpus/addendums/{project_id}/{addendum_code}.docx
- addendum_code auto-gen formato: ADENDA-ENS-{YYYY}-{NNNN} si caller no lo aporta
- Idempotente: si addendum_code ya existe (UNIQUE constraint), devuelve existing

Usage:
    from backend.app.motors.m14_contracts.adenda_generator import AdendaGenerator

    gen = AdendaGenerator(db=session)
    result = await gen.generate(
        project_id=pid,
        provider_id=prid,
        normativas_aplicables=["ENS", "RGPD", "NIS2"],
        provider_extras={"nif": "B12345678", "domicilio": "..."},
    )
    # result = AdendaGenerationResult(addendum_id, minio_object_key, signed_url, ...)
"""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.storage.minio_client import (
    BUCKET_DOCUMENTS,
    get_minio_client,
    put_object,
)
from backend.app.models.core import Client, Project
from backend.app.models.m14_providers import Provider, ProviderAddendum
from backend.app.motors.m06_document_factory.rendering import render_docx


logger = logging.getLogger(__name__)


TEMPLATE_CODE = "E-604"
SIGNED_URL_TTL_SECONDS = 3600  # 1h default

# Path to the precompiled DOCX template (built via
# backend/scripts/build_proveedores_templates.py).
REPO_ROOT = Path(__file__).resolve().parents[4]
TEMPLATE_DOCX_PATH = REPO_ROOT / "var" / "templates_docx" / f"{TEMPLATE_CODE}.docx"


@dataclass
class AdendaGenerationResult:
    addendum_id: UUID
    addendum_code: str
    minio_object_key: str
    signed_url: str
    signed_url_expires_at: datetime
    normativas_cubiertas: list[str]
    docx_size_bytes: int
    generated_at: datetime
    template_code: str = TEMPLATE_CODE


class AdendaGenerator:
    """Auto-genera adenda contractual E-604 desde provider + project context."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self,
        project_id: UUID,
        provider_id: UUID,
        normativas_aplicables: list[str] | None = None,
        addendum_code: str | None = None,
        contract_ref: str | None = None,
        fecha_vigor: datetime | None = None,
        vencimiento: datetime | None = None,
        provider_extras: dict | None = None,
        client_extras: dict | None = None,
        signed_url_ttl: int = SIGNED_URL_TTL_SECONDS,
    ) -> AdendaGenerationResult:
        # 1. Resolver entidades · provider · client · project
        provider, project, client = await self._load_entities(project_id, provider_id)

        # 2. Resolver normativas (default ENS solo)
        normativas = list(normativas_aplicables) if normativas_aplicables else ["ENS"]

        # 3. Resolver addendum_code (auto-gen si null)
        code = addendum_code or await self._next_addendum_code(project_id)

        # 4. Idempotencia · si ya existe row con (project_id, addendum_code), devuelve existing
        existing = await self._find_existing(project_id, code)
        if existing is not None:
            return await self._result_from_existing(existing, signed_url_ttl)

        # 5. Construir context Jinja2
        context = self._build_context(
            provider=provider,
            project=project,
            client=client,
            addendum_code=code,
            contract_ref=contract_ref,
            fecha_vigor=fecha_vigor,
            vencimiento=vencimiento,
            normativas=normativas,
            provider_extras=provider_extras or {},
            client_extras=client_extras or {},
        )

        # 6. Render template E-604 -> DOCX bytes (via tmp file · render_docx file-based)
        if not TEMPLATE_DOCX_PATH.exists():
            raise FileNotFoundError(
                f"Precompiled template not found: {TEMPLATE_DOCX_PATH}. "
                f"Run: PYTHONPATH=. .venv/bin/python "
                f"backend/scripts/build_proveedores_templates.py"
            )
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            render_docx(TEMPLATE_DOCX_PATH, context, tmp_path)
            docx_bytes = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

        # 7. Upload a MinIO bucket fulkro-documents
        object_key = f"corpus/addendums/{project_id}/{code}.docx"
        put_object(
            bucket=BUCKET_DOCUMENTS,
            key=object_key,
            data=docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            metadata={
                "addendum_code": code,
                "template_code": TEMPLATE_CODE,
                "provider_id": str(provider_id),
                "project_id": str(project_id),
            },
        )

        # 8. INSERT row provider_addendums
        addendum_id = uuid4()
        now = datetime.now(timezone.utc)
        new_addendum = ProviderAddendum(
            id=addendum_id,
            project_id=project_id,
            provider_id=provider_id,
            addendum_code=code,
            contract_ref=contract_ref,
            normativas_cubiertas=normativas,
            fecha_vigor=fecha_vigor.date() if fecha_vigor else None,
            vencimiento=vencimiento.date() if vencimiento else None,
            firmado_cliente=False,
            firmado_proveedor=False,
            minio_object_key=object_key,
            generated_from_template_code=TEMPLATE_CODE,
            metadata_={
                "generated_at": now.isoformat(),
                "docx_size_bytes": len(docx_bytes),
                "generator_version": "1.B.7.1.3",
                "provider_extras": provider_extras or {},
                "client_extras": client_extras or {},
            },
        )
        self.db.add(new_addendum)
        await self.db.flush()

        # 9. Build signed URL via MinIO presigned_get_object directo
        signed_url, expires_at = self._presigned_url(object_key, signed_url_ttl)

        logger.info(
            "Generated addendum %s for provider %s (project %s) %d bytes normativas=%s",
            code, provider_id, project_id, len(docx_bytes), normativas,
        )

        return AdendaGenerationResult(
            addendum_id=addendum_id,
            addendum_code=code,
            minio_object_key=object_key,
            signed_url=signed_url,
            signed_url_expires_at=expires_at,
            normativas_cubiertas=normativas,
            docx_size_bytes=len(docx_bytes),
            generated_at=now,
        )

    # ----------------------- helpers privados -----------------------

    async def _load_entities(
        self, project_id: UUID, provider_id: UUID,
    ) -> tuple[Provider, Project, Client]:
        provider_res = await self.db.execute(
            select(Provider).where(
                Provider.id == provider_id,
                Provider.project_id == project_id,
                Provider.deleted_at.is_(None),
            )
        )
        provider = provider_res.scalar_one_or_none()
        if provider is None:
            raise ValueError(
                f"Provider {provider_id} no encontrado en project {project_id}"
            )

        project_res = await self.db.execute(select(Project).where(Project.id == project_id))
        project = project_res.scalar_one()

        client_res = await self.db.execute(select(Client).where(Client.id == project.client_id))
        client = client_res.scalar_one()

        return provider, project, client

    async def _next_addendum_code(self, project_id: UUID) -> str:
        """Auto-gen formato ADENDA-ENS-YYYY-NNNN secuencial por project."""
        year = datetime.now(timezone.utc).year
        prefix = f"ADENDA-ENS-{year}-"
        res = await self.db.execute(
            select(ProviderAddendum.addendum_code).where(
                ProviderAddendum.project_id == project_id,
                ProviderAddendum.addendum_code.startswith(prefix),
            )
        )
        existing_codes = [row[0] for row in res.all()]
        next_n = len(existing_codes) + 1
        return f"{prefix}{next_n:04d}"

    async def _find_existing(
        self, project_id: UUID, addendum_code: str,
    ) -> ProviderAddendum | None:
        res = await self.db.execute(
            select(ProviderAddendum).where(
                ProviderAddendum.project_id == project_id,
                ProviderAddendum.addendum_code == addendum_code,
                ProviderAddendum.deleted_at.is_(None),
            )
        )
        return res.scalar_one_or_none()

    async def _result_from_existing(
        self, addendum: ProviderAddendum, signed_url_ttl: int,
    ) -> AdendaGenerationResult:
        signed_url, expires_at = self._presigned_url(addendum.minio_object_key, signed_url_ttl)
        meta = addendum.metadata_ or {}
        return AdendaGenerationResult(
            addendum_id=addendum.id,
            addendum_code=addendum.addendum_code,
            minio_object_key=addendum.minio_object_key,
            signed_url=signed_url,
            signed_url_expires_at=expires_at,
            normativas_cubiertas=list(addendum.normativas_cubiertas or []),
            docx_size_bytes=meta.get("docx_size_bytes", 0),
            generated_at=addendum.created_at,
        )

    def _presigned_url(self, object_key: str, ttl_seconds: int) -> tuple[str, datetime]:
        """Genera presigned GET URL usando minio.presigned_get_object directo."""
        client = get_minio_client()
        url = client.presigned_get_object(
            bucket_name=BUCKET_DOCUMENTS,
            object_name=object_key,
            expires=timedelta(seconds=ttl_seconds),
        )
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        return url, expires_at

    def _build_context(
        self,
        *,
        provider: Provider,
        project: Project,
        client: Client,
        addendum_code: str,
        contract_ref: str | None,
        fecha_vigor: datetime | None,
        vencimiento: datetime | None,
        normativas: list[str],
        provider_extras: dict,
        client_extras: dict,
    ) -> dict:
        now_iso = datetime.now(timezone.utc).date().isoformat()
        return {
            "documento": {
                "codigo": TEMPLATE_CODE,
                "version": "1.0",
                "fecha_emision": now_iso,
            },
            "cliente": {
                # Map real ORM (nombre, cif) -> template (razon_social, nif).
                "razon_social": client.nombre,
                "nif": client.cif,
                "domicilio": client_extras.get("domicilio"),
                "representante": client_extras.get("representante"),
                "contacto_compliance": client_extras.get("contacto_compliance"),
                "project_id": str(project.id),
            },
            "proveedor": {
                "id": str(provider.id),
                # Map real ORM (name, scope, criticality) -> template
                # (razon_social, servicio_descripcion, nivel_criticidad).
                "razon_social": provider.name,
                "nif": provider_extras.get("nif"),
                "domicilio": provider_extras.get("domicilio"),
                "representante": provider_extras.get("representante"),
                "servicio_descripcion": provider.scope,
                "nivel_criticidad": provider.criticality,
                "categoria_servicio_ens": provider_extras.get("categoria_servicio_ens"),
                "normativas_aplicables": normativas,
            },
            "adenda": {
                "addendum_code": addendum_code,
                "contract_ref": contract_ref,
                "fecha_vigor": fecha_vigor.date().isoformat() if fecha_vigor else now_iso,
                "vencimiento": vencimiento.date().isoformat() if vencimiento else None,
                "notificacion_horas": 24,
                "notificacion_horas_rgpd": 24,
                "notificacion_horas_nis2": 12,
            },
            "contrato_base": {
                "fecha": None,
                "objeto": None,
            },
        }
