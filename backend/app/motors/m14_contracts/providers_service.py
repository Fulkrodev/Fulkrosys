"""M14 Providers + C-002 service · ADR-046 v3 SAN-E.MB-3.B.

Auto-detect cross-compliance al crear proveedor:
- type=cloud o saas + criticality=CRITICO/ALTO → ENS Art 18 + GDPR Art 28
- type=cloud + criticality=CRITICO → +NIS2 article 21 review

Operaciones:
- list_providers / create_provider / delete_provider (soft)
- get_c002_status / get_gaps / generate_c002 / mark_reviewed
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.m14_providers import Provider, ProviderAddendum, ProviderC002


class ProvidersError(Exception):
    pass


@dataclass
class GapEntry:
    framework: str
    article: str
    severity: str
    description: str
    suggested_clause: str

    def to_dict(self) -> dict:
        return {
            "framework": self.framework,
            "article": self.article,
            "severity": self.severity,
            "description": self.description,
            "suggested_clause": self.suggested_clause,
        }


def detect_cross_compliance_gaps(provider_type: str, criticality: str) -> list[GapEntry]:
    """Auto-deteccion clausulas requeridas segun tipo y criticidad."""
    gaps: list[GapEntry] = []
    high_risk = criticality in ("CRITICO", "ALTO")
    cloud_or_saas = provider_type in ("cloud", "saas")

    if cloud_or_saas and high_risk:
        gaps.append(GapEntry(
            framework="ENS",
            article="Art. 18",
            severity="ALTA",
            description="Encadenamiento medidas seguridad y nivel cumplimiento (ENS RD 311/2022).",
            suggested_clause="C-002.ENS-18 · subcontratista debe declarar nivel ENS y heredar medidas equivalentes.",
        ))
        gaps.append(GapEntry(
            framework="GDPR",
            article="Art. 28",
            severity="ALTA",
            description="Encargado tratamiento · clausulas obligatorias contratos (RGPD).",
            suggested_clause="C-002.RGPD-28 · objeto, duracion, naturaleza, finalidad tratamiento, instrucciones documentadas, confidencialidad, seguridad, sub-encargados, asistencia, eliminacion, auditoria.",
        ))
    if provider_type == "cloud" and criticality == "CRITICO":
        gaps.append(GapEntry(
            framework="NIS2",
            article="Art. 21",
            severity="CRITICA",
            description="Gestion riesgos cadena suministro (NIS2 transposicion).",
            suggested_clause="C-002.NIS2-21 · obligacion notificacion incidentes 24h al servicio receptor + auditoria anual cadena suministro.",
        ))
    return gaps


@dataclass
class ProviderDTO:
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    type: str
    scope: str
    criticality: str
    last_reviewed_at: datetime | None
    last_reviewed_by: str | None
    c002_status: str
    gaps_count: int

    @classmethod
    def from_orm(cls, row: Provider, c002: ProviderC002 | None) -> "ProviderDTO":
        gaps = c002.gaps_json if (c002 and c002.gaps_json) else []
        return cls(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            type=row.type,
            scope=row.scope,
            criticality=row.criticality,
            last_reviewed_at=row.last_reviewed_at,
            last_reviewed_by=row.last_reviewed_by,
            c002_status=c002.status if c002 else "pendiente",
            gaps_count=len(gaps),
        )


class M14ProvidersService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_c002(self, provider_id: uuid.UUID) -> ProviderC002 | None:
        return (await self.db.execute(
            select(ProviderC002).where(
                ProviderC002.provider_id == provider_id,
                ProviderC002.deleted_at.is_(None),
            )
        )).scalar_one_or_none()

    async def list_providers(self, project_id: uuid.UUID) -> list[ProviderDTO]:
        rows = (await self.db.execute(
            select(Provider)
            .where(
                Provider.project_id == project_id,
                Provider.deleted_at.is_(None),
            )
            .order_by(Provider.criticality, Provider.name)
        )).scalars().all()
        out: list[ProviderDTO] = []
        for r in rows:
            c002 = await self._get_c002(r.id)
            out.append(ProviderDTO.from_orm(r, c002))
        return out

    async def create_provider(
        self,
        project_id: uuid.UUID,
        name: str,
        type: str,
        scope: str,
        criticality: str,
    ) -> tuple[ProviderDTO, list[GapEntry]]:
        if type not in ("cloud", "saas", "on-prem", "staffing", "hardware", "consultoria"):
            raise ProvidersError(f"Tipo invalido: {type}")
        if criticality not in ("CRITICO", "ALTO", "MEDIO", "BAJO"):
            raise ProvidersError(f"Criticidad invalida: {criticality}")
        provider = Provider(
            project_id=project_id,
            name=name,
            type=type,
            scope=scope,
            criticality=criticality,
        )
        self.db.add(provider)
        await self.db.flush()

        gaps = detect_cross_compliance_gaps(type, criticality)
        c002 = ProviderC002(
            provider_id=provider.id,
            status="pendiente",
            gaps_json=[g.to_dict() for g in gaps] if gaps else None,
            last_gap_check_at=datetime.now(timezone.utc) if gaps else None,
        )
        self.db.add(c002)
        await self.db.flush()
        return ProviderDTO.from_orm(provider, c002), gaps

    async def get_provider(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> Provider:
        row = (await self.db.execute(
            select(Provider).where(
                Provider.id == provider_id,
                Provider.project_id == project_id,
                Provider.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if row is None:
            raise ProvidersError(f"Provider {provider_id} not found en project {project_id}")
        return row

    async def _get_latest_addendum(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> ProviderAddendum | None:
        """Última adenda E-604 generada para el proveedor: el artefacto REAL que
        materializa la cláusula C-002 (vive en el bucket fulkro-documents)."""
        return (await self.db.execute(
            select(ProviderAddendum)
            .where(
                ProviderAddendum.project_id == project_id,
                ProviderAddendum.provider_id == provider_id,
                ProviderAddendum.deleted_at.is_(None),
            )
            .order_by(ProviderAddendum.created_at.desc())
            .limit(1)
        )).scalars().first()

    async def get_c002_status(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> dict:
        await self.get_provider(project_id, provider_id)
        c002 = await self._get_c002(provider_id)
        addendum = await self._get_latest_addendum(project_id, provider_id)
        # M8 · el artefacto REAL de la C-002 es la adenda E-604 (ProviderAddendum,
        # bucket fulkro-documents). `evidence_id` (FK a la tabla m07 `evidence`)
        # NO aplica a este flujo —una adenda contractual no es evidencia ENS de
        # m07/WORM— y permanece null a propósito; la trazabilidad documental se
        # expone vía addendum_id + minio_object_key (antes la status sólo
        # mostraba evidence_id=null y parecía que no había documento).
        addendum_block = {
            "addendum_id": str(addendum.id) if addendum else None,
            "addendum_code": addendum.addendum_code if addendum else None,
            "minio_object_key": addendum.minio_object_key if addendum else None,
        }
        if c002 is None:
            return {
                "provider_id": str(provider_id),
                "status": "pendiente",
                "generated_at": None,
                "evidence_id": None,
                **addendum_block,
            }
        return {
            "provider_id": str(provider_id),
            "status": c002.status,
            "generated_at": c002.generated_at.isoformat() if c002.generated_at else None,
            "evidence_id": str(c002.evidence_id) if c002.evidence_id else None,
            **addendum_block,
        }

    async def get_gaps(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> dict:
        provider = await self.get_provider(project_id, provider_id)
        c002 = await self._get_c002(provider_id)
        # Recalcular gaps en cada query (refresca si type/criticality cambio)
        gaps = detect_cross_compliance_gaps(provider.type, provider.criticality)
        if c002 is not None:
            c002.gaps_json = [g.to_dict() for g in gaps] if gaps else None
            c002.last_gap_check_at = datetime.now(timezone.utc)
            await self.db.flush()
        return {
            "provider_id": str(provider_id),
            "gaps": [g.to_dict() for g in gaps],
            "gaps_count": len(gaps),
            "last_gap_check_at": (
                c002.last_gap_check_at.isoformat() if c002 and c002.last_gap_check_at else None
            ),
        }

    async def generate_c002(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> dict:
        """Genera el documento REAL de la cláusula de seguridad C-002 (adenda
        E-604) vía AdendaGenerator: render DOCX + upload MinIO + fila
        ProviderAddendum. Antes solo ponía ``status='firmado'`` SIN producir nada
        (firma fingida · hueco de trazabilidad ENS/ENAC). El estado pasa a
        'generado' (NO 'firmado': la firma real es un paso aparte sobre la adenda).
        """
        provider = await self.get_provider(project_id, provider_id)
        c002 = await self._get_c002(provider_id)
        if c002 is None:
            raise ProvidersError("ProviderC002 row missing · provider state corrupt")

        # Normativas a materializar = frameworks de los gaps detectados.
        gaps = detect_cross_compliance_gaps(provider.type, provider.criticality)
        framework_to_normativa = {
            "ENS": "ENS", "GDPR": "RGPD", "NIS2": "NIS2", "DORA": "DORA",
        }
        normativas = sorted({
            framework_to_normativa.get(g.framework, g.framework) for g in gaps
        }) or ["ENS"]

        from backend.app.motors.m14_contracts.adenda_generator import (
            AdendaGenerator,
        )
        result = await AdendaGenerator(self.db).generate(
            project_id=project_id,
            provider_id=provider_id,
            normativas_aplicables=normativas,
        )

        c002.status = "generado"
        c002.generated_at = result.generated_at
        c002.gaps_json = [g.to_dict() for g in gaps] if gaps else None
        c002.last_gap_check_at = datetime.now(timezone.utc)
        await self.db.flush()
        return {
            "provider_id": str(provider_id),
            "status": c002.status,
            "generated_at": c002.generated_at.isoformat(),
            "covered_gaps": c002.gaps_json or [],
            "addendum_id": str(result.addendum_id),
            "addendum_code": result.addendum_code,
            "minio_object_key": result.minio_object_key,
            "signed_url": result.signed_url,
        }

    async def mark_reviewed(
        self,
        project_id: uuid.UUID,
        provider_id: uuid.UUID,
        user_id: str | None,
    ) -> dict:
        provider = await self.get_provider(project_id, provider_id)
        provider.last_reviewed_at = datetime.now(timezone.utc)
        provider.last_reviewed_by = user_id
        await self.db.flush()
        return {
            "provider_id": str(provider_id),
            "last_reviewed_at": provider.last_reviewed_at.isoformat(),
            "last_reviewed_by": provider.last_reviewed_by,
        }

    async def delete_provider(
        self, project_id: uuid.UUID, provider_id: uuid.UUID,
    ) -> None:
        provider = await self.get_provider(project_id, provider_id)
        provider.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
