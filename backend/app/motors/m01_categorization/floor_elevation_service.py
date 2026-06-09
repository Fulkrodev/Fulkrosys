"""#5 cabo · Orquestador de elevación del suelo AAPP con guard por nivel.

Al fijar/elevar el suelo heredado de la AAPP (`projects.categoria_heredada_aapp`),
`categoria_objetivo` solo puede SUBIR (Variante 2). Pero subirlo TARDE, cuando
ya hay artefactos downstream (propuesta/contrato/plan/factura), los dejaría
incoherentes — y un contrato firmado es FÍSICAMENTE INMUTABLE. Este orquestador
decide qué pasa según el estado de esos artefactos, con prioridad:

    N3   contrato FIRMADO (firmado_cliente_at) o factura emitida (verifactu_hash)
         -> BLOQUEA 409 · constancia en contract.adendas · JAMÁS toca lo firmado.
    N2.5 contrato EN VUELO (firmado_marcos/sent, SIN firma cliente)
         -> BLOQUEA · hay que RETIRAR el contrato (revocar magic-link) antes.
    N2   borradores (propuesta/plan/contrato draft, sin firma)
         -> ELEVA + regenera los 3 a la categoría nueva (no hay firma que proteger).
    N1   sin artefactos
         -> ELEVA libre.

"Atado" = la incoherencia es imposible y queda constancia; NUNCA = el sistema
regenera lo firmado ni genera adendas automáticas (eso es Future-X dedicado).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import Contract
from backend.app.models.core import Project
from backend.app.motors.m01_categorization.service import elevate_to_floor


class FloorElevationError(Exception):
    """Error base del orquestador."""


class InFlightContractError(FloorElevationError):
    """N2.5 · contrato en vuelo · retíralo (revoca su magic-link) antes de elevar."""


class SignedContractError(FloorElevationError):
    """N3 · contrato firmado o factura emitida · requiere vía formal (nuevo
    contrato/adenda) · lo firmado no se toca."""


@dataclass
class FloorElevationResult:
    level: str
    categoria_heredada_aapp: str | None
    categoria_objetivo: str | None
    categoria_objetivo_elevated: bool
    regenerated: list[str] = field(default_factory=list)


async def detect_level(db: AsyncSession, project_id: uuid.UUID) -> str:
    """Detecta el nivel del proyecto (prioridad N3 > N2.5 > N2 > N1)."""
    pid = {"p": str(project_id)}
    firmados = (await db.execute(text(
        "SELECT 1 FROM contracts WHERE project_id = :p AND deleted_at IS NULL "
        "AND firmado_cliente_at IS NOT NULL LIMIT 1"), pid)).first()
    facturas = (await db.execute(text(
        "SELECT 1 FROM invoices WHERE project_id = :p AND deleted_at IS NULL "
        "AND verifactu_hash IS NOT NULL LIMIT 1"), pid)).first()
    if firmados or facturas:
        return "N3"
    en_vuelo = (await db.execute(text(
        "SELECT 1 FROM contracts WHERE project_id = :p AND deleted_at IS NULL "
        "AND firmado_cliente_at IS NULL AND estado IN ('firmado_marcos','sent') "
        "LIMIT 1"), pid)).first()
    if en_vuelo:
        return "N2.5"
    borradores = (
        (await db.execute(text(
            "SELECT 1 FROM proposals WHERE project_id = :p AND deleted_at IS NULL "
            "LIMIT 1"), pid)).first()
        or (await db.execute(text(
            "SELECT 1 FROM project_plans WHERE project_id = :p AND deleted_at IS NULL "
            "LIMIT 1"), pid)).first()
        or (await db.execute(text(
            "SELECT 1 FROM contracts WHERE project_id = :p AND deleted_at IS NULL "
            "AND estado = 'draft' LIMIT 1"), pid)).first()
    )
    return "N2" if borradores else "N1"


async def _record_blocked_attempt(
    db: AsyncSession, project_id: uuid.UUID, before: str | None, floor: str | None,
) -> None:
    """N3 · anexa la constancia del intento al contrato firmado (campo de
    auditoría `adendas`). NUNCA toca documento_sha256/firma/firmado_cliente_at."""
    res = await db.execute(
        select(Contract).where(
            Contract.project_id == project_id,
            Contract.firmado_cliente_at.isnot(None),
            Contract.deleted_at.is_(None),
        ).order_by(Contract.firmado_cliente_at.desc())
    )
    c = res.scalars().first()
    if c is None:
        return  # factura sin contrato firmado · no hay contrato donde anotar
    adendas = c.adendas if isinstance(c.adendas, dict) else {}
    intentos = adendas.get("intentos_elevacion_bloqueados")
    if not isinstance(intentos, list):
        intentos = []
    intentos.append({
        "tipo": "intento_elevacion_categoria_bloqueado",
        "categoria_contrato": before,
        "suelo_aapp": floor,
        "at": datetime.now(timezone.utc).isoformat(),
        "via_formal": "requiere nuevo contrato/adenda · el firmado no se toca",
    })
    adendas["intentos_elevacion_bloqueados"] = intentos
    c.adendas = adendas
    await db.flush()


async def _regenerate_drafts(
    db: AsyncSession, project_id: uuid.UUID, new_categoria: str,
) -> list[str]:
    """N2 · regenera los borradores (propuesta + plan + gap) a la categoría
    nueva. Sin snapshots stale (no hay firma que proteger)."""
    regenerated: list[str] = []

    from backend.app.motors.m13_commercial.proposal_service import ProposalService
    prop = await ProposalService().regenerate_for_categoria(
        db, project_id, new_categoria,
    )
    if prop is not None:
        regenerated.append("propuesta")

    from backend.app.motors.m17_planning.planning_service import (
        PlanningError,
        replan,
    )
    try:
        await replan(db, project_id, new_categoria)
        regenerated.append("plan")
    except PlanningError:
        pass  # no había plan que regenerar

    from backend.app.motors.m04_gap.service import GapAnalysisService
    from backend.app.motors.m04_gap.exceptions import (
        DdANotReadyError,
        GapAlreadyAnalyzedError,
    )
    try:
        await GapAnalysisService(db).analyze_project(
            project_id, force=True, categoria_objetivo=new_categoria,
        )
        regenerated.append("gap")
    except (GapAlreadyAnalyzedError, DdANotReadyError, ValueError):
        pass  # gap puede no aplicar (sin DdA) · best-effort
    return regenerated


async def elevate_inherited_floor(
    db: AsyncSession, project_id: uuid.UUID, floor: str | None,
) -> FloorElevationResult:
    """Fija el suelo AAPP y eleva `categoria_objetivo` con guard por nivel.

    Commitea internamente en los caminos permitidos (y en N3 para persistir la
    constancia antes de lanzar el 409). Lanza InFlightContractError (N2.5) /
    SignedContractError (N3) cuando la elevación debe bloquearse.
    """
    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise FloorElevationError("Proyecto no encontrado")

    before = project.categoria_objetivo
    target = elevate_to_floor(before, floor)
    would_elevate = target != before
    level = await detect_level(db, project_id)

    # Los bloqueos solo aplican si la operación ELEVARÍA la categoría.
    if would_elevate and level == "N3":
        # Constancia primero (se persiste), luego 409 · el floor NO se guarda.
        await _record_blocked_attempt(db, project_id, before, floor)
        await db.commit()
        raise SignedContractError(
            f"El proyecto tiene contrato firmado (o factura emitida) en categoría "
            f"{before}. No puede elevarse a {floor} sin un nuevo contrato/adenda: "
            f"el documento firmado no se toca. El intento quedó registrado."
        )

    if would_elevate and level == "N2.5":
        # NO se muta nada · el cliente no debe firmar el contrato obsoleto.
        raise InFlightContractError(
            f"Hay un contrato EN VUELO (enviado al cliente, sin su firma) en "
            f"categoría {before}. Retíralo/anúlalo antes de elevar a {floor}, "
            f"para que el cliente no firme el contrato obsoleto."
        )

    # N1 (libre) · N2 (eleva + regenera) · o sin elevación (solo guarda el floor).
    project.categoria_heredada_aapp = floor
    project.categoria_objetivo = target
    regenerated: list[str] = []
    if would_elevate and level == "N2":
        regenerated = await _regenerate_drafts(db, project_id, target)
    await db.commit()
    await db.refresh(project)

    return FloorElevationResult(
        level=level,
        categoria_heredada_aapp=project.categoria_heredada_aapp,
        categoria_objetivo=project.categoria_objetivo,
        categoria_objetivo_elevated=would_elevate,
        regenerated=regenerated,
    )
