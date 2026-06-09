"""Motor 4 -- Gap Analysis Engine -- service.

Compares current control state vs target state from DdA. Generates
prioritized list of gaps using deterministic rules from the severity
catalog. LLM contextual refinement deferred (M4-G1).

Pattern: consistent with M19 and M3.
- async methods with AsyncSession
- raise specific exceptions from exceptions module
- no internal commits (delegate to caller)
- RLS enforced via set_tenant_context in middleware/endpoint
"""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.findings import Finding
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m04_gap.catalog_loader import (
    load_catalog,
    get_medida_rule,
    get_severidad_for_categoria,
    get_esfuerzo_for_categoria,
    is_quick_win_for_categoria,
    is_nuclear,
    get_catalog_version,
)
from backend.app.motors.m04_gap.enums import (
    SEVERITY_SCORING_STR,
    LEVEL_ORDER,
    CATEGORY_TARGET_LEVEL,
    ESTADO_IMPL_TO_CMM,
    CMM_LABELS,
)
from backend.app.motors.m04_gap.control_status_service import (
    compute_control_status,
)
from backend.app.motors.m04_gap.exceptions import (
    GapNotFoundError,
    GapValidationError,
    GapStateError,
    DdANotReadyError,
    GapAlreadyAnalyzedError,
)

FUENTE_GAP = "gap_analysis"


def derive_control_state(estado_implementacion: str | None) -> str | None:
    """#21 Ola 4 · deriva el nivel CMM base (L0-L5) desde el estado de
    implementación de la SoA (dda_entries.estado_implementacion · fuente única).

    Returns None si la medida NO computa madurez (`no_aplica` · excluida del
    CMM/gap). L4 (implantada + evidencia verde) se resuelve en el acople #20→#21
    dentro de analyze_project, NO aquí (requiere el semáforo). Grafía
    desconocida → L0 conservador (la marca como gap pendiente · nunca silencia).
    """
    if estado_implementacion is None:
        return "L0"  # sin valorar (igual que no_valorado · conservador)
    return ESTADO_IMPL_TO_CMM.get(estado_implementacion, "L0")


async def effective_cmm_level(
    db: AsyncSession,
    *,
    project_id: UUID,
    measure_code: str,
    estado_implementacion: str | None,
) -> str | None:
    """#21 · nivel CMM EFECTIVO de una medida: base derivado de la SoA +
    acople L4 (#20→#21: implantada=L3 + evidencia VERDE → L4 gestionado).

    Returns None si la medida NO computa madurez (no_aplica). Best-effort en el
    semáforo: si compute_control_status falla, queda en L3 (no rompe el cálculo).
    Reusado por analyze_project (loop · pasa el estado ya cargado, sin query
    extra) y por el endpoint per-medida (DRY · OPS-026).
    """
    base = derive_control_state(estado_implementacion)
    if base != "L3":
        return base
    try:
        ev = await compute_control_status(
            db, project_id=project_id, measure_code=measure_code,
        )
        if ev.semaforo == "verde":
            return "L4"
    except Exception:
        pass
    return "L3"


async def get_measure_cmm_detail(
    db: AsyncSession,
    *,
    project_id: UUID,
    measure_code: str,
) -> dict[str, Any]:
    """#21 cierre · detalle CMM de UNA medida para la fila SoA (lente madurez).

    Devuelve estado_implementacion (declarado · lente conformidad) + cmm_level/
    label (madurez derivada) + target_level (objetivo por categoría · best-effort).
    Fuente única: la SoA (dda_entries.estado_implementacion).
    """
    row = (
        await db.execute(
            select(DdaEntry.estado_implementacion)
            .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
            .where(
                DdaEntry.project_id == project_id,
                EnsMeasure.codigo == measure_code,
                DdaEntry.deleted_at.is_(None),
            )
            .limit(1)
        )
    ).first()
    estado_impl = row[0] if row else None

    cmm = await effective_cmm_level(
        db,
        project_id=project_id,
        measure_code=measure_code,
        estado_implementacion=estado_impl,
    )

    target_level: str | None = None
    try:
        # auto-detect (categoria_objetivo=None → lee la categorización m01 del
        # sistema del proyecto). best-effort: si no hay categoría, target=None.
        categoria = await GapAnalysisService(db)._detect_categoria(
            project_id, None,
        )
        target_level = CATEGORY_TARGET_LEVEL.get(categoria)
    except Exception:
        pass

    return {
        "measure_code": measure_code,
        "estado_implementacion": estado_impl,
        "cmm_level": cmm,
        "cmm_label": CMM_LABELS.get(cmm) if cmm else None,
        "target_level": target_level,
    }


# Cached aggregate of effort from M5 obligation templates per measure_code.
# Populated on first access; small dict (~73 keys).
_M5_EFFORT_CACHE: dict[str, float] | None = None


def _m5_template_effort_for_measure(measure_code: str) -> float | None:
    """Return the sum of ``esfuerzo_horas`` across all M5 obligation
    templates that target ``measure_code``.

    Loaded lazily from ``obligations_library.json`` the first time
    any gap needs it. Returns ``None`` if no templates exist for the
    measure so callers can distinguish "no data" from "0 hours".
    """
    global _M5_EFFORT_CACHE
    if _M5_EFFORT_CACHE is None:
        import json as _json
        from pathlib import Path as _Path
        lib_path = (
            _Path(__file__).resolve().parents[1]
            / "m05_obligations" / "library" / "obligations_library.json"
        )
        agg: dict[str, float] = {}
        try:
            data = _json.loads(lib_path.read_text(encoding="utf-8"))
            for t in data.get("templates", []):
                mc = (t.get("measure_code") or "").strip()
                if not mc:
                    continue
                try:
                    effort = float(t.get("esfuerzo_horas") or 0)
                except (TypeError, ValueError):
                    effort = 0.0
                agg[mc] = agg.get(mc, 0.0) + effort
        except Exception:
            agg = {}
        _M5_EFFORT_CACHE = agg
    val = _M5_EFFORT_CACHE.get(measure_code)
    return round(val, 2) if val is not None else None


class GapAnalysisService:
    """Service for gap analysis (Motor 4).

    All methods are async. Commits delegated to caller.
    RLS enforced via tenant context set before calling service.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ================================================================
    # CRUD on gap findings
    # ================================================================

    async def get_gap(self, gap_id: UUID) -> Finding:
        """Get a gap finding by id. Raises GapNotFoundError."""
        finding = await self.db.get(Finding, gap_id)
        if finding is None or finding.deleted_at is not None:
            raise GapNotFoundError(f"Gap finding {gap_id} not found")
        if finding.fuente != FUENTE_GAP:
            raise GapNotFoundError(f"Finding {gap_id} is not a gap analysis finding")
        return finding

    async def list_gaps(
        self,
        project_id: UUID,
        severidad: str | None = None,
        estado: str | None = None,
        familia: str | None = None,
        only_quick_wins: bool = False,
        only_nuclear: bool = False,
    ) -> list[Finding]:
        """List gap findings for a project with optional filters."""
        conditions = [
            Finding.project_id == project_id,
            Finding.fuente == FUENTE_GAP,
            Finding.deleted_at.is_(None),
        ]
        if severidad is not None:
            conditions.append(Finding.severidad == severidad)
        if estado is not None:
            conditions.append(Finding.estado == estado)

        result = await self.db.execute(
            select(Finding)
            .where(and_(*conditions))
            .order_by(Finding.medida_afectada)
        )
        gaps = list(result.scalars().all())

        # Post-filter on JSONB fields
        if familia is not None:
            gaps = [g for g in gaps if (g.metadata_jsonb or {}).get("familia") == familia]
        if only_quick_wins:
            gaps = [g for g in gaps if (g.metadata_jsonb or {}).get("quick_win") is True]
        if only_nuclear:
            gaps = [g for g in gaps if (g.metadata_jsonb or {}).get("nuclear") is True]

        return gaps

    async def update_gap(self, gap_id: UUID, **fields: Any) -> Finding:
        """Partial update of a gap finding."""
        immutable = {"id", "project_id", "fuente", "created_at"}
        gap = await self.get_gap(gap_id)

        if "severidad" in fields and fields["severidad"] is not None:
            valid = {"critica", "alta", "media", "baja", "informativa"}
            if fields["severidad"] not in valid:
                raise GapValidationError(f"Invalid severidad: {fields['severidad']}")
        if "estado" in fields and fields["estado"] is not None:
            valid_st = {"abierto", "en_curso", "cerrado", "descartado"}
            if fields["estado"] not in valid_st:
                raise GapValidationError(f"Invalid estado: {fields['estado']}")

        for key, value in fields.items():
            if key in immutable:
                continue  # pragma: no cover — immutable fields silently skipped
            if hasattr(gap, key):
                setattr(gap, key, value)

        await self.db.flush()
        return gap

    async def close_gap(
        self,
        gap_id: UUID,
        resolution_notes: str,
        closed_by: str | None = None,
    ) -> Finding:
        """Close a gap finding."""
        gap = await self.get_gap(gap_id)
        if gap.estado == "cerrado":
            raise GapStateError(f"Gap {gap_id} is already closed")

        now = datetime.now(timezone.utc)
        gap.estado = "cerrado"
        md = gap.metadata_jsonb or {}
        md["closure"] = {
            "resolution_notes": resolution_notes,
            "closed_by": closed_by,
            "closed_at": now.isoformat(),
        }
        gap.metadata_jsonb = md
        await self.db.flush()
        return gap

    async def delete_gap(self, gap_id: UUID) -> None:
        """Soft delete a gap finding."""
        gap = await self.get_gap(gap_id)
        gap.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    # ================================================================
    # Core analysis
    # ================================================================

    async def _detect_categoria(
        self, project_id: UUID, categoria_objetivo: str | None
    ) -> str:
        """Detect system category for the project.

        If categoria_objetivo is provided, use it directly.
        Otherwise look up the latest categorization for the project's system.
        """
        if categoria_objetivo:
            cat = categoria_objetivo.upper()
            if cat not in CATEGORY_TARGET_LEVEL:
                raise GapValidationError(
                    f"Invalid categoria_objetivo: {cat} (valid: BASICA, MEDIA, ALTA)"
                )
            return cat

        # Look up system -> categorization
        result = await self.db.execute(
            text(
                "SELECT c.categoria_resultante "
                "FROM categorizations c "
                "JOIN systems s ON s.id = c.system_id "
                "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
                "ORDER BY c.created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        row = result.first()
        if row is None or row[0] is None:
            raise DdANotReadyError(
                f"No categorization found for project {project_id}. "
                "Run Motor 1 Categorization first, or pass categoria_objetivo."
            )
        return row[0].upper()

    async def _get_dda_entries_with_measures(
        self, project_id: UUID
    ) -> list[dict[str, Any]]:
        """Get all applicable DdA entries for a project, joined with measure info.

        Returns list of dicts with dda_entry fields + measure codigo/familia.
        Raises DdANotReadyError if no DdA entries exist.
        """
        result = await self.db.execute(
            select(
                DdaEntry.id.label("dda_entry_id"),
                DdaEntry.aplicabilidad,
                DdaEntry.estado_implementacion,
                EnsMeasure.codigo,
                EnsMeasure.familia,
                EnsMeasure.nombre.label("medida_nombre"),
            )
            .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
            .where(
                DdaEntry.project_id == project_id,
                DdaEntry.deleted_at.is_(None),
            )
        )
        rows = result.all()
        if not rows:
            raise DdANotReadyError(
                f"No DdA entries found for project {project_id}. "
                "Run Motor 3 DdA Engine first."
            )
        return [
            {
                "dda_entry_id": r.dda_entry_id,
                "aplicabilidad": r.aplicabilidad,
                "estado_implementacion": r.estado_implementacion,
                "codigo": r.codigo,
                "familia": r.familia,
                "medida_nombre": r.medida_nombre,
            }
            for r in rows
        ]

    # #21 Ola 4 · `_get_control_state` ELIMINADO: leía `controls.estado` (tabla
    # vacía → siempre L0 = el bug). El nivel CMM ahora se deriva de la SoA vía
    # `derive_control_state(estado_implementacion)` (módulo · sin query extra).
    # La tabla `controls` queda huérfana (0 lecturas · NO se borra).

    async def _get_evidence_coverage(
        self, project_id: UUID, measure_code: str,
    ) -> dict:
        """GAP 11: Query real a Evidence para una medida ENS.

        Retorna resumen de evidencia: total/vigente/caducada.
        """
        from backend.app.models.documents import Evidence
        from datetime import date as _date
        today = _date.today()
        res = await self.db.execute(
            select(Evidence).where(
                Evidence.project_id == project_id,
                Evidence.measure_code == measure_code,
                Evidence.deleted_at.is_(None),
            )
        )
        evidencias = list(res.scalars().all())
        total = len(evidencias)
        vigentes = sum(
            1 for e in evidencias
            if (e.vigente is True) and (e.fecha_caducidad is None or e.fecha_caducidad >= today)
        )
        caducadas = sum(
            1 for e in evidencias
            if e.fecha_caducidad and e.fecha_caducidad < today
        )
        return {
            "total": total,
            "vigentes": vigentes,
            "caducadas": caducadas,
            "has_any": total > 0,
            "has_vigente": vigentes > 0,
        }

    async def analyze_project(
        self,
        project_id: UUID,
        force: bool = False,
        categoria_objetivo: str | None = None,
    ) -> dict[str, Any]:
        """Run gap analysis for a project.

        Compares current control state vs target for each DdA entry.
        Creates Finding records for each gap detected.

        Returns analysis summary dict.
        """
        # Check if already analyzed
        if not force:
            existing = await self.db.execute(
                select(Finding.id)
                .where(
                    Finding.project_id == project_id,
                    Finding.fuente == FUENTE_GAP,
                    Finding.deleted_at.is_(None),
                )
                .limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                raise GapAlreadyAnalyzedError(
                    f"Gap analysis already run for project {project_id}. "
                    "Use force=True to re-analyze."
                )

        # Detect category
        categoria = await self._detect_categoria(project_id, categoria_objetivo)
        target_level = CATEGORY_TARGET_LEVEL[categoria]
        target_order = LEVEL_ORDER[target_level]

        # Load catalog
        catalog = load_catalog()
        catalog_version = get_catalog_version(catalog)

        # Get DdA entries
        dda_entries = await self._get_dda_entries_with_measures(project_id)

        # If force, soft-delete previous gaps
        if force:
            prev_result = await self.db.execute(
                select(Finding)
                .where(
                    Finding.project_id == project_id,
                    Finding.fuente == FUENTE_GAP,
                    Finding.deleted_at.is_(None),
                )
            )
            now = datetime.now(timezone.utc)
            for prev in prev_result.scalars().all():
                prev.deleted_at = now
            await self.db.flush()

        # Analyze each entry
        gaps_created = 0
        gaps_by_severidad: dict[str, int] = {}
        quick_wins_count = 0
        nuclear_gaps: list[str] = []
        now = datetime.now(timezone.utc)

        for entry in dda_entries:
            # Skip non-applicable measures
            if entry["aplicabilidad"] == "no_aplica":
                continue

            codigo = entry["codigo"]
            familia = entry["familia"]
            dda_entry_id = entry["dda_entry_id"]

            # #21 Ola 4 · nivel CMM efectivo derivado de la SoA
            # (estado_implementacion YA cargado · sin query extra) + acople L4
            # (#20→#21). Antes leía controls.estado (tabla VACÍA → SIEMPRE L0 =
            # EL BUG · gap máximo falso). controls queda huérfana (0 lecturas ·
            # NO se borra). Lógica compartida con el endpoint per-medida (DRY).
            estado_actual = await effective_cmm_level(
                self.db,
                project_id=project_id,
                measure_code=codigo,
                estado_implementacion=entry["estado_implementacion"],
            )
            if estado_actual is None:
                continue  # estado_implementacion = no_aplica → excluida del gap
            actual_order = LEVEL_ORDER.get(estado_actual, 0)

            # Compare with target
            if actual_order >= target_order:
                continue  # No gap

            # There IS a gap — create finding
            rule = get_medida_rule(catalog, codigo)
            severidad = get_severidad_for_categoria(catalog, codigo, categoria) or "media"
            esfuerzo = get_esfuerzo_for_categoria(catalog, codigo, categoria)
            qw = is_quick_win_for_categoria(catalog, codigo, categoria)
            nuc = is_nuclear(catalog, codigo)

            guia = rule["guia_remediacion"] if rule else ""
            evidencia = rule["evidencia_tipica"] if rule else ""
            notas = rule["notas_auditor"] if rule else ""

            # GAP 11: enriquecer metadata con cobertura real de evidencia (M7)
            try:
                evidence_coverage = await self._get_evidence_coverage(project_id, codigo)
            except Exception:
                evidence_coverage = {"total": 0, "vigentes": 0, "has_vigente": False}

            # Sum of estimated effort for the obligations that M5 would
            # instantiate for this medida. Gives a realistic, bottom-up
            # view of how many hours the gap will cost to close.
            m5_effort = _m5_template_effort_for_measure(codigo)

            metadata = {
                "motor": "m04_gap",
                "catalog_version": catalog_version,
                "codigo_medida": codigo,
                "medida_codigo": codigo,  # alias para hook M5
                "familia": familia,
                "estado_actual": estado_actual,
                "estado_objetivo": target_level,
                "esfuerzo_horas": esfuerzo,
                # Canonical alias aligned with M5 obligation templates.
                "esfuerzo_estimado_horas": esfuerzo or m5_effort or 0,
                "esfuerzo_obligaciones_m5": m5_effort,
                "quick_win": qw,
                "nuclear": nuc,
                "guia_remediacion": guia,
                "evidencia_tipica": evidencia,
                "evidence_coverage": evidence_coverage,
                "notas_auditor": notas,
                "dda_entry_id": str(dda_entry_id),
                "control_id": None,
                "generated_at": now.isoformat(),
            }

            finding = Finding(
                project_id=project_id,
                fuente=FUENTE_GAP,
                severidad=severidad,
                medida_afectada=codigo,
                descripcion=f"Gap en {codigo}: estado actual {estado_actual}, objetivo {target_level}. {guia}",
                estado="abierto",
                metadata_jsonb=metadata,
            )
            self.db.add(finding)
            gaps_created += 1
            gaps_by_severidad[severidad] = gaps_by_severidad.get(severidad, 0) + 1
            if qw:
                quick_wins_count += 1
            if nuc:
                nuclear_gaps.append(codigo)

        await self.db.flush()

        # ── Hook M4 → M5: instanciar obligaciones automáticamente ──
        # Best-effort: no bloquear analyze si falla el hook.
        obligations_created = 0
        try:
            obligations_created = await self._trigger_obligations_hook(
                project_id, categoria,
            )
        except Exception:
            # Log silencioso; el gap analysis se completa igualmente
            pass

        return {
            "project_id": str(project_id),
            "categoria_usada": categoria,
            "dda_entries_evaluated": len(dda_entries),
            "gaps_created": gaps_created,
            "gaps_by_severidad": gaps_by_severidad,
            "quick_wins_count": quick_wins_count,
            "critical_nuclear_gaps": nuclear_gaps,
            "obligations_auto_created": obligations_created,
            "catalog_version": catalog_version,
            "generated_at": now.isoformat(),
        }

    async def _trigger_obligations_hook(
        self, project_id: UUID, categoria: str,
    ) -> int:
        """Hook M4 → M5: tras crear gaps, instanciar obligaciones desde library.

        Invoca `instantiate_obligations_for_multiple_gaps` de M5 pasando los
        gaps recién creados como GapInput. Tolerante a fallos.
        """
        try:
            from backend.app.motors.m05_obligations.instantiation_service import (
                instantiate_obligations_for_multiple_gaps,
            )
            from backend.app.motors.m05_obligations.instantiation_types import (
                ClientContext, GapInput, ProjectContext,
            )
        except Exception:
            return 0

        # Cargar gaps recién creados
        res = await self.db.execute(
            select(Finding).where(
                Finding.project_id == project_id,
                Finding.fuente == FUENTE_GAP,
                Finding.deleted_at.is_(None),
            )
        )
        gaps = list(res.scalars().all())
        if not gaps:
            return 0

        gap_inputs = []
        for g in gaps:
            md = g.metadata_jsonb or {}
            code = md.get("medida_codigo") or md.get("codigo")
            if code:
                gap_inputs.append(GapInput(gap_id=g.id, measure_code=code))

        if not gap_inputs:
            return 0

        ctx = ProjectContext(
            project_id=project_id,
            nombre_proyecto="",
            categoria_ens=categoria,
            cliente=ClientContext(razon_social="", sector=None),
        )
        outcomes = await instantiate_obligations_for_multiple_gaps(
            self.db, gap_inputs, ctx, use_llm_personalization=False,
        )
        created = sum(len(o.obligations_created_ids) for o in outcomes)
        await self.db.flush()
        return created

    # ================================================================
    # Dashboard
    # ================================================================

    async def get_dashboard(self, project_id: UUID) -> dict[str, Any]:
        """Gap analysis dashboard.

        Returns dashboard structure even if no gaps exist (zeros, no 404).
        """
        gaps = await self.list_gaps(project_id)

        by_severidad: dict[str, int] = {}
        by_familia: dict[str, int] = {}
        by_estado: dict[str, int] = {}
        by_semaforo: dict[str, int] = {"verde": 0, "amarillo": 0, "rojo": 0}
        items = []

        for g in gaps:
            md = g.metadata_jsonb or {}

            sev = g.severidad or "informativa"
            by_severidad[sev] = by_severidad.get(sev, 0) + 1

            fam = md.get("familia", "unknown")
            by_familia[fam] = by_familia.get(fam, 0) + 1

            est = g.estado or "abierto"
            by_estado[est] = by_estado.get(est, 0) + 1

            sev_num = SEVERITY_SCORING_STR.get(sev, 1)
            gap_mag = LEVEL_ORDER.get(md.get("estado_objetivo", "L2"), 2) - LEVEL_ORDER.get(md.get("estado_actual", "L0"), 0)
            score = sev_num * max(gap_mag, 1)

            if score >= 15 or sev == "critica":
                semaforo = "rojo"
            elif score >= 6 or sev in ("alta", "media"):
                semaforo = "amarillo"
            else:
                semaforo = "verde"
            by_semaforo[semaforo] += 1

            items.append({
                "id": str(g.id),
                "medida_afectada": g.medida_afectada,
                "severidad": sev,
                "severidad_numeric": sev_num,
                "estado": g.estado,
                "esfuerzo_horas": md.get("esfuerzo_horas"),
                "quick_win": md.get("quick_win", False),
                "nuclear": md.get("nuclear", False),
                "familia": md.get("familia"),
                "semaforo": semaforo,
                "score": score,
            })

        # Top 10 critical (excl cerrado)
        active = [i for i in items if i["estado"] != "cerrado"]
        top_10 = sorted(active, key=lambda x: (-x["severidad_numeric"], -x.get("score", 0)))[:10]

        # Quick wins
        qw_items = [i for i in active if i["quick_win"]]

        # Nuclear
        nuc_items = [i for i in items if i["nuclear"]]

        def _to_dashboard_item(i: dict) -> dict:
            return {k: v for k, v in i.items() if k != "score"}

        return {
            "project_id": str(project_id),
            "total_gaps": len(gaps),
            "by_severidad": by_severidad,
            "by_familia": by_familia,
            "by_estado": by_estado,
            "by_semaforo": by_semaforo,
            "top_10_critical": [_to_dashboard_item(i) for i in top_10],
            "quick_wins": [_to_dashboard_item(i) for i in qw_items],
            "nuclear_gaps": [_to_dashboard_item(i) for i in nuc_items],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
