"""M9 — Agente 11 Auditor Interno Virtual (pre-externa ENAC).

Ejecuta 10-15 preguntas tipo auditor real sobre el proyecto, valida
respuestas contra Evidence Vault (M7) + Documents (M6) + hallazgos de
verificacion (M8 v5.1), y emite un informe E-701 con score 0-100 y
lista de hallazgos potenciales.

Flujo:
1. ``run_internal_audit(db, project_id, categoria)`` produce una lista
   de ``InternalAuditQuestion`` con respuesta automatica y veredicto.
2. ``build_e701_context`` construye el contexto para el template E-701
   del M6 Document Factory.
3. El caller invoca ``DocumentFactoryService.generate_document("E-701")``
   con ese contexto.

Diseno:
- 100% determinista en offline (no depende de Haiku): cada pregunta
  tiene una verificacion programatica.
- Si hay Anthropic API key, el caller puede enriquecer las respuestas
  con el LLM Router, pero la emision del informe NO lo requiere.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.fulkro_identity import FULKRO_AUTHOR_NAME, FULKRO_AUTHOR_ROLE
from backend.app.models.documents import Document, Evidence
from backend.app.motors.m08_verification.integrations.m9_audit_prep import (
    collect_findings_for_dossier, has_verification_run,
)


# ════════════════════════════════════════════════════════════════════
# Question catalog
# ════════════════════════════════════════════════════════════════════

@dataclass
class InternalAuditQuestion:
    code: str
    area: str
    question: str
    verdict: str = "not_assessed"   # ok | partial | fail | not_assessed
    evidence_refs: list[str] = field(default_factory=list)
    answer: str = ""
    weight: int = 1                 # contribucion al score (1-3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "area": self.area,
            "question": self.question,
            "verdict": self.verdict,
            "evidence_refs": list(self.evidence_refs),
            "answer": self.answer,
            "weight": self.weight,
        }


VERDICT_WEIGHT = {"ok": 1.0, "partial": 0.5, "fail": 0.0, "not_assessed": 0.0}


# Banco de preguntas tipo auditor ENAC (minimo 15 — version condensada
# del checklist de ENAC para auditoria interna pre-externa).
QUESTION_BANK: list[dict[str, Any]] = [
    {
        "code": "Q-001", "area": "gobierno", "weight": 3,
        "question": (
            "¿Existe una Politica de Seguridad de la Informacion aprobada "
            "formalmente por el organo de gobierno y en vigor?"
        ),
        "check_kind": "document_exists", "code_required": "E-100",
    },
    {
        "code": "Q-002", "area": "gobierno", "weight": 3,
        "question": (
            "¿Se han asignado formalmente los roles de Responsable de la "
            "Informacion, del Servicio, de Seguridad y del Sistema?"
        ),
        # FIX(catalog): E-005 no tiene plantilla → Q-002 fallaba SIEMPRE (weight 3).
        # El acta de nombramiento de roles ENS es E-002 (existe en el registry).
        "check_kind": "document_exists", "code_required": "E-002",
    },
    {
        "code": "Q-003", "area": "categorizacion", "weight": 3,
        "question": (
            "¿Existe un acta de categorizacion del sistema firmada y vigente?"
        ),
        "check_kind": "document_signed", "code_required": "E-012",
    },
    {
        "code": "Q-004", "area": "riesgos", "weight": 2,
        "question": (
            "¿Se ha realizado un analisis de riesgos MAGERIT y esta "
            "documentado el plan de tratamiento?"
        ),
        # NOTA(honest-path): E-050 = INFORME DE AUDITORÍA INTERNA (duplica Q-007 ·
        # semánticamente incorrecto para MAGERIT). No existe plantilla emitible de
        # análisis de riesgos MAGERIT dedicada en el registry (vive en M02), así
        # que NO se reasigna a un código inventado. Módulo A11/E-701 aún latente
        # (sin caller de producción); revisar code_required con Marcos al cablearlo.
        "check_kind": "document_exists", "code_required": "E-050",
    },
    {
        "code": "Q-005", "area": "dda", "weight": 3,
        "question": (
            "¿La Declaracion de Aplicabilidad esta firmada por el RSEG "
            "y refleja el estado actual de todas las medidas aplicables?"
        ),
        "check_kind": "document_signed", "code_required": "E-040",
    },
    {
        "code": "Q-006", "area": "continuidad", "weight": 2,
        "question": (
            "¿Existe analisis de impacto (BIA) y plan de continuidad "
            "aprobados, con pruebas documentadas en los ultimos 12 meses?"
        ),
        "check_kind": "document_exists", "code_required": "E-400",
    },
    {
        "code": "Q-007", "area": "auditoria_interna", "weight": 3,
        "question": (
            "¿Se ha realizado una auditoria interna del SGSI previa a la "
            "auditoria externa y esta documentado su informe?"
        ),
        "check_kind": "document_exists", "code_required": "E-050",
    },
    {
        "code": "Q-008", "area": "evidencias_opexp5", "weight": 3,
        "question": (
            "¿Hay evidencia vigente de gestion de vulnerabilidades "
            "(op.exp.5) en los ultimos 6 meses?"
        ),
        "check_kind": "evidence_fresh", "measure_code": "op.exp.5",
    },
    {
        "code": "Q-009", "area": "evidencias_opacc", "weight": 2,
        "question": (
            "¿Hay evidencias de revision de accesos privilegiados "
            "(op.acc.4/op.acc.6) en los ultimos 6 meses?"
        ),
        "check_kind": "evidence_fresh_any",
        "measure_codes": ["op.acc.4", "op.acc.6"],
    },
    {
        "code": "Q-010", "area": "procedimientos", "weight": 2,
        "question": (
            "¿Esta vigente el procedimiento de gestion de incidentes y "
            "existen registros de incidentes o simulacros?"
        ),
        "check_kind": "document_exists", "code_required": "E-204",
    },
    {
        "code": "Q-011", "area": "formacion", "weight": 1,
        "question": (
            "¿Existe plan de formacion en seguridad y registros de "
            "asistencia/evaluaciones?"
        ),
        # FIX(catalog): E-207 = PROCEDIMIENTO DE COPIAS DE SEGURIDAD (backup), NO
        # formación → E-500 = PLAN ANUAL DE FORMACIÓN Y CONCIENCIACIÓN.
        "check_kind": "document_exists", "code_required": "E-500",
    },
    {
        "code": "Q-012", "area": "proveedores", "weight": 2,
        "question": (
            "¿Existe inventario de proveedores y procedimiento de "
            "evaluacion de riesgos de terceros (op.ext.4)?"
        ),
        "check_kind": "document_exists", "code_required": "E-217",
    },
    {
        "code": "Q-013", "area": "verificacion_tecnica", "weight": 3,
        "question": (
            "¿Se ha ejecutado al menos un run de verificacion tecnica y "
            "existe informe E-702 emitido?"
        ),
        "check_kind": "verification_run_exists",
    },
    {
        "code": "Q-014", "area": "verificacion_tecnica_critical", "weight": 3,
        "question": (
            "¿No quedan hallazgos tecnicos criticos o altos abiertos sin "
            "remediacion ni aceptacion formal?"
        ),
        "check_kind": "no_high_critical_open",
    },
    {
        "code": "Q-015", "area": "contradicciones_dda", "weight": 3,
        "question": (
            "¿No existen contradicciones 'error' entre la DdA y las "
            "evidencias disponibles (implantado sin evidencia vigente)?"
        ),
        "check_kind": "no_dda_contradictions",
    },
]


# ════════════════════════════════════════════════════════════════════
# Checkers (cada kind tiene su implementacion async)
# ════════════════════════════════════════════════════════════════════

async def _check_document_exists(
    db: AsyncSession, project_id: uuid.UUID, code: str,
    *, require_signature: bool = False,
) -> tuple[str, str, list[str]]:
    stmt = select(Document).where(
        Document.project_id == project_id,
        Document.deleted_at.is_(None),
        Document.template_codigo == code,
    )
    docs = list((await db.execute(stmt)).scalars().all())
    if not docs:
        return (
            "fail",
            f"No se encontro documento {code}.",
            [],
        )
    signed = [d for d in docs if d.signature_ed25519]
    refs = [f"{d.template_codigo}:{d.id}" for d in docs[:3]]
    if require_signature and not signed:
        return (
            "partial",
            f"Documento {code} existe pero no esta firmado digitalmente.",
            refs,
        )
    return (
        "ok",
        f"Documento {code} presente{' y firmado' if signed else ''}.",
        refs,
    )


async def _check_evidence_fresh(
    db: AsyncSession, project_id: uuid.UUID, measure_codes: list[str],
    *, max_age_days: int = 180,
) -> tuple[str, str, list[str]]:
    stmt = select(Evidence).where(
        Evidence.project_id == project_id,
        Evidence.deleted_at.is_(None),
        Evidence.measure_code.in_(measure_codes),
    )
    all_ev = list((await db.execute(stmt)).scalars().all())
    today = date.today()
    fresh = []
    for e in all_ev:
        if not e.vigente:
            continue
        if e.fecha_caducidad and e.fecha_caducidad < today:
            continue
        ref_date = e.fecha_evidencia or (
            e.created_at.date() if e.created_at else None
        )
        if ref_date and (today - ref_date).days <= max_age_days:
            fresh.append(e)
    if not fresh:
        codes_str = ", ".join(measure_codes)
        return (
            "fail",
            f"No hay evidencias vigentes para {codes_str} "
            f"(ultimo limite: {max_age_days} dias).",
            [],
        )
    refs = [f"{e.measure_code}:{(e.hash_sha256 or '')[:10]}" for e in fresh[:3]]
    return (
        "ok",
        f"{len(fresh)} evidencia(s) vigentes en ventana de {max_age_days} dias.",
        refs,
    )


async def _check_verification_run_exists(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[str, str, list[str]]:
    has_run = await has_verification_run(db, project_id)
    if not has_run:
        return (
            "fail",
            "No se ha ejecutado ninguna verificacion tecnica.",
            [],
        )
    # Hay al menos 1 run; ¿ha emitido E-702?
    stmt = select(Document).where(
        Document.project_id == project_id,
        Document.deleted_at.is_(None),
        Document.template_codigo == "E-702",
    )
    e702 = list((await db.execute(stmt)).scalars().all())
    if not e702:
        return (
            "partial",
            "Hay runs de verificacion pero no se ha emitido E-702.",
            [],
        )
    refs = [f"E-702:{d.id}" for d in e702[:3]]
    return ("ok", "Verificacion ejecutada + E-702 emitido.", refs)


async def _check_no_high_critical_open(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[str, str, list[str]]:
    findings = await collect_findings_for_dossier(db, project_id)
    open_hc = [
        f for f in findings
        if (f.get("severity") or "").lower() in ("critical", "high")
        and (f.get("status") or "open") in ("open", "needs_review")
    ]
    if open_hc:
        refs = [f"{f['severity']}:{f['title'][:40]}" for f in open_hc[:3]]
        return (
            "fail",
            f"Quedan {len(open_hc)} hallazgo(s) high/critical sin cerrar.",
            refs,
        )
    return ("ok", "Sin hallazgos high/critical abiertos.", [])


async def _check_no_dda_contradictions(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[str, str, list[str]]:
    from backend.app.motors.m08_verification.integrations.m3_dda_updater import (
        detect_dda_contradictions,
    )
    contras = await detect_dda_contradictions(db, project_id)
    error_contras = [c for c in contras if c.get("severidad") == "error"]
    if error_contras:
        refs = [c["medida"] for c in error_contras[:3]]
        return (
            "fail",
            f"Existen {len(error_contras)} contradicciones DdA vs evidencia/findings.",
            refs,
        )
    return ("ok", "Sin contradicciones graves DdA vs evidencias.", [])


# ════════════════════════════════════════════════════════════════════
# Orquestacion
# ════════════════════════════════════════════════════════════════════

async def run_internal_audit(
    db: AsyncSession, project_id: uuid.UUID, categoria: str,
) -> dict[str, Any]:
    """Ejecuta las 15 preguntas y devuelve resumen + detalle.

    No requiere API key externa; todas las comprobaciones son queries SQL.
    """
    results: list[InternalAuditQuestion] = []
    for q in QUESTION_BANK:
        kind = q["check_kind"]
        verdict: str = "not_assessed"
        answer: str = ""
        refs: list[str] = []
        if kind == "document_exists":
            verdict, answer, refs = await _check_document_exists(
                db, project_id, q["code_required"],
            )
        elif kind == "document_signed":
            verdict, answer, refs = await _check_document_exists(
                db, project_id, q["code_required"],
                require_signature=True,
            )
        elif kind == "evidence_fresh":
            verdict, answer, refs = await _check_evidence_fresh(
                db, project_id, [q["measure_code"]],
            )
        elif kind == "evidence_fresh_any":
            verdict, answer, refs = await _check_evidence_fresh(
                db, project_id, q["measure_codes"],
            )
        elif kind == "verification_run_exists":
            verdict, answer, refs = await _check_verification_run_exists(
                db, project_id,
            )
        elif kind == "no_high_critical_open":
            verdict, answer, refs = await _check_no_high_critical_open(
                db, project_id,
            )
        elif kind == "no_dda_contradictions":
            verdict, answer, refs = await _check_no_dda_contradictions(
                db, project_id,
            )
        else:  # pragma: no cover — kind desconocido
            verdict = "not_assessed"
            answer = f"Tipo de check no soportado: {kind}"
        results.append(InternalAuditQuestion(
            code=q["code"], area=q["area"], weight=q["weight"],
            question=q["question"], verdict=verdict,
            answer=answer, evidence_refs=refs,
        ))

    # Score ponderado
    total_weight = sum(r.weight for r in results)
    achieved = sum(
        r.weight * VERDICT_WEIGHT.get(r.verdict, 0.0) for r in results
    )
    score = int(round(100 * achieved / total_weight)) if total_weight else 0

    fail_findings = [r.to_dict() for r in results if r.verdict == "fail"]
    partial_findings = [r.to_dict() for r in results if r.verdict == "partial"]

    recomendacion = (
        "favorable" if score >= 85
        else "favorable_con_observaciones" if score >= 70
        else "requiere_trabajo_adicional"
    )

    return {
        "categoria": categoria,
        "score": score,
        "score_level": (
            "excelente" if score >= 90
            else "aceptable" if score >= 75
            else "mejorable" if score >= 50
            else "critico"
        ),
        "total_questions": len(results),
        "by_verdict": {
            "ok": sum(1 for r in results if r.verdict == "ok"),
            "partial": sum(1 for r in results if r.verdict == "partial"),
            "fail": sum(1 for r in results if r.verdict == "fail"),
            "not_assessed": sum(
                1 for r in results if r.verdict == "not_assessed"
            ),
        },
        "questions": [r.to_dict() for r in results],
        "potential_findings": fail_findings,
        "partial_findings": partial_findings,
        "recomendacion": recomendacion,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


async def build_e701_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    audit_result: dict[str, Any],
    cliente: dict[str, Any],
    proyecto: dict[str, Any],
    responsables: dict[str, Any],
    *,
    auditoria_meta: dict[str, Any] | None = None,
    cierre_ncs: list[dict[str, Any]] | None = None,
    puntos_riesgo: list[dict[str, Any]] | None = None,
    e700_audit_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye contexto completo para template E-701 (Path Hybrid Phase E).

    Polish exhaustivo · todos los placeholders del template
    ``E701_auditoria_interna_pre_externa.md`` quedan resueltos sin
    Jinja2 ``UndefinedError`` durante render M6.

    Variables resueltas:
      - ``cliente`` / ``proyecto`` / ``responsables`` (passed-through)
      - ``auditoria_interna`` (legacy · score + counts)
      - ``auditoria`` (metadata sección 3 alcance · fecha + auditor + e700_ref + externa_fecha)
      - ``preguntas`` (lista 15 preguntas con verdict)
      - ``cierre_ncs`` (cierre de NCs previas · default empty si no hay E-700 prior)
      - ``nuevas_ncs`` (mapeo audit_result.potential_findings → NCs detectadas)
      - ``observaciones`` (partial findings)
      - ``documentos_revisados`` (query top documents production-grade)
      - ``puntos_riesgo`` (free-text · default empty si auditor no aporta)
      - ``recomendaciones`` (derivadas score_level)
      - ``conclusion`` (estado + texto + recomendacion derivados score)
      - ``resumen`` (counts NCs cerradas/pendientes/nuevas)
      - ``hallazgos_potenciales`` (legacy alias de nuevas_ncs)
      - ``firmas`` (placeholder · nombre/cargo/fecha vacíos hasta firma RSEG)

    Args:
        db: AsyncSession para query documentos_revisados.
        project_id: UUID proyecto para query Document table.
        audit_result: output de ``run_internal_audit``.
        cliente / proyecto / responsables: passed-through al template.
        auditoria_meta: opcional override de la sección "auditoria" (alcance).
        cierre_ncs: opcional NCs previas de E-700 (si se ejecutó · default empty).
        puntos_riesgo: opcional puntos riesgo extra (auditor consultor).
        e700_audit_result: opcional output previo E-700 para resumen NCs.
    """
    score = audit_result.get("score", 0)
    score_level = audit_result.get("score_level", "")
    by_verdict = audit_result.get("by_verdict", {})

    # Mapeo potential_findings → nuevas_ncs (formato template)
    nuevas_ncs: list[dict[str, Any]] = []
    for idx, finding in enumerate(audit_result.get("potential_findings", []), 1):
        verdict_to_severity = {
            "fail": "alta", "partial": "media", "ok": "baja",
        }
        sev = verdict_to_severity.get(finding.get("verdict"), "media")
        nuevas_ncs.append({
            "id": f"NC-{idx:03d}",
            "medida": finding.get("area", ""),
            "tipo": "menor" if sev == "baja" else "mayor",
            "descripcion": finding.get("answer", finding.get("question", "")),
            "severidad": sev,
            "plazo": "antes_auditoria_externa",
        })

    # Documentos revisados · query top N documentos del proyecto
    documentos_revisados: list[dict[str, Any]] = []
    docs_query = await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        ).order_by(Document.template_codigo.asc())
    )
    for doc in list(docs_query.scalars().all())[:25]:  # top 25 docs
        coherencia = "Coherente" if doc.signature_ed25519 else "Pendiente firma"
        documentos_revisados.append({
            "nombre": f"{doc.template_codigo or 'sin_codigo'} - {doc.nombre or ''}",
            "version": doc.version_actual or "1.0",
            "aprobado_por": doc.aprobado_por or "Pendiente",
            "fecha": (
                doc.fecha_aprobacion.isoformat() if doc.fecha_aprobacion else "-"
            ),
            "coherencia": coherencia,
        })

    # Resumen NCs · combina E-700 previo (si hay) + audit actual
    if e700_audit_result:
        ncs_iniciales = len(e700_audit_result.get("potential_findings", []))
        cierre = cierre_ncs or []
        ncs_cerradas = sum(
            1 for c in cierre if str(c.get("estado", "")).lower() == "cerrada"
        )
        ncs_pendientes = ncs_iniciales - ncs_cerradas
    else:
        ncs_iniciales = 0
        ncs_cerradas = 0
        ncs_pendientes = 0
    resumen = {
        "ncs_iniciales": ncs_iniciales,
        "ncs_cerradas": ncs_cerradas,
        "ncs_pendientes": max(0, ncs_pendientes),
        "ncs_nuevas": len(nuevas_ncs),
    }

    # Recomendaciones derivadas score level
    recomendaciones = _build_recomendaciones(score, score_level, nuevas_ncs)

    # Conclusión derivada score
    if score >= 90:
        estado = "LISTO PARA AUDITORÍA EXTERNA"
        recomendacion = "favorable"
        texto = (
            "El sistema presenta un nivel de preparación excelente. Las "
            "evidencias documentales y técnicas están en regla. Procede "
            "convocar la auditoría externa por entidad acreditada ENAC."
        )
    elif score >= 75:
        estado = "ACEPTABLE CON OBSERVACIONES"
        recomendacion = "favorable_con_observaciones"
        texto = (
            "El sistema es presentable a auditoría externa con observaciones "
            "menores. Se recomienda cerrar las NCs nuevas detectadas antes "
            "de la fecha de auditoría externa."
        )
    elif score >= 50:
        estado = "MEJORABLE · TRABAJO ADICIONAL REQUERIDO"
        recomendacion = "requiere_trabajo_adicional"
        texto = (
            "Existen hallazgos significativos pendientes. Se recomienda "
            "completar las NCs nuevas y reforzar evidencias antes de la "
            "auditoría externa."
        )
    else:
        estado = "NO RECOMENDADO PARA AUDITORÍA EXTERNA"
        recomendacion = "no_presentar"
        texto = (
            "El sistema no está preparado para auditoría externa. Se "
            "recomienda un plan de adecuación intensivo antes de convocar "
            "auditoría externa."
        )
    conclusion = {
        "estado": estado,
        "texto": texto,
        "recomendacion": recomendacion,
    }

    # Auditoría meta (sección 3 alcance template) · default sensato
    today_iso = date.today().isoformat()
    auditoria_default = {
        "fecha_inicio": today_iso,
        "fecha_fin": today_iso,
        "auditor_jefe": (
            responsables.get("consultor", {}).get("nombre")
            if isinstance(responsables, dict) else None
        ) or FULKRO_AUTHOR_NAME,
        "equipo_auditor": (
            responsables.get("consultor", {}).get("nombre")
            if isinstance(responsables, dict) else None
        ) or f"{FULKRO_AUTHOR_NAME} (auditor único)",
        "e700_ref": "n/a",
        "externa_fecha": "Por definir según disponibilidad ENAC",
    }
    if auditoria_meta:
        auditoria_default.update(auditoria_meta)

    # Firmas · placeholder · nombre/cargo/fecha vacíos hasta firma RSEG real
    firmas = {
        "elaborado": {
            "nombre": (
                responsables.get("consultor", {}).get("nombre")
                if isinstance(responsables, dict) else None
            ) or FULKRO_AUTHOR_NAME,
            "cargo": (
                responsables.get("consultor", {}).get("cargo")
                if isinstance(responsables, dict) else None
            ) or FULKRO_AUTHOR_ROLE,
            "fecha": today_iso,
            "firma_marca": "—",  # se rellena al firmar Ed25519
        },
        "revisado": {
            "nombre": (
                responsables.get("responsable_seguridad", {}).get("nombre")
                if isinstance(responsables, dict) else None
            ) or "Responsable de Seguridad",
            "cargo": (
                responsables.get("responsable_seguridad", {}).get("cargo")
                if isinstance(responsables, dict) else None
            ) or "RSEG",
            "fecha": "—",
            "firma_marca": "—",
        },
        "aprobado": {
            "nombre": cliente.get("organo_aprobador_politicas", "Órgano de Gobierno"),
            "cargo": "Órgano competente de la Entidad",
            "fecha": "—",
            "firma_marca": "—",
        },
    }

    return {
        "cliente": cliente,
        "proyecto": proyecto,
        "responsables": responsables,
        # Sección 3 alcance · template variables
        "auditoria": auditoria_default,
        # Sección 1-2 + 4 metadatos auditoría interna
        "auditoria_interna": {
            "fecha_ejecucion": audit_result.get("executed_at", ""),
            "score": score,
            "score_level": score_level,
            "recomendacion": audit_result.get("recomendacion", ""),
            "total_preguntas": audit_result.get("total_questions", 0),
            "ok": by_verdict.get("ok", 0),
            "partial": by_verdict.get("partial", 0),
            "fail": by_verdict.get("fail", 0),
        },
        # Sección 5 cierre NCs E-700 previas
        "cierre_ncs": cierre_ncs or [],
        # Sección 6 nuevas NCs detectadas pre-externa
        "nuevas_ncs": nuevas_ncs,
        # Sección 7 documentación revisada
        "documentos_revisados": documentos_revisados,
        # Sección 8 puntos riesgo identificados (free-text auditor)
        "puntos_riesgo": puntos_riesgo or [],
        # Sección 9 recomendaciones pre-externa
        "recomendaciones": recomendaciones,
        # Sección 10 conclusión auditor jefe
        "conclusion": conclusion,
        # Resumen contadores
        "resumen": resumen,
        # Tabla firmas
        "firmas": firmas,
        # Legacy aliases (compatibilidad código existente que esperaba estos nombres)
        "preguntas": audit_result.get("questions", []),
        "hallazgos_potenciales": audit_result.get("potential_findings", []),
        "observaciones": audit_result.get("partial_findings", []),
    }


def _build_recomendaciones(
    score: int, score_level: str, nuevas_ncs: list[dict[str, Any]],
) -> list[str]:
    """Genera lista de recomendaciones pre-externa basadas en score + NCs."""
    recomendaciones: list[str] = []
    if score >= 90:
        recomendaciones.append(
            "Convocar auditoría externa ENAC en la ventana planificada · "
            "todo en regla."
        )
    elif score >= 75:
        recomendaciones.append(
            "Cerrar las NCs nuevas detectadas antes de auditoría externa."
        )
        recomendaciones.append(
            "Mantener evidencias vigentes durante los próximos 30 días."
        )
    elif score >= 50:
        recomendaciones.append(
            "Plan intensivo de cierre de hallazgos críticos."
        )
        recomendaciones.append(
            "Refrescar evidencias caducadas · revisar plan de tratamiento."
        )
        recomendaciones.append(
            "Considerar diferir la fecha de auditoría externa 2-4 semanas."
        )
    else:
        recomendaciones.append(
            "Plan de adecuación completo antes de convocar auditoría externa."
        )
        recomendaciones.append(
            "Re-ejecutar auditoría interna pre-externa cuando score > 75."
        )

    # Específicas por NCs altas
    sev_altas = sum(1 for nc in nuevas_ncs if nc.get("severidad") == "alta")
    if sev_altas > 0:
        recomendaciones.append(
            f"Atención prioritaria: {sev_altas} NC(s) de severidad alta "
            f"requieren cierre antes de auditoría externa."
        )
    return recomendaciones


__all__ = [
    "InternalAuditQuestion",
    "QUESTION_BANK",
    "build_e701_context",
    "run_internal_audit",
    "_build_recomendaciones",
]
