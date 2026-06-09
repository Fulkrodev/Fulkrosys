"""Admin RoPA API — Article 30 GDPR (atom 9.bis.3).

Admin-only endpoints to inspect, update and export the FULKRO Record
of Processing Activities. Used by Marcos when:
- Onboarding a new sub-processor (PATCH)
- Producing the annual review evidence (XLSX export)
- Generating the AEPD audit deliverable
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db
from backend.app.motors.m_compliance.ropa_service import RoPAService


router = APIRouter(
    prefix="/admin/compliance/ropa",
    tags=["MB-9.bis atom 3 — RoPA admin"],
    dependencies=[Depends(require_owner)],
)


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    treatment_code: str
    treatment_name: str
    role: str
    purpose: str
    legal_basis: str
    data_categories: list[str]
    data_subjects_categories: list[str]
    recipients: list[str] | None
    transfers_outside_eu: bool
    transfer_safeguards: str | None
    retention_period: str
    security_measures: str
    processor_name: str | None
    is_sub_processor: bool
    dpa_signed: bool
    dpa_expires_at: datetime | None
    controller_dpo: str
    last_reviewed_at: datetime


class TreatmentPatchBody(BaseModel):
    treatment_name: str | None = None
    role: str | None = None
    purpose: str | None = None
    legal_basis: str | None = None
    data_categories: list[str] | None = None
    data_subjects_categories: list[str] | None = None
    recipients: list[str] | None = None
    transfers_outside_eu: bool | None = None
    transfer_safeguards: str | None = None
    retention_period: str | None = None
    security_measures: str | None = None
    processor_name: str | None = None
    is_sub_processor: bool | None = None
    dpa_signed: bool | None = None
    dpa_expires_at: datetime | None = None
    controller_dpo: str | None = None


@router.get("", response_model=list[TreatmentOut])
async def list_treatments(db: AsyncSession = Depends(get_db)) -> list[TreatmentOut]:
    rows = await RoPAService(db).list_treatments()
    return [TreatmentOut.model_validate(r) for r in rows]


@router.get("/{code}", response_model=TreatmentOut)
async def get_treatment(code: str, db: AsyncSession = Depends(get_db)) -> TreatmentOut:
    row = await RoPAService(db).get_treatment(code)
    if row is None:
        raise HTTPException(404, detail=f"Treatment {code} not found")
    return TreatmentOut.model_validate(row)


@router.patch("/{code}", response_model=TreatmentOut)
async def patch_treatment(
    code: str,
    body: TreatmentPatchBody,
    db: AsyncSession = Depends(get_db),
) -> TreatmentOut:
    svc = RoPAService(db)
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, detail="No fields to update")
    try:
        row = await svc.update_treatment(code, fields)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
    await db.commit()
    return TreatmentOut.model_validate(row)


@router.post("/{code}/review", response_model=TreatmentOut)
async def mark_treatment_reviewed(
    code: str, db: AsyncSession = Depends(get_db)
) -> TreatmentOut:
    try:
        row = await RoPAService(db).mark_reviewed(code)
    except KeyError as e:
        raise HTTPException(404, detail=str(e))
    await db.commit()
    return TreatmentOut.model_validate(row)


@router.get(".xlsx")
async def export_aepd_excel(db: AsyncSession = Depends(get_db)) -> Response:
    """Return the full RoPA as an AEPD-compatible Excel file."""
    buf = await RoPAService(db).export_aepd_excel()
    headers = {
        "Content-Disposition": 'attachment; filename="RoPA_FULKRO.xlsx"',
    }
    return Response(
        content=buf.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers=headers,
    )
