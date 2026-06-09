"""Motor 19 — Project Risk Management — service.

Implements CRUD for ProjectRisk + catalog instantiation.
Lifecycle transitions and dashboard are added in 18.3-B.

Pattern: consistent with M12 Magic Link and M3 DdA Engine.
- async methods with AsyncSession
- raise specific exceptions from exceptions module
- no internal commits (delegate to caller)
- RLS enforced via set_tenant_context in middleware/endpoint
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.planning import ProjectRisk
from backend.app.motors.m19_risk.catalog_loader import (
    load_catalog,
    catalog_to_project_risk_data,
    get_catalog_version,
    VALID_CATEGORIES,
    VALID_STATUS,
)
from backend.app.motors.m19_risk.exceptions import (
    ProjectRiskNotFoundError,
    ProjectRiskValidationError,
    ProjectRiskStateError,
    CatalogAlreadyInstantiatedError,
)


class ProjectRiskService:
    """Service for managing project risks (Motor 19).

    All methods are async. Commits delegated to caller.
    RLS enforced via tenant context set before calling service.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ================================================================
    # CRUD — Create / Read / Update / Delete
    # ================================================================

    async def create_risk(
        self,
        project_id: UUID,
        risk_code: str,
        titulo: str,
        descripcion: str | None = None,
        categoria: str | None = None,
        probabilidad: float | None = None,
        impacto_dias: int | None = None,
        impacto_euros: float | None = None,
        owner: str | None = None,
        trigger_condicion: str | None = None,
        mitigation_plan: dict[str, Any] | None = None,
        contingency_plan: dict[str, Any] | None = None,
        status: str = "identificado",
    ) -> ProjectRisk:
        """Create a new project risk manually.

        Raises ProjectRiskValidationError if status or categoria invalid.
        """
        if status not in VALID_STATUS:
            raise ProjectRiskValidationError(
                f"Invalid status: {status} (valid: {VALID_STATUS})"
            )
        if categoria is not None and categoria not in VALID_CATEGORIES:
            raise ProjectRiskValidationError(
                f"Invalid categoria: {categoria} (valid: {VALID_CATEGORIES})"
            )
        if probabilidad is not None and not (0.0 <= probabilidad <= 1.0):
            raise ProjectRiskValidationError(
                f"probabilidad must be in [0.0, 1.0], got {probabilidad}"
            )

        risk = ProjectRisk(
            project_id=project_id,
            risk_code=risk_code,
            titulo=titulo,
            descripcion=descripcion,
            categoria=categoria,
            probabilidad=probabilidad,
            impacto_dias=impacto_dias,
            impacto_euros=impacto_euros,
            owner=owner,
            trigger_condicion=trigger_condicion,
            mitigation_plan=mitigation_plan,
            contingency_plan=contingency_plan,
            status=status,
        )
        self.db.add(risk)
        await self.db.flush()
        return risk

    async def get_risk(self, risk_id: UUID) -> ProjectRisk:
        """Get a project risk by id. Raises ProjectRiskNotFoundError."""
        risk = await self.db.get(ProjectRisk, risk_id)
        if risk is None or risk.deleted_at is not None:
            raise ProjectRiskNotFoundError(f"Project risk {risk_id} not found")
        return risk

    async def list_risks(
        self,
        project_id: UUID,
        status: str | None = None,
        categoria: str | None = None,
        owner: str | None = None,
    ) -> list[ProjectRisk]:
        """List all risks of a project with optional filters."""
        conditions = [
            ProjectRisk.project_id == project_id,
            ProjectRisk.deleted_at.is_(None),
        ]
        if status is not None:
            conditions.append(ProjectRisk.status == status)
        if categoria is not None:
            conditions.append(ProjectRisk.categoria == categoria)
        if owner is not None:
            conditions.append(ProjectRisk.owner == owner)

        result = await self.db.execute(
            select(ProjectRisk)
            .where(and_(*conditions))
            .order_by(ProjectRisk.risk_code)
        )
        return list(result.scalars().all())

    async def update_risk(
        self,
        risk_id: UUID,
        **fields: Any,
    ) -> ProjectRisk:
        """Partial update of a project risk.

        Immutable fields (id, project_id, risk_code, created_at) are ignored.
        """
        immutable = {"id", "project_id", "risk_code", "created_at"}

        risk = await self.get_risk(risk_id)

        if "categoria" in fields and fields["categoria"] is not None:
            if fields["categoria"] not in VALID_CATEGORIES:
                raise ProjectRiskValidationError(
                    f"Invalid categoria: {fields['categoria']}"
                )
        if "probabilidad" in fields and fields["probabilidad"] is not None:
            if not (0.0 <= fields["probabilidad"] <= 1.0):
                raise ProjectRiskValidationError("probabilidad must be in [0.0, 1.0]")

        for key, value in fields.items():
            if key in immutable:
                continue
            if hasattr(risk, key):
                setattr(risk, key, value)

        await self.db.flush()
        return risk

    async def delete_risk(self, risk_id: UUID) -> None:
        """Soft delete a project risk."""
        risk = await self.get_risk(risk_id)
        risk.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ================================================================
    # Catalog instantiation
    # ================================================================

    async def is_catalog_instantiated(self, project_id: UUID) -> bool:
        """Check if the catalog has been instantiated for a project."""
        result = await self.db.execute(
            select(ProjectRisk.id)
            .where(
                ProjectRisk.project_id == project_id,
                ProjectRisk.risk_code.like("R-%"),
                ProjectRisk.deleted_at.is_(None),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def instantiate_catalog_for_project(
        self,
        project_id: UUID,
        force: bool = False,
        only_categorias: list[str] | None = None,
    ) -> dict[str, Any]:
        """Instantiate the base catalog of 30 risks for a project.

        Returns dict with project_id, risks_created, risks_skipped,
        catalog_version, categorias_loaded.

        Raises CatalogAlreadyInstantiatedError if loaded and force=False.
        """
        if not force:
            already = await self.is_catalog_instantiated(project_id)
            if already:
                raise CatalogAlreadyInstantiatedError(
                    f"Catalog already instantiated for project {project_id}. "
                    f"Use force=True to re-instantiate."
                )

        catalog = load_catalog()
        catalog_version = get_catalog_version(catalog)

        # Get existing codes to skip duplicates
        result = await self.db.execute(
            select(ProjectRisk.risk_code)
            .where(
                ProjectRisk.project_id == project_id,
                ProjectRisk.deleted_at.is_(None),
            )
        )
        existing_codes = {row[0] for row in result.all()}

        risks_to_load = catalog["riesgos_base"]
        if only_categorias:
            risks_to_load = [
                r for r in risks_to_load if r["categoria"] in only_categorias
            ]

        created = 0
        skipped = 0
        categorias_seen: set[str] = set()

        for risk_entry in risks_to_load:
            if risk_entry["codigo"] in existing_codes:
                skipped += 1
                continue

            data = catalog_to_project_risk_data(risk_entry, project_id)
            risk = ProjectRisk(**data)
            self.db.add(risk)
            created += 1
            categorias_seen.add(risk_entry["categoria"])

        await self.db.flush()

        return {
            "project_id": str(project_id),
            "risks_created": created,
            "risks_skipped": skipped,
            "catalog_version": catalog_version,
            "categorias_loaded": sorted(categorias_seen),
        }

    # ================================================================
    # Lifecycle transitions (18.3-B placeholder)
    # ================================================================

    async def monitor_risk(
        self,
        risk_id: UUID,
        notas: str | None = None,
    ) -> ProjectRisk:
        """Transition: identificado -> monitorizado."""
        risk = await self.get_risk(risk_id)
        if risk.status != "identificado":
            raise ProjectRiskStateError(
                f"Cannot monitor risk in status '{risk.status}'. Must be 'identificado'."
            )
        risk.status = "monitorizado"
        if notas:
            timestamp = datetime.now(timezone.utc).isoformat()
            existing_desc = risk.descripcion or ""
            risk.descripcion = f"{existing_desc}\n\n[Monitorización {timestamp}]: {notas}".strip()
        await self.db.flush()
        return risk

    async def materialize_risk(
        self,
        risk_id: UUID,
        trigger_evidence: str,
        materialized_by: str | None = None,
    ) -> ProjectRisk:
        """Transition: monitorizado -> materializado."""
        risk = await self.get_risk(risk_id)
        if risk.status != "monitorizado":
            raise ProjectRiskStateError(
                f"Cannot materialize risk in status '{risk.status}'. Must be 'monitorizado'."
            )
        now = datetime.now(timezone.utc)
        risk.status = "materializado"
        risk.materializado_at = now
        risk.materialization_evidence = {
            "trigger_evidence": trigger_evidence,
            "materialized_by": materialized_by,
            "materialized_at": now.isoformat(),
        }
        # contingency_plan SE QUEDA INTACTO. Es el plan puro, no el log de ejecución.
        await self.db.flush()

        # ── Sprint C6: hooks reactivos automáticos ──
        try:
            await self._trigger_reactive_hooks(risk)
        except Exception:
            # Best-effort: no bloquear materialización si hook falla
            pass

        return risk

    async def _trigger_reactive_hooks(self, risk: ProjectRisk) -> None:
        """Hooks M19 → M17 (replan) + M19 → M18 (escalation).

        Solo se dispara si impacto alto (>5 días o probabilidad >=0.7).
        """
        impacto = risk.impacto_dias or 0
        prob = risk.probabilidad or 0.0

        # Escalation M18 — siempre que se materialice un riesgo monitorizado
        try:
            from backend.app.motors.m18_communication.escalation_service import (
                EscalationService,
            )
            await EscalationService().create_escalation(
                self.db,
                project_id=risk.project_id,
                trigger="riesgo_materializado_alto",
                descripcion=f"Riesgo materializado: {risk.titulo}",
            )
        except Exception:
            pass

        # Replan M17 — solo si impacto significativo
        if impacto > 5 or prob >= 0.7:
            try:
                # Best-effort: crear change request auto
                from sqlalchemy import select as _select
                from backend.app.models.planning import ProjectPlan, ChangeRequest
                plan = (await self.db.execute(
                    _select(ProjectPlan).where(
                        ProjectPlan.project_id == risk.project_id,
                    ).limit(1)
                )).scalar_one_or_none()
                if plan:
                    # FIX P1-8: código CR serializado (helper compartido con m17 ·
                    # advisory lock evita CR-NNN duplicado entre ambos generadores).
                    from backend.app.core.sequences import (
                        next_change_request_code,
                    )
                    code = await next_change_request_code(
                        self.db, risk.project_id,
                    )
                    cr_desc = ""
                    if isinstance(risk.contingency_plan, dict):
                        cr_desc = risk.contingency_plan.get("descripcion", "") or ""
                    if not cr_desc:
                        cr_desc = f"Activación contingencia por riesgo {risk.risk_code}"
                    cr = ChangeRequest(
                        project_id=risk.project_id,
                        plan_id=plan.id,
                        code=code,
                        titulo=f"Riesgo materializado: {risk.titulo}",
                        descripcion=cr_desc,
                        impacto_plazo_dias=risk.impacto_dias,
                        solicitado_por="sistema_riesgos",
                        estado="propuesto",
                    )
                    self.db.add(cr)
                    await self.db.flush()
            except Exception:
                pass

    async def close_risk(
        self,
        risk_id: UUID,
        resolution_notes: str,
        closed_by: str | None = None,
    ) -> ProjectRisk:
        """Transition: identificado|monitorizado|materializado -> cerrado."""
        risk = await self.get_risk(risk_id)
        allowed_from = {"identificado", "monitorizado", "materializado"}
        if risk.status not in allowed_from:
            raise ProjectRiskStateError(
                f"Cannot close risk in status '{risk.status}'. Must be one of {allowed_from}."
            )
        now = datetime.now(timezone.utc)
        risk.status = "cerrado"
        risk.cerrado_at = now
        risk.closure_evidence = {
            "resolution_notes": resolution_notes,
            "closed_by": closed_by,
            "closed_at": now.isoformat(),
        }
        # mitigation_plan SE QUEDA INTACTO.
        await self.db.flush()
        return risk

    # ================================================================
    # Dashboard
    # ================================================================

    async def get_dashboard(self, project_id: UUID) -> dict[str, Any]:
        """Risk dashboard for Marcos weekly review.

        Returns dashboard structure incluso si el proyecto no tiene risks instanciados
        (devuelve totales en 0 y listas vacías). Esto es importante porque K.3 tab Riesgos
        y K.6 consola retainer llaman a este endpoint para proyectos recién creados.
        """
        risks = await self.list_risks(project_id)

        by_status: dict[str, int] = {}
        by_categoria: dict[str, int] = {}
        by_semaforo: dict[str, int] = {"verde": 0, "amarillo": 0, "rojo": 0}
        items = []

        for r in risks:
            s = r.status or "identificado"
            by_status[s] = by_status.get(s, 0) + 1

            c = r.categoria or "sin_categoria"
            by_categoria[c] = by_categoria.get(c, 0) + 1

            prob = r.probabilidad or 0.0
            dias = r.impacto_dias or 0
            score = prob * dias

            if score >= 15 or s == "materializado":
                semaforo = "rojo"
            elif score >= 5 or s == "monitorizado":
                semaforo = "amarillo"
            else:
                semaforo = "verde"
            by_semaforo[semaforo] += 1

            items.append({
                "id": str(r.id),
                "risk_code": r.risk_code,
                "titulo": r.titulo,
                "categoria": r.categoria,
                "status": r.status,
                "probabilidad": r.probabilidad,
                "impacto_dias": r.impacto_dias,
                "score": score,
                "semaforo": semaforo,
                "owner": r.owner,
                "materializado_at": r.materializado_at,
            })

        active_items = [i for i in items if i["status"] != "cerrado"]
        top_critical = sorted(active_items, key=lambda x: -x["score"])[:5]

        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        recently = [
            i for i in items
            if i["status"] == "materializado"
            and i["materializado_at"] is not None
            and i["materializado_at"] >= cutoff
        ]

        return {
            "project_id": str(project_id),
            "total_risks": len(risks),
            "by_status": by_status,
            "by_categoria": by_categoria,
            "by_semaforo": by_semaforo,
            "top_critical": top_critical,
            "recently_materialized": recently,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
