"""ThreatAutoMapper service (ADR-037 SAN-D MB-15.2).

Auto-genera ``MageritThreatAssessment`` rows linking catalog
``MageritThreat`` (looked up by ``code``) a assets del proyecto via
``MageritAsset.id``. Reduce trabajo manual M02 risk analysis para
proyectos con muchos activos.

Pipeline:
1. Resolver/crear ``MageritAnalysis`` para el proyecto.
2. Load Libro II catalog (yaml docs/magerit_catalog/threats.yaml).
3. Por cada ``MageritAsset`` (analysis_id), lookup threats catalog
   matching ``asset_type_code`` ∈ ``threat.asset_types``.
4. Crear ``MageritThreatAssessment(analysis_id, asset_id, threat_code,
   probability)`` con default probability derivado de
   ``typical_frequency``.
5. Skip rows already existentes (idempotente).

Default probability per MAGERIT scale MB/B/M/A/MA (ver
``frequency_to_probability``). Caller puede override post-mapping.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project
from backend.app.motors.m02_magerit.libro_ii_loader import (
    frequency_to_probability,
    get_threats_for_asset_type,
    load_libro_ii,
)
from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritThreatAssessment,
)


class ThreatAutoMapper:
    """Auto-mapper amenazas Libro II per asset inventario."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_map_threats_for_project(
        self,
        project_id: UUID,
        analysis_id: UUID | None = None,
    ) -> dict:
        """Auto-mapea amenazas para todos los assets del proyecto.

        Args:
            project_id: proyecto target.
            analysis_id: análisis específico opcional · si None, usa
                el análisis más reciente del proyecto · si no existe,
                crea uno nuevo (lightweight).

        Returns:
            dict con `created` · `skipped` · `analysis_id` · `assets_processed`.
        """
        project = await self.db.get(Project, project_id)
        if not project:
            return {
                "created": 0,
                "skipped": 0,
                "analysis_id": None,
                "assets_processed": 0,
                "error": "project_not_found",
            }

        analysis = await self._resolve_or_create_analysis(
            project_id=project_id, analysis_id=analysis_id,
        )

        assets = (
            await self.db.execute(
                select(MageritAsset)
                .where(MageritAsset.analysis_id == analysis.id)
                .where(MageritAsset.deleted_at.is_(None))
            )
        ).scalars().all()
        assets = list(assets)

        catalog = load_libro_ii()  # lru_cache
        # catalog usage downstream via get_threats_for_asset_type
        _ = catalog

        created = 0
        skipped = 0

        # Pre-cargar assessments existentes para idempotencia
        existing_keys: set[tuple[UUID, str]] = set()
        existing_rows = (
            await self.db.execute(
                select(
                    MageritThreatAssessment.asset_id,
                    MageritThreatAssessment.threat_code,
                )
                .where(MageritThreatAssessment.analysis_id == analysis.id)
            )
        ).all()
        for row in existing_rows:
            existing_keys.add((row[0], row[1]))

        for asset in assets:
            applicable = get_threats_for_asset_type(asset.asset_type_code)
            for threat in applicable:
                key = (asset.id, threat.code)
                if key in existing_keys:
                    skipped += 1
                    continue

                probability = frequency_to_probability(threat.typical_frequency)
                assessment = MageritThreatAssessment(
                    analysis_id=analysis.id,
                    asset_id=asset.id,
                    threat_code=threat.code,
                    probability=probability,
                )
                self.db.add(assessment)
                created += 1

        await self.db.flush()

        return {
            "created": created,
            "skipped": skipped,
            "analysis_id": analysis.id,
            "assets_processed": len(assets),
        }

    async def _resolve_or_create_analysis(
        self,
        project_id: UUID,
        analysis_id: UUID | None,
    ) -> MageritAnalysis:
        if analysis_id:
            analysis = await self.db.get(MageritAnalysis, analysis_id)
            if analysis and analysis.project_id == project_id:
                return analysis

        # Buscar último análisis del proyecto
        latest = (
            await self.db.execute(
                select(MageritAnalysis)
                .where(MageritAnalysis.project_id == project_id)
                .where(MageritAnalysis.deleted_at.is_(None))
                .order_by(MageritAnalysis.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest:
            return latest

        # Crear lightweight para auto-mapping (DEC-MAGERIT-2 ADR-037)
        new_analysis = MageritAnalysis(
            project_id=project_id,
            name="Análisis auto-generado (ThreatAutoMapper)",
            version=1,
            status="draft",
            calculation_mode="qualitative",
        )
        self.db.add(new_analysis)
        await self.db.flush()
        await self.db.refresh(new_analysis)
        return new_analysis
