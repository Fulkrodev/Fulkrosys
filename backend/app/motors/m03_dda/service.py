"""Motor 3 — DdA Engine Service.

Logica core para generar y gestionar Declaraciones de Aplicabilidad ENS
segun RD 311/2022 Anexo II.

Patron:
- Service class consistente con MageritService (Motor 2) y MagicLinkService (Motor 12)
- Generacion atomica de las 73 entries al crear DdA
- Templates estaticos para justificaciones (futuro: enriquecimiento LLM via Motor 11, M3-G1)
- Freeze/unfreeze via aprobado_por + fecha_aprobacion en entries
- Read-only enrichment con magerit_ens_mapping (salvaguardas MAGERIT)

References:
- RD 311/2022 Anexo II — medidas de seguridad (73 medidas)
- CCN-STIC 803 — valoracion de sistemas
- CCN-STIC 804 — implantacion de medidas
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ens import EnsMeasure, DdaEntry
from backend.app.motors.m03_dda.anexo2_rd311_2022 import EJE_Y_DIMENSIONES
from backend.app.motors.m01_categorization.aplicabilidad import (
    DIMENSIONES_ENS,
    NIVELES_CON_ADSCRIPCION,
    NO_AFECTADA,
    medidas_aplicables,
)
from backend.app.motors.m03_dda.enums import (
    Aplicabilidad,
    EstadoImplementacion,
    CategoriaSistema,
)
from backend.app.motors.m03_dda.templates import render_no_aplica_justification


# ================================================================
# EXCEPTIONS (patron Motor 12 jerarquico)
# ================================================================

class DdaError(Exception):
    """Base exception for DdA Engine errors."""


class DdaNotFoundError(DdaError):
    """No DdA entries found for this project."""


class DdaFrozenError(DdaError):
    """DdA is frozen (aprobada), cannot modify."""


class DdaEntryNotFoundError(DdaError):
    """Specific entry within DdA not found."""


class DdaIncompleteForFreezeError(DdaError):
    """DdA has too many NO_VALORADO entries to freeze."""


# ================================================================
# SERVICE
# ================================================================

class DdaService:
    """Service para Motor 3 DdA Engine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ================================================================
    # PUBLIC: Generate DdA
    # ================================================================

    async def generate_dda(
        self,
        project_id: UUID,
        system_category: CategoriaSistema,
        responsable: str | None = None,
        enforce_gates: bool = True,
    ) -> dict:
        """Genera nueva DdA: 73 entries en transaccion atomica.

        Si ya existe DdA para el proyecto, la sobrescribe (DELETE+INSERT).
        Para cada medida:
        - Si aplica segun categoria -> entry con estado NO_VALORADO
        - Si no aplica -> entry con justificacion template + estado NO_APLICA
        - Si aplica con refuerzos -> marca refuerzos aplicables

        RD 311/2022 Anexo II: aplicabilidad determinada por las columnas
        aplica_basica/media/alta en ens_measures (cargadas desde YAML).

        Gate: si ``enforce_gates`` es True (default en producción),
        requiere una categorización firmada en el proyecto.
        """
        if enforce_gates:
            from backend.app.core.workflow_gates import require_signed_categorization
            await require_signed_categorization(self.db, project_id)

        # 1. Delete previous entries for this project (replace semantics)
        await self.db.execute(
            sa_text("DELETE FROM dda_entries WHERE project_id = :pid AND deleted_at IS NULL"),
            {"pid": str(project_id)},
        )
        await self.db.flush()

        # 2. Load all 73 measures.
        # Refuerzos se leen on-demand vía ``_applicable_reinforcements``
        # contra ens_measure_refuerzos seedeado canónicamente (SAN-C.MB-9.1).
        result = await self.db.execute(
            select(EnsMeasure)
            .where(EnsMeasure.deleted_at.is_(None))
            .order_by(EnsMeasure.codigo)
        )
        measures = result.scalars().all()

        # L-8 (FRENTE L): tamaño de empresa para la nota de proporcionalidad
        # CCN-STIC 801 sec 4.2 en las justificaciones (micro/autónomo).
        empresa_size = await self.db.scalar(
            sa_text("SELECT tamano_empleados FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )

        # O1 · niveles por dimension del proyecto, para poder aplicar el eje
        # "dimension" del Anexo II y no solo el de categoria.
        niveles = await self._niveles_por_dimension(project_id)
        # La categoria viene de una categorizacion FIRMADA (gate de arriba): es
        # dato de entrada. Un proyecto sin ninguna dimension afectada da las
        # medidas de eje categoria y ninguna de eje dimension, que es lo que
        # dice la tabla; no es motivo para negarse a generar la DdA.
        aplicables_por_codigo = medidas_aplicables(
            system_category.value, niveles, exigir_alguna_afectada=False,
        )

        # 3. Generate entries
        entries_aplicables = 0
        entries_no_aplica = 0

        for measure in measures:
            motivo = aplicables_por_codigo.get(measure.codigo)
            aplica = motivo is not None

            if aplica:
                refuerzos = await self._applicable_reinforcements(measure, system_category)
                aplicabilidad = (
                    Aplicabilidad.APLICA_CON_REFUERZOS.value
                    if refuerzos
                    else Aplicabilidad.APLICA.value
                )
                entry = DdaEntry(
                    project_id=project_id,
                    measure_id=measure.id,
                    aplicabilidad=aplicabilidad,
                    estado_implementacion=EstadoImplementacion.NO_VALORADO.value,
                    refuerzos_aplicados=refuerzos if refuerzos else [],
                    justificacion_no_aplica=None,
                    responsable=responsable,
                    version=1,
                )
                entries_aplicables += 1
            else:
                cat_min = measure.categoria_minima or "BASICA"
                justificacion = render_no_aplica_justification(
                    codigo=measure.codigo,
                    nombre=measure.nombre,
                    cat_minima=cat_min,
                    system_category=system_category.value,
                    empresa_size=empresa_size,
                )
                entry = DdaEntry(
                    project_id=project_id,
                    measure_id=measure.id,
                    aplicabilidad=Aplicabilidad.NO_APLICA.value,
                    estado_implementacion=EstadoImplementacion.NO_APLICA.value,
                    refuerzos_aplicados=[],
                    justificacion_no_aplica=justificacion,
                    responsable=responsable,
                    version=1,
                )
                entries_no_aplica += 1

            self.db.add(entry)

        await self.db.flush()

        return {
            "project_id": str(project_id),
            "system_category": system_category.value,
            "total_entries": len(measures),
            "aplicables": entries_aplicables,
            "no_aplica": entries_no_aplica,
        }

    # ================================================================
    # PUBLIC: List entries
    # ================================================================

    async def list_entries(
        self,
        project_id: UUID,
        marco: str | None = None,
        familia: str | None = None,
    ) -> list[dict]:
        """Lista entries de la DdA enriquecidas con salvaguardas MAGERIT."""
        query = (
            select(DdaEntry, EnsMeasure)
            .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
            .where(
                DdaEntry.project_id == project_id,
                DdaEntry.deleted_at.is_(None),
            )
        )
        if marco:
            query = query.where(EnsMeasure.marco == marco)
        if familia:
            query = query.where(EnsMeasure.familia == familia)

        query = query.order_by(EnsMeasure.marco, EnsMeasure.familia, EnsMeasure.codigo)

        result = await self.db.execute(query)
        rows = result.all()

        if not rows:
            raise DdaNotFoundError(f"No DdA entries for project {project_id}")

        entries = []
        for entry, measure in rows:
            safeguards = await self._get_magerit_safeguards(measure.codigo)
            entries.append({
                "id": str(entry.id),
                "project_id": str(entry.project_id),
                "measure_codigo": measure.codigo,
                "measure_nombre": measure.nombre,
                "measure_marco": measure.marco,
                "measure_familia": measure.familia,
                "aplicabilidad": entry.aplicabilidad,
                "estado_implementacion": entry.estado_implementacion,
                "justificacion_no_aplica": entry.justificacion_no_aplica,
                "refuerzos_aplicados": entry.refuerzos_aplicados or [],
                "magerit_safeguards": safeguards,
                "responsable": entry.responsable,
                "observaciones": entry.observaciones,
                "version": entry.version,
                "aprobado_por": entry.aprobado_por,
                "fecha_aprobacion": entry.fecha_aprobacion.isoformat() if entry.fecha_aprobacion else None,
            })

        return entries

    # ================================================================
    # PUBLIC: Update entry
    # ================================================================

    async def update_entry(
        self,
        entry_id: UUID,
        updates: dict,
    ) -> DdaEntry:
        """Actualiza una entry especifica. Bloqueado si DdA esta frozen."""
        entry = await self.db.get(DdaEntry, entry_id)
        if not entry or entry.deleted_at is not None:
            raise DdaEntryNotFoundError(f"Entry {entry_id} not found")

        # Check frozen
        if entry.aprobado_por is not None:
            raise DdaFrozenError(
                "La DdA esta aprobada/congelada. Llame a POST /unfreeze primero."
            )

        for field, value in updates.items():
            if value is not None and hasattr(entry, field):
                setattr(entry, field, value)

        entry.version = (entry.version or 1) + 1
        await self.db.flush()
        return entry

    # ================================================================
    # PUBLIC: Completion stats
    # ================================================================

    async def get_completion_stats(self, project_id: UUID) -> dict:
        """Stats de completitud para dashboard."""
        result = await self.db.execute(
            sa_text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE aplicabilidad != 'no_aplica') as aplicables,
                    COUNT(*) FILTER (WHERE aplicabilidad = 'no_aplica') as no_aplica,
                    COUNT(*) FILTER (WHERE estado_implementacion = 'implantada') as implantadas,
                    COUNT(*) FILTER (WHERE estado_implementacion = 'parcial') as parcial,
                    COUNT(*) FILTER (WHERE estado_implementacion = 'no_implantada') as no_implantadas,
                    COUNT(*) FILTER (WHERE estado_implementacion = 'no_valorado') as no_valoradas
                FROM dda_entries
                WHERE project_id = :pid AND deleted_at IS NULL
            """),
            {"pid": str(project_id)},
        )
        row = result.mappings().first()
        if not row or row["total"] == 0:
            raise DdaNotFoundError(f"No DdA entries for project {project_id}")

        aplicables = row["aplicables"]
        implantadas = row["implantadas"]
        pct = round((implantadas / aplicables * 100), 2) if aplicables > 0 else 0.0

        return {
            "project_id": str(project_id),
            "total_medidas": row["total"],
            "total_aplicables": aplicables,
            "no_aplica": row["no_aplica"],
            "implantadas": implantadas,
            "parcial": row["parcial"],
            "no_implantadas": row["no_implantadas"],
            "no_valoradas": row["no_valoradas"],
            "completion_pct": pct,
        }

    # ================================================================
    # PUBLIC: #4 · Revisión anual del AR/DdA (Fase 8 · CCN-STIC 808)
    # ================================================================

    async def annual_review(self, project_id: UUID) -> dict:
        """#4 · Revisión anual del Análisis de Riesgos / DdA (mantenimiento).

        Snapshotea el estado vigente de las 73 medidas, registra el ciclo en
        annual_review_records, bumpa la versión de las dda_entries y EXIGE
        reaprobación de Dirección (limpia aprobado_por/fecha_aprobacion · la DdA
        deja de estar congelada). Disparado on-demand por el scheduler retainer
        (execute_activity 'revision_ar_dda' · cadencia anual en CADENCES_BY_PROFILE).
        """
        import json
        import uuid as _uuid

        # La task abre sesión sin contexto · fijar RLS del proyecto (transaction-local).
        await self.db.execute(
            sa_text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(project_id)},
        )
        stats = await self.get_completion_stats(project_id)  # raises si no hay DdA

        version_from = int((await self.db.execute(
            sa_text(
                "SELECT COALESCE(MAX(version), 1) FROM dda_entries "
                "WHERE project_id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).scalar() or 1)
        version_to = version_from + 1
        record_id = _uuid.uuid4()

        await self.db.execute(
            sa_text(
                "INSERT INTO annual_review_records "
                "(id, project_id, dda_version_from, dda_version_to, estado, "
                " completion_snapshot, created_at) "
                "VALUES (:id, :pid, :vf, :vt, 'pending', CAST(:snap AS jsonb), now())"
            ),
            {
                "id": str(record_id), "pid": str(project_id),
                "vf": version_from, "vt": version_to, "snap": json.dumps(stats),
            },
        )
        # Bump versión + exige reaprobación Dirección + enlaza el record por entrada.
        await self.db.execute(
            sa_text(
                "UPDATE dda_entries SET version = :vt, aprobado_por = NULL, "
                "fecha_aprobacion = NULL, annual_review_record_id = :rid "
                "WHERE project_id = :pid AND deleted_at IS NULL"
            ),
            {"vt": version_to, "rid": str(record_id), "pid": str(project_id)},
        )
        await self.db.flush()
        return {
            "project_id": str(project_id),
            "annual_review_record_id": str(record_id),
            "previous_version": version_from,
            "new_version": version_to,
            "estado": "pending_director_approval",
            "completion_snapshot": stats,
        }

    # ================================================================
    # PUBLIC: Freeze / Unfreeze
    # ================================================================

    async def freeze_dda(self, project_id: UUID, aprobado_por: str) -> dict:
        """Congela la DdA: marca entries con aprobado_por + fecha.

        Requiere minimo 80% de medidas aplicables valoradas (no NO_VALORADO).
        Patron freeze/unfreeze del Motor 2.
        """
        stats = await self.get_completion_stats(project_id)
        aplicables = stats["total_aplicables"]
        no_valoradas = stats["no_valoradas"]

        if aplicables > 0 and (no_valoradas / aplicables) > 0.20:
            raise DdaIncompleteForFreezeError(
                f"DdA tiene {no_valoradas}/{aplicables} medidas NO_VALORADO "
                f"({no_valoradas/aplicables*100:.1f}%). Minimo 80% valoradas para freeze."
            )

        # Check not already frozen
        result = await self.db.execute(
            sa_text(
                "SELECT COUNT(*) FROM dda_entries "
                "WHERE project_id = :pid AND aprobado_por IS NOT NULL AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )
        already_frozen = result.scalar()
        if already_frozen > 0:
            raise DdaFrozenError("La DdA ya esta aprobada/congelada.")

        now = datetime.now(timezone.utc)
        await self.db.execute(
            sa_text("""
                UPDATE dda_entries
                SET aprobado_por = :aprobador, fecha_aprobacion = :fecha
                WHERE project_id = :pid AND deleted_at IS NULL
            """),
            {"aprobador": aprobado_por, "fecha": now.date(), "pid": str(project_id)},
        )
        await self.db.flush()

        return {
            "project_id": str(project_id),
            "aprobado_por": aprobado_por,
            "fecha_aprobacion": now.isoformat(),
            "frozen_entries": stats["total_medidas"],
        }

    async def unfreeze_dda(self, project_id: UUID) -> dict:
        """Descongela la DdA: limpia aprobado_por + fecha_aprobacion."""
        result = await self.db.execute(
            sa_text(
                "SELECT COUNT(*) FROM dda_entries "
                "WHERE project_id = :pid AND aprobado_por IS NOT NULL AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )
        frozen_count = result.scalar()
        if not frozen_count:
            raise DdaError("La DdA no esta congelada.")

        await self.db.execute(
            sa_text("""
                UPDATE dda_entries
                SET aprobado_por = NULL, fecha_aprobacion = NULL
                WHERE project_id = :pid AND deleted_at IS NULL
            """),
            {"pid": str(project_id)},
        )
        await self.db.flush()
        return {"project_id": str(project_id), "unfrozen": True}

    # ================================================================
    # PUBLIC: Catalog + single entry lookup
    # ================================================================

    async def list_catalog_measures(self, marco: str | None = None) -> list[dict]:
        """Read-only catalog of the 73 ENS measures. No tenant context needed.

        Refuerzos se incluyen por medida con ``applicable_categories`` JSONB
        seedeado canónicamente desde RD 311/2022 Anexo II (SAN-C.MB-9.1).
        """
        query = (
            select(EnsMeasure)
            .where(EnsMeasure.deleted_at.is_(None))
        )
        if marco:
            query = query.where(EnsMeasure.marco == marco)
        query = query.order_by(EnsMeasure.marco, EnsMeasure.familia, EnsMeasure.codigo)

        result = await self.db.execute(query)
        measures = result.scalars().all()

        refuerzos_by_code: dict[str, list[dict]] = {}
        if measures:
            ref_result = await self.db.execute(
                sa_text(
                    "SELECT measure_code, refuerzo_level, applicable_categories, description "
                    "FROM ens_measure_refuerzos ORDER BY measure_code, refuerzo_level"
                )
            )
            for row in ref_result.fetchall():
                refuerzos_by_code.setdefault(row[0], []).append({
                    "level": row[1],
                    "applicable_categories": row[2],
                    "description": row[3],
                })

        return [
            {
                "codigo": m.codigo,
                "nombre": m.nombre,
                "marco": m.marco,
                "familia": m.familia,
                "descripcion": m.descripcion,
                "aplica_basica": m.aplica_basica,
                "aplica_media": m.aplica_media,
                "aplica_alta": m.aplica_alta,
                "categoria_minima": m.categoria_minima,
                # N1 · del catalogo del Anexo II contrastado contra el PDF del
                # BOE (N0), no de la columna `dimensiones_aplicables`, que
                # estaba mal en 4 de las 12 medidas contrastadas a mano.
                "eje_aplicabilidad": EJE_Y_DIMENSIONES.get(m.codigo, (None, ""))[0],
                "dimensiones_aplicables": list(
                    EJE_Y_DIMENSIONES.get(m.codigo, (None, ""))[1]
                ) or None,
                "refuerzos": refuerzos_by_code.get(m.codigo, []),
            }
            for m in measures
        ]

    async def get_entry_by_measure(
        self, project_id: UUID, measure_codigo: str,
    ) -> dict:
        """Get a single DdA entry by measure code, enriched with MAGERIT."""
        result = await self.db.execute(
            select(DdaEntry, EnsMeasure)
            .join(EnsMeasure, DdaEntry.measure_id == EnsMeasure.id)
            .where(
                DdaEntry.project_id == project_id,
                DdaEntry.deleted_at.is_(None),
                EnsMeasure.codigo == measure_codigo,
            )
        )
        row = result.first()
        if not row:
            raise DdaEntryNotFoundError(
                f"Entry for measure {measure_codigo} not found in project {project_id}"
            )

        entry, measure = row
        safeguards = await self._get_magerit_safeguards(measure.codigo)
        return {
            "id": str(entry.id),
            "project_id": str(entry.project_id),
            "measure_codigo": measure.codigo,
            "measure_nombre": measure.nombre,
            "measure_marco": measure.marco,
            "measure_familia": measure.familia,
            "aplicabilidad": entry.aplicabilidad,
            "estado_implementacion": entry.estado_implementacion,
            "justificacion_no_aplica": entry.justificacion_no_aplica,
            "refuerzos_aplicados": entry.refuerzos_aplicados or [],
            "magerit_safeguards": safeguards,
            "responsable": entry.responsable,
            "observaciones": entry.observaciones,
            "version": entry.version,
            "aprobado_por": entry.aprobado_por,
            "fecha_aprobacion": entry.fecha_aprobacion.isoformat() if entry.fecha_aprobacion else None,
        }

    # ================================================================
    # PRIVATE: Applicability logic
    # ================================================================

    async def _niveles_por_dimension(self, project_id: UUID) -> dict[str, str]:
        """Nivel de cada dimension del proyecto, sin adscribir lo no valorado.

        O1 · Anexo I punto 3: una dimension que ningun tipo de informacion y
        ningun servicio valora NO se adscribe a ningun nivel. Se arranca en
        NO_AFECTADA y solo sube con valoraciones reales.
        """
        niveles = dict.fromkeys(DIMENSIONES_ENS, NO_AFECTADA)
        filas = (await self.db.execute(sa_text(
            "SELECT valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
            "       valoracion_t "
            "FROM information_types it JOIN systems s ON s.id = it.system_id "
            "WHERE s.project_id = :pid AND it.deleted_at IS NULL "
            "UNION ALL "
            "SELECT valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
            "       valoracion_t "
            "FROM services sv JOIN systems s2 ON s2.id = sv.system_id "
            "WHERE s2.project_id = :pid AND sv.deleted_at IS NULL"
        ), {"pid": str(project_id)})).all()

        for fila in filas:
            for dim, bruto in zip(DIMENSIONES_ENS, fila):
                nivel = str(bruto or "").upper()
                if nivel not in NIVELES_CON_ADSCRIPCION:
                    continue
                actual = niveles[dim]
                if actual == NO_AFECTADA or (
                    NIVELES_CON_ADSCRIPCION.index(nivel)
                    > NIVELES_CON_ADSCRIPCION.index(actual)
                ):
                    niveles[dim] = nivel
        return niveles

    def _measure_applies(
        self,
        measure: EnsMeasure,
        category: CategoriaSistema,
    ) -> bool:
        """Determina si una medida aplica a una categoria, SOLO por categoria.

        OJO · este metodo ignora el eje "dimension" del Anexo II punto 5. Ya NO
        lo usa `generate_dda`, que llama a `medidas_aplicables` (la funcion pura
        que si conoce los dos ejes). Se conserva porque lo usan consumidores de
        solo lectura que no tienen los niveles por dimension a mano; para
        generar una DdA NO sirve.
        """
        if category == CategoriaSistema.BASICA:
            return measure.aplica_basica
        elif category == CategoriaSistema.MEDIA:
            return measure.aplica_media
        elif category == CategoriaSistema.ALTA:
            return measure.aplica_alta
        return True  # pragma: no cover — enum exhaustive

    async def _applicable_reinforcements(
        self,
        measure: EnsMeasure,
        category: CategoriaSistema,
    ) -> list[str]:
        """Devuelve codigos de refuerzo (``+R1``..``+R9``) aplicables a la categoría.

        Lee ``ens_measure_refuerzos.applicable_categories`` JSONB seedeado
        canónicamente desde RD 311/2022 Anexo II (SAN-C.MB-9.1). Una entry
        aplica a la categoría si su clave (``BASICA``/``MEDIA``/``ALTA``)
        está presente en el JSONB con valor ``required``.
        """
        result = await self.db.execute(
            sa_text(
                "SELECT refuerzo_level FROM ens_measure_refuerzos "
                "WHERE measure_code = :code "
                "AND applicable_categories ? :cat "
                "ORDER BY refuerzo_level"
            ),
            {"code": measure.codigo, "cat": category.value.upper()},
        )
        return [row[0] for row in result.fetchall()]

    def _reinforcement_applies(
        self,
        cat_minima: str | None,
        system_cat: CategoriaSistema,
    ) -> bool:
        """Check if a reinforcement's minimum category is met by the system."""
        if not cat_minima:
            return True
        order = {"B": 0, "M": 1, "A": 2, "BASICA": 0, "MEDIA": 1, "ALTA": 2}
        min_idx = order.get(cat_minima.upper(), 0)
        sys_idx = order.get(system_cat.value.upper(), 0)
        return sys_idx >= min_idx

    async def _get_magerit_safeguards(self, ens_code: str) -> list[str]:
        """Lee salvaguardas MAGERIT de magerit_ens_mapping (read-only)."""
        result = await self.db.execute(
            sa_text("SELECT magerit_safeguards FROM magerit_ens_mapping WHERE ens_measure = :code"),
            {"code": ens_code},
        )
        row = result.first()
        if not row or not row[0]:
            return []
        data = row[0]
        return data if isinstance(data, list) else []
