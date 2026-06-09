"""Checklist pre-auditoria (M9-A).

Verifica entregables, evidencias, registros operativos, firmas y cruza
DdA <-> Evidence para detectar contradicciones. Todo SQL real contra
modelos de M1/M3/M5/M6/M7/M8 (motores cerrados).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_prep import (
    AuditChecklistItem,
    AuditPreparationRun,
)
from backend.app.models.documents import Document, DocumentVersion, Evidence
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.integrations.m9_audit_prep import (
    count_findings_by_measure,
)


# =============== Catalogo de entregables por categoria (spec §2.15) ===============
#
# Lista completa auditable ENAC. Nomenclatura fija E-XXX; la carpeta
# destino se resuelve en dossier_generator.classify_folder().

# BASICA: 43 entregables minimos
_BASICA_DELIVS: list[str] = [
    # Gobierno
    "E-001", "E-002", "E-003", "E-005", "E-006",
    # Categorizacion
    "E-012",
    # Analisis de riesgos y DdA
    "E-020", "E-021", "E-022", "E-023", "E-024", "E-025", "E-026",
    "E-027", "E-028", "E-029", "E-030",
    "E-040", "E-050",
    # Politicas esenciales
    "E-100", "E-101", "E-102", "E-103", "E-104", "E-105", "E-106",
    "E-107", "E-108",
    # Procedimientos operativos clave
    "E-200", "E-201", "E-203", "E-204", "E-205", "E-207", "E-210",
    "E-218", "E-228",
    # Plan continuidad + BCP resumido
    "E-400", "E-500",
    # Informes tecnicos (verificacion v5.1)
    "E-702", "E-703",
]

# MEDIA: anade politicas adicionales + procedimientos + informes
_MEDIA_ADD: list[str] = [
    "E-109", "E-110", "E-111", "E-112", "E-113", "E-114",
    "E-202", "E-206", "E-208", "E-209", "E-211", "E-212", "E-213",
    "E-214", "E-215", "E-216", "E-217", "E-219", "E-220",
    "E-401", "E-402", "E-403", "E-404", "E-405", "E-406",
    "E-501", "E-502", "E-503", "E-504",
    "E-600", "E-601", "E-602", "E-603", "E-604", "E-605",
    "E-700", "E-701", "E-709",
]

# ALTA: anade procedimientos seguridad fisica + auditoria + red team
_ALTA_ADD: list[str] = [
    "E-115", "E-116", "E-117", "E-118", "E-119", "E-120",
    "E-121", "E-122", "E-123", "E-124", "E-125", "E-126",
    "E-221", "E-222", "E-223", "E-224", "E-225", "E-226",
    "E-227", "E-229", "E-230", "E-231", "E-232", "E-233",
    "E-234",
    "E-704",
]

REQUIRED_DELIVERABLES: dict[str, list[str]] = {
    "BASICA": list(dict.fromkeys(_BASICA_DELIVS)),
    "MEDIA": list(dict.fromkeys(_BASICA_DELIVS + _MEDIA_ADD)),
    "ALTA": list(dict.fromkeys(_BASICA_DELIVS + _MEDIA_ADD + _ALTA_ADD)),
}

# Documentos criticos que requieren firma digital (RSEG, gerencia o
# organo de aprobacion segun el tipo). Si falta firma el item baja a
# 'warning' aunque el documento exista.
REQUIRE_SIGNATURE: set[str] = {
    "E-001", "E-005", "E-012", "E-040", "E-050",
    # 27 politicas E-100..E-126
    *(f"E-{100 + i}" for i in range(27)),
    # Procedimientos criticos
    "E-200", "E-201", "E-204", "E-205", "E-210", "E-218", "E-228", "E-234",
    # Plan continuidad + BIA
    "E-400", "E-500",
    # Informes tecnicos
    "E-702", "E-703", "E-704",
}

# Umbral de dias para warning de proxima caducidad
EXPIRY_WARNING_DAYS = 30
REGISTROS_MESES_REQUERIDOS = 6


# =============== Exceptions ===============

class ChecklistError(ValueError):
    pass


# =============== Helpers de normalizacion ===============

def _normalize_categoria(cat: str) -> str:
    c = (cat or "").strip().upper()
    # Aceptar 'B'/'M'/'A' y full names
    if c in {"B", "BASICA", "BÁSICA", "BASIC"}:
        return "BASICA"
    if c in {"M", "MEDIA", "MEDIUM"}:
        return "MEDIA"
    if c in {"A", "ALTA", "HIGH"}:
        return "ALTA"
    raise ChecklistError(
        f"Categoria '{cat}' invalida. Validas: BASICA, MEDIA, ALTA"
    )


def get_required_deliverables(categoria: str) -> list[str]:
    return list(REQUIRED_DELIVERABLES[_normalize_categoria(categoria)])


# =============== Create run + persist items ===============

async def create_run(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> AuditPreparationRun:
    cat = _normalize_categoria(categoria)
    run = AuditPreparationRun(
        project_id=project_id,
        categoria=cat,
        estado="pending",
        checklist_results={},
        readiness_score=None,
    )
    db.add(run)
    await db.flush()
    return run


async def _add_item(
    db: AsyncSession,
    run: AuditPreparationRun,
    categoria_check: str,
    referencia: str,
    descripcion: str,
    estado: str,
    severidad: str = "info",
    detalle: Optional[str] = None,
    accion_sugerida: Optional[str] = None,
) -> AuditChecklistItem:
    item = AuditChecklistItem(
        run_id=run.id,
        project_id=run.project_id,
        categoria_check=categoria_check,
        referencia=referencia,
        descripcion=descripcion,
        estado=estado,
        severidad=severidad,
        detalle=detalle,
        accion_sugerida=accion_sugerida,
    )
    db.add(item)
    return item


# =============== Check 1: deliverables ===============

async def check_deliverables(
    db: AsyncSession, run: AuditPreparationRun,
) -> dict:
    required = get_required_deliverables(run.categoria)
    r = await db.execute(
        select(Document.template_codigo).where(
            Document.project_id == run.project_id,
            Document.template_codigo.isnot(None),
            Document.deleted_at.is_(None),
        )
    )
    present_codes = {row[0] for row in r.all() if row[0]}
    missing = [c for c in required if c not in present_codes]

    for code in required:
        if code in present_codes:
            await _add_item(
                db, run, "entregable", code,
                f"Entregable {code} presente", "ok", "info",
            )
        else:
            await _add_item(
                db, run, "entregable", code,
                f"Entregable {code} ausente", "missing", "error",
                detalle=f"No hay Document con template_codigo='{code}'",
                accion_sugerida=(
                    f"Generar el documento {code} antes de la auditoría"
                ),
            )
    return {
        "total": len(required),
        "present": len(required) - len(missing),
        "missing": missing,
    }


# =============== Check 2: evidence freshness ===============

async def check_evidence_freshness(
    db: AsyncSession, run: AuditPreparationRun,
) -> dict:
    today = date.today()
    warn_until = today + timedelta(days=EXPIRY_WARNING_DAYS)

    # Cargar DdA aplicables (aplicabilidad != 'no_aplica')
    r = await db.execute(
        select(DdaEntry, EnsMeasure.codigo).join(
            EnsMeasure, EnsMeasure.id == DdaEntry.measure_id,
        ).where(
            DdaEntry.project_id == run.project_id,
            DdaEntry.deleted_at.is_(None),
        )
    )
    dda_aplicables: list[tuple[DdaEntry, str]] = []
    for entry, codigo in r.all():
        if (entry.aplicabilidad or "").lower() == "no_aplica":
            continue
        dda_aplicables.append((entry, codigo))

    # Evidencias por medida
    r = await db.execute(
        select(Evidence).where(
            Evidence.project_id == run.project_id,
            Evidence.deleted_at.is_(None),
        )
    )
    evidences = list(r.scalars().all())

    # Index evidence por codigo de medida
    by_code: dict[str, list[Evidence]] = {}
    for ev in evidences:
        code = ev.measure_code
        if code is None and ev.measure_id:
            # fallback: lookup codigo via ens_measures
            pass  # lo resolvemos con una consulta adicional si hace falta
        if code:
            by_code.setdefault(code, []).append(ev)

    vigentes = 0
    caducadas = 0
    faltantes = 0
    proximas = 0

    for entry, codigo in dda_aplicables:
        ev_list = by_code.get(codigo, [])
        if not ev_list:
            faltantes += 1
            # Item: falta evidencia
            await _add_item(
                db, run, "evidencia", codigo,
                f"Medida {codigo} sin evidencia asociada",
                "missing", "warning",
                detalle=(
                    f"DdA aplicabilidad={entry.aplicabilidad}, "
                    f"estado={entry.estado_implementacion}"
                ),
                accion_sugerida=(
                    f"Aportar evidencia documental para la medida {codigo}"
                ),
            )
            continue

        # Encontrar la mas fresca vigente
        best: Optional[Evidence] = None
        for ev in ev_list:
            if not ev.vigente:
                continue
            if ev.fecha_caducidad and ev.fecha_caducidad < today:
                continue
            if best is None or (
                ev.fecha_evidencia and best.fecha_evidencia
                and ev.fecha_evidencia > best.fecha_evidencia
            ):
                best = ev

        if best is None:
            caducadas += 1
            latest = max(
                ev_list,
                key=lambda e: (e.fecha_caducidad or date.min),
            )
            await _add_item(
                db, run, "evidencia", codigo,
                f"Evidencia de {codigo} caducada o invalida",
                "expired", "error",
                detalle=(
                    f"fecha_caducidad mas reciente: "
                    f"{latest.fecha_caducidad}"
                ),
                accion_sugerida=f"Renovar evidencia de {codigo}",
            )
        else:
            vigentes += 1
            if (
                best.fecha_caducidad
                and best.fecha_caducidad <= warn_until
            ):
                proximas += 1
                await _add_item(
                    db, run, "frescura", codigo,
                    f"Evidencia de {codigo} proxima a caducar",
                    "warning", "warning",
                    detalle=(
                        f"fecha_caducidad: {best.fecha_caducidad}"
                    ),
                    accion_sugerida=(
                        "Planificar renovacion antes de la caducidad"
                    ),
                )
            else:
                await _add_item(
                    db, run, "evidencia", codigo,
                    f"Evidencia de {codigo} vigente",
                    "ok", "info",
                )

    total = len(dda_aplicables)
    return {
        "total": total,
        "vigentes": vigentes,
        "caducadas": caducadas,
        "faltantes": faltantes,
        "proximas_caducar": proximas,
    }


# =============== Check 3: operational records (6 months) ===============

async def check_operational_records(
    db: AsyncSession, run: AuditPreparationRun,
) -> dict:
    today = date.today()
    cutoff = today - timedelta(days=30 * REGISTROS_MESES_REQUERIDOS)

    r = await db.execute(
        select(Evidence.fecha_evidencia).where(
            Evidence.project_id == run.project_id,
            Evidence.deleted_at.is_(None),
            Evidence.tipo == "registro_operativo",
            Evidence.fecha_evidencia.isnot(None),
            Evidence.fecha_evidencia >= cutoff,
        )
    )
    fechas = [row[0] for row in r.all() if row[0]]

    meses_cubiertos: set[str] = set()
    for f in fechas:
        meses_cubiertos.add(f.strftime("%Y-%m"))

    # Generar lista de meses requeridos
    meses_req: list[str] = []
    for i in range(REGISTROS_MESES_REQUERIDOS):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        meses_req.append(f"{y:04d}-{m:02d}")

    gaps = [m for m in meses_req if m not in meses_cubiertos]
    ok = not gaps

    if ok:
        await _add_item(
            db, run, "registro_operativo", "registros_6_meses",
            "Registros operativos 6 meses completos", "ok", "info",
        )
    else:
        await _add_item(
            db, run, "registro_operativo", "registros_6_meses",
            f"Faltan registros operativos en {len(gaps)} meses",
            "fail", "warning",
            detalle=f"Meses sin registro: {gaps}",
            accion_sugerida="Aportar registros de los meses faltantes",
        )
    return {
        "meses_cubiertos": len(meses_req) - len(gaps),
        "meses_requeridos": REGISTROS_MESES_REQUERIDOS,
        "ok": ok,
        "gaps": gaps,
    }


# =============== Check 4: signatures ===============

async def check_signatures(
    db: AsyncSession, run: AuditPreparationRun,
) -> dict:
    required = [
        c for c in get_required_deliverables(run.categoria)
        if c in REQUIRE_SIGNATURE
    ]
    r = await db.execute(
        select(Document).where(
            Document.project_id == run.project_id,
            Document.template_codigo.in_(required),
            Document.deleted_at.is_(None),
        )
    )
    docs = list(r.scalars().all())
    by_code: dict[str, Document] = {}
    for d in docs:
        by_code[d.template_codigo] = d

    firmadas = 0
    pendientes: list[str] = []

    for code in required:
        d = by_code.get(code)
        if d is None:
            # el documento ni existe — ya se marco missing en deliverables
            pendientes.append(code)
            continue
        has_sig = bool(d.signature_ed25519) or bool(d.aprobado_por)
        if not has_sig:
            # buscar en document_versions
            r2 = await db.execute(
                select(DocumentVersion.firmado_por).where(
                    DocumentVersion.document_id == d.id,
                    DocumentVersion.firmado_por.isnot(None),
                    DocumentVersion.deleted_at.is_(None),
                ).limit(1)
            )
            has_sig = r2.scalar_one_or_none() is not None
        if has_sig:
            firmadas += 1
            await _add_item(
                db, run, "firma", code,
                f"Documento {code} firmado", "ok", "info",
            )
        else:
            pendientes.append(code)
            await _add_item(
                db, run, "firma", code,
                f"Documento {code} sin firma", "fail", "warning",
                detalle="Falta firma/aprobacion",
                accion_sugerida=(
                    f"Firmar el documento {code} por el responsable competente"
                ),
            )
    return {
        "total": len(required),
        "firmadas": firmadas,
        "pendientes": pendientes,
    }


# =============== Check 5: cross-validation DdA <-> Evidence ===============

async def cross_validate_dda_evidence(
    db: AsyncSession, run: AuditPreparationRun,
) -> list[dict]:
    today = date.today()

    r = await db.execute(
        select(DdaEntry, EnsMeasure.codigo).join(
            EnsMeasure, EnsMeasure.id == DdaEntry.measure_id,
        ).where(
            DdaEntry.project_id == run.project_id,
            DdaEntry.deleted_at.is_(None),
        )
    )
    entries = [(e, c) for e, c in r.all()]

    r = await db.execute(
        select(Evidence.measure_code, Evidence.vigente, Evidence.fecha_caducidad)
        .where(
            Evidence.project_id == run.project_id,
            Evidence.deleted_at.is_(None),
        )
    )
    ev_index: dict[str, list[tuple[bool, Optional[date]]]] = {}
    for code, vigente, caducidad in r.all():
        if not code:
            continue
        ev_index.setdefault(code, []).append((bool(vigente), caducidad))

    contradictions: list[dict] = []

    for entry, codigo in entries:
        est = (entry.estado_implementacion or "").lower()
        apl = (entry.aplicabilidad or "").lower()
        ev_list = ev_index.get(codigo, [])
        has_vigente = any(
            v and (c is None or c >= today) for v, c in ev_list
        )

        if apl == "no_aplica":
            continue  # no requiere evidencia

        if est == "implantado" and not has_vigente:
            contra = {
                "medida": codigo,
                "dda_estado": entry.estado_implementacion,
                "evidencia_estado": "sin_evidencia_vigente",
                "descripcion": (
                    f"DdA dice 'implantado' pero no hay evidencia vigente "
                    f"en Evidence Vault para {codigo}"
                ),
                "severidad": "error",
            }
            contradictions.append(contra)
            await _add_item(
                db, run, "contradiccion", codigo,
                "Contradiccion: implantado sin evidencia",
                "contradiction", "error",
                detalle=contra["descripcion"],
                accion_sugerida=(
                    "Aportar evidencia de la medida o corregir estado en DdA"
                ),
            )
        elif est == "en_proceso" and not has_vigente:
            contra = {
                "medida": codigo,
                "dda_estado": entry.estado_implementacion,
                "evidencia_estado": "sin_evidencia",
                "descripcion": (
                    f"DdA dice 'en_proceso' sin evidencia aun para {codigo}"
                ),
                "severidad": "warning",
            }
            contradictions.append(contra)
            await _add_item(
                db, run, "contradiccion", codigo,
                "En proceso sin evidencia", "warning", "warning",
                detalle=contra["descripcion"],
            )

    # Cruce con verification_findings (M8 v5.1).
    pentest_by_measure: dict[str, int] = await count_findings_by_measure(
        db, run.project_id,
    )

    for entry, codigo in entries:
        est = (entry.estado_implementacion or "").lower()
        if est == "implantado" and codigo in pentest_by_measure:
            contra = {
                "medida": codigo,
                "dda_estado": entry.estado_implementacion,
                "evidencia_estado": "pentest_high_finding",
                "descripcion": (
                    f"DdA dice 'implantado' pero pentest detecto "
                    f"{pentest_by_measure[codigo]} hallazgo(s) "
                    f"high/critical en {codigo}"
                ),
                "severidad": "error",
            }
            contradictions.append(contra)
            await _add_item(
                db, run, "contradiccion", codigo,
                "DdA implantado vs pentest high/critical",
                "contradiction", "error",
                detalle=contra["descripcion"],
                accion_sugerida=(
                    "Revisar: aceptar finding y reclasificar estado, "
                    "o aportar evidencia de remediacion"
                ),
            )
    return contradictions


# =============== Readiness score ===============

# =============== Validacion bloqueante para generar dossier ===============

BLOCKING_THRESHOLD = 85  # readiness minimo para dossier final firmable


def _collect_blockers(results: dict) -> list[dict]:
    """Extrae los items bloqueantes del resultado de checklist.

    Un item es bloqueante si:
    - Es un entregable 'missing' (E-012/E-040/E-050 siempre bloqueantes)
    - Es una contradiccion con severidad 'error' (DdA implantado sin evidencia
      o pentest high/critical sobre medida implantada)
    - Faltan firmas en documentos REQUIRE_SIGNATURE
    - < 6 meses de registros operativos cuando BASICA+
    """
    blockers: list[dict] = []

    entregables = results.get("entregables") or {}
    missing = entregables.get("missing") or []
    for m in missing:
        blockers.append({
            "tipo": "entregable_missing",
            "codigo": m,
            "severidad": "error",
            "descripcion": f"Entregable obligatorio {m} no encontrado",
        })

    contras = results.get("contradicciones") or []
    for c in contras:
        if c.get("severidad") == "error":
            blockers.append({
                "tipo": "contradiccion",
                "codigo": c.get("medida", "?"),
                "severidad": "error",
                "descripcion": c.get("descripcion", ""),
            })

    firmas = results.get("firmas") or {}
    missing_firmas = firmas.get("missing") or []
    for f in missing_firmas:
        blockers.append({
            "tipo": "firma_missing",
            "codigo": f,
            "severidad": "error",
            "descripcion": f"Documento {f} sin firma digital",
        })

    registros = results.get("registros_operativos") or {}
    if registros and not registros.get("ok", True):
        blockers.append({
            "tipo": "registros_insuficientes",
            "codigo": "registros_6m",
            "severidad": "error",
            "descripcion": (
                f"Faltan registros para alcanzar "
                f"{registros.get('meses_requeridos', REGISTROS_MESES_REQUERIDOS)} "
                f"meses (cubiertos: {registros.get('meses_cubiertos', 0)})"
            ),
        })

    return blockers


def require_complete_audit_prep(run) -> list[dict]:
    """Valida que un AuditPreparationRun este listo para generar dossier.

    Devuelve lista de blockers. Si esta vacia, el dossier puede emitirse
    firmable. En cualquier otro caso, el caller debe decidir si bloquea
    (modo default) o emite dossier parcial con sello 'BORRADOR'.

    Raises: ChecklistError si el run esta en estado invalido
    (no completado, sin resultados).
    """
    if run is None:
        raise ChecklistError("run es None")
    results = run.checklist_results or {}
    if not results:
        raise ChecklistError(
            "El run no tiene resultados de checklist. "
            "Ejecuta run_full_checklist() primero.",
        )
    blockers = _collect_blockers(results)
    # Score minimo
    score = run.readiness_score
    if score is None:
        score = calculate_readiness_score(results)
    if score < BLOCKING_THRESHOLD and not blockers:
        blockers.append({
            "tipo": "score_insuficiente",
            "codigo": "readiness",
            "severidad": "error",
            "descripcion": (
                f"Puntuacion de preparacion {score}/100 "
                f"inferior al umbral {BLOCKING_THRESHOLD}"
            ),
        })
    return blockers


def calculate_readiness_score(results: dict) -> int:
    score = 0

    ent = results.get("entregables", {}) or {}
    total_e = ent.get("total", 0) or 0
    present_e = ent.get("present", 0) or 0
    if total_e > 0:
        score += int(30 * present_e / total_e)
    else:
        score += 30

    ev = results.get("evidencias", {}) or {}
    total_ev = ev.get("total", 0) or 0
    vigentes_ev = ev.get("vigentes", 0) or 0
    if total_ev > 0:
        score += int(30 * vigentes_ev / total_ev)
    else:
        score += 30

    contras = results.get("contradicciones", []) or []
    critical_contras = sum(
        1 for c in contras if c.get("severidad") == "error"
    )
    if critical_contras == 0:
        score += 20

    firmas = results.get("firmas", {}) or {}
    total_f = firmas.get("total", 0) or 0
    firmadas = firmas.get("firmadas", 0) or 0
    if total_f > 0:
        score += int(10 * firmadas / total_f)
    else:
        score += 10

    registros = results.get("registros_operativos", {}) or {}
    if registros.get("ok"):
        score += 10
    else:
        cubiertos = registros.get("meses_cubiertos", 0) or 0
        requeridos = registros.get("meses_requeridos", 1) or 1
        score += int(10 * cubiertos / requeridos)

    return max(0, min(100, score))


# =============== Orquestador ===============

async def run_full_checklist(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
    *, enforce_gates: bool = True,
) -> AuditPreparationRun:
    # Gate (P7-F1 · handoff H4): no se puede preparar la auditoría (Motor 9)
    # si no existe evidencia subida para el proyecto (Motor 7). Mirror del
    # patrón ya cableado en m03_dda/service.py.
    if enforce_gates:
        from backend.app.core.workflow_gates import require_some_evidence
        await require_some_evidence(db, project_id)

    run = await create_run(db, project_id, categoria)
    run.estado = "checking"
    run.started_at = datetime.now(timezone.utc)
    await db.flush()

    deliv = await check_deliverables(db, run)
    evid = await check_evidence_freshness(db, run)
    regs = await check_operational_records(db, run)
    firmas = await check_signatures(db, run)
    contras = await cross_validate_dda_evidence(db, run)

    results = {
        "entregables": deliv,
        "evidencias": evid,
        "registros_operativos": regs,
        "firmas": firmas,
        "contradicciones": contras,
    }
    run.checklist_results = results
    run.contradicciones_count = len(contras)
    run.alertas_count = (
        evid.get("caducadas", 0) + evid.get("faltantes", 0)
        + len(firmas.get("pendientes", []))
    )
    run.readiness_score = calculate_readiness_score(results)
    run.estado = "completed"
    run.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return run


# =============== Queries ===============

async def get_run(
    db: AsyncSession, run_id: uuid.UUID,
) -> Optional[AuditPreparationRun]:
    r = await db.execute(
        select(AuditPreparationRun).where(
            AuditPreparationRun.id == run_id,
            AuditPreparationRun.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def list_runs(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[AuditPreparationRun]:
    r = await db.execute(
        select(AuditPreparationRun)
        .where(
            AuditPreparationRun.project_id == project_id,
            AuditPreparationRun.deleted_at.is_(None),
        )
        .order_by(AuditPreparationRun.created_at.desc())
    )
    return list(r.scalars().all())


async def get_items(
    db: AsyncSession,
    run_id: uuid.UUID,
    categoria_check: Optional[str] = None,
    estado: Optional[str] = None,
    severidad: Optional[str] = None,
) -> list[AuditChecklistItem]:
    stmt = select(AuditChecklistItem).where(
        AuditChecklistItem.run_id == run_id,
        AuditChecklistItem.deleted_at.is_(None),
    )
    if categoria_check:
        stmt = stmt.where(AuditChecklistItem.categoria_check == categoria_check)
    if estado:
        stmt = stmt.where(AuditChecklistItem.estado == estado)
    if severidad:
        stmt = stmt.where(AuditChecklistItem.severidad == severidad)
    r = await db.execute(stmt.order_by(AuditChecklistItem.created_at.asc()))
    return list(r.scalars().all())


async def resolve_item(
    db: AsyncSession, item_id: uuid.UUID, resuelto_por: str,
) -> Optional[AuditChecklistItem]:
    r = await db.execute(
        select(AuditChecklistItem).where(
            AuditChecklistItem.id == item_id,
            AuditChecklistItem.deleted_at.is_(None),
        )
    )
    item = r.scalar_one_or_none()
    if item is None:
        return None
    item.resuelto = True
    item.resuelto_at = datetime.now(timezone.utc)
    item.resuelto_por = resuelto_por
    await db.flush()
    return item


async def get_contradictions(
    db: AsyncSession, run_id: uuid.UUID,
) -> list[AuditChecklistItem]:
    return await get_items(db, run_id, categoria_check="contradiccion")


async def soft_delete_run(
    db: AsyncSession, run_id: uuid.UUID,
) -> bool:
    run = await get_run(db, run_id)
    if run is None:
        return False
    run.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True


# =============== Dicts ===============

def run_to_dict(run: AuditPreparationRun) -> dict:
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "categoria": run.categoria,
        "estado": run.estado,
        "checklist_results": run.checklist_results or {},
        "readiness_score": run.readiness_score,
        "contradicciones_count": run.contradicciones_count,
        "alertas_count": run.alertas_count,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": (
            run.completed_at.isoformat() if run.completed_at else None
        ),
        "dossier_zip_path": run.dossier_zip_path,
        "dossier_generated_at": (
            run.dossier_generated_at.isoformat()
            if run.dossier_generated_at else None
        ),
        "matriz_99_path": run.matriz_99_path,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def item_to_dict(item: AuditChecklistItem) -> dict:
    return {
        "id": str(item.id),
        "run_id": str(item.run_id),
        "project_id": str(item.project_id),
        "categoria_check": item.categoria_check,
        "referencia": item.referencia,
        "descripcion": item.descripcion,
        "estado": item.estado,
        "severidad": item.severidad,
        "detalle": item.detalle,
        "accion_sugerida": item.accion_sugerida,
        "resuelto": item.resuelto,
        "resuelto_at": item.resuelto_at.isoformat() if item.resuelto_at else None,
        "resuelto_por": item.resuelto_por,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# =============== Readiness quick (sin crear run) ===============

async def readiness_quick(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> dict:
    """Score rapido leyendo el estado actual sin persistir items."""
    cat = _normalize_categoria(categoria)
    required = REQUIRED_DELIVERABLES[cat]

    # Documentos presentes
    r = await db.execute(
        select(Document.template_codigo).where(
            Document.project_id == project_id,
            Document.template_codigo.isnot(None),
            Document.deleted_at.is_(None),
        )
    )
    present = {row[0] for row in r.all() if row[0]}
    deliv = {
        "total": len(required),
        "present": sum(1 for c in required if c in present),
        "missing": [c for c in required if c not in present],
    }

    # Evidencias vigentes
    today = date.today()
    r = await db.execute(
        select(Evidence.vigente, Evidence.fecha_caducidad).where(
            Evidence.project_id == project_id,
            Evidence.deleted_at.is_(None),
        )
    )
    total_ev = 0
    vigentes_ev = 0
    for vigente, caducidad in r.all():
        total_ev += 1
        if vigente and (caducidad is None or caducidad >= today):
            vigentes_ev += 1

    evid = {
        "total": total_ev,
        "vigentes": vigentes_ev,
        "caducadas": total_ev - vigentes_ev,
        "faltantes": 0,
        "proximas_caducar": 0,
    }

    results = {
        "entregables": deliv,
        "evidencias": evid,
        "registros_operativos": {"ok": False, "meses_cubiertos": 0, "meses_requeridos": 6},
        "firmas": {"total": 0, "firmadas": 0},
        "contradicciones": [],
    }
    score = calculate_readiness_score(results)
    return {
        "categoria": cat,
        "readiness_score": score,
        "entregables_presentes": deliv["present"],
        "entregables_total": deliv["total"],
        "evidencias_vigentes": vigentes_ev,
        "evidencias_total": total_ev,
        "interpretation": (
            "listo_auditoria" if score >= 90
            else "ajustes_menores" if score >= 70
            else "trabajo_significativo" if score >= 50
            else "no_presentar"
        ),
    }
