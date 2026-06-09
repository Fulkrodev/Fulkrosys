"""Orchestrator for Motor 21 Organizational Diagnosis."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import DiagnosisRun
from backend.app.motors.m16_onboarding.token_encryption import encrypt_credentials, decrypt_credentials

from .stakeholder_service import analyze_stakeholders
from .process_service import inventory_processes
from .compliance_service import detect_compliance_obligations
from .maturity_service import calculate_maturity


class DiagnosisError(ValueError):
    pass


async def run_diagnosis(
    session: AsyncSession,
    project_id: uuid.UUID,
    sector: str,
    triggered_by: str = "marcos",
    confidential_notes: Optional[str] = None,
) -> dict:
    run = DiagnosisRun(project_id=project_id, status="running", triggered_by=triggered_by)
    session.add(run)
    await session.flush()

    try:
        run.stakeholder_analysis = await analyze_stakeholders(session, project_id)
        run.process_inventory = await inventory_processes(session, project_id)
        run.compliance_detection = await detect_compliance_obligations(session, project_id, sector)
        run.maturity_scoring = await calculate_maturity(session, project_id)

        run.summary = {
            "stakeholders_verdict": run.stakeholder_analysis["verdict"],
            "stakeholders_critical_gaps": run.stakeholder_analysis["critical_gaps"],
            "processes_total": run.process_inventory["total_processes"],
            "processes_verdict": run.process_inventory["verdict"],
            "compliance_applicable": run.compliance_detection["total_applicable"],
            "compliance_verdict": run.compliance_detection["verdict"],
            "maturity_overall_level": run.maturity_scoring["overall"]["level"],
            "maturity_overall_label": run.maturity_scoring["overall"]["label"],
            "maturity_verdict": run.maturity_scoring["verdict"],
        }

        if confidential_notes:
            run.confidential_notes_encrypted = encrypt_credentials({"notes": confidential_notes})

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        run.status = "failed"
        run.summary = {"error": str(exc)}

    await session.commit()
    return _run_to_dict(run, include_confidential=bool(confidential_notes))


async def get_latest_diagnosis(
    session: AsyncSession, project_id: uuid.UUID, include_confidential: bool = False,
) -> Optional[dict]:
    r = await session.execute(
        select(DiagnosisRun).where(DiagnosisRun.project_id == project_id)
        .order_by(DiagnosisRun.created_at.desc()).limit(1)
    )
    run = r.scalar_one_or_none()
    return _run_to_dict(run, include_confidential) if run else None


async def list_diagnosis_runs(session: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    r = await session.execute(
        select(DiagnosisRun).where(DiagnosisRun.project_id == project_id)
        .order_by(DiagnosisRun.created_at.desc())
    )
    return [_run_to_summary(run) for run in r.scalars().all()]


def _run_to_dict(run: DiagnosisRun, include_confidential: bool = False) -> dict:
    result = {
        "id": run.id, "project_id": run.project_id, "status": run.status,
        "triggered_by": run.triggered_by,
        "stakeholder_analysis": run.stakeholder_analysis,
        "process_inventory": run.process_inventory,
        "compliance_detection": run.compliance_detection,
        "maturity_scoring": run.maturity_scoring,
        "summary": run.summary,
        "created_at": run.created_at, "completed_at": run.completed_at,
    }
    if include_confidential and run.confidential_notes_encrypted:
        try:
            result["confidential_notes"] = decrypt_credentials(run.confidential_notes_encrypted).get("notes")
        except Exception:
            result["confidential_notes"] = "[error al descifrar]"
    return result


def _run_to_summary(run: DiagnosisRun) -> dict:
    return {
        "id": run.id, "project_id": run.project_id, "status": run.status,
        "triggered_by": run.triggered_by, "summary": run.summary,
        "created_at": run.created_at, "completed_at": run.completed_at,
    }
