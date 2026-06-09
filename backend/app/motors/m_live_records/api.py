"""API endpoints m_live_records · sub-lote 1.C.B fase 3b.

REST endpoints project-scoped (/projects/{project_id}/records/...). Auth:
require_marcos_or_client (Marcos owner gestiona admin + cliente gestiona via
portal cliente magic link). RLS enforced project-scoped via set_tenant_context
en middleware authenticate_request global dep (ADR-021).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_marcos_or_client
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m_live_records.constants import (
    COUNTS_PER_CATEGORY,
    REGISTER_TYPE_REQUIRED_CATEGORIES,
    CategoryEns,
    get_required_registers_for_category,
)
from backend.app.motors.m_live_records.schemas import (
    ENTRY_SCHEMAS,
    LiveRecordCreate,
    LiveRecordListResponse,
    LiveRecordRead,
    LiveRecordUpdate,
    LiveRecordsDashboardResponse,
)
from backend.app.motors.m_live_records.service import LiveRecordsService


router = APIRouter(
    prefix="/api/v1/projects/{project_id}/records",
    tags=["live_records"],
    dependencies=[Depends(require_marcos_or_client)],
)


async def _set_project_context(db: AsyncSession, project_id: uuid.UUID) -> None:
    """Set app.current_project_id for RLS within this request transaction."""
    await set_tenant_context(db, project_id=project_id)


def _to_read(record) -> LiveRecordRead:
    return LiveRecordRead.model_validate(record, from_attributes=True)


@router.get(
    "/categories/required",
    summary="Matriz registros requeridos per category (Anexo K · R28)",
)
async def get_required_registers_by_category(
    project_id: uuid.UUID,
    category: CategoryEns = Query(
        ...,
        description="BASICA | MEDIA | ALTA",
    ),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> dict:
    """Returns lista register_types required para categoría ENS especificada.

    Single source de matriz Anexo K v3.9 · consumido por frontend filter +
    admin reporting per category (cliente piloto MEDIA = 24 registros · ALTA
    full 26 · BASICA subset 17).

    Sostiene R28 (adaptación per category sistematizada) + R32 (matriz K
    centralizada · NO ad-hoc).
    """
    await _set_project_context(db, project_id)
    required = get_required_registers_for_category(category)
    return {
        "project_id": str(project_id),
        "category": category,
        "required_count": len(required),
        "expected_count": COUNTS_PER_CATEGORY[category],
        "required_register_types": required,
        "total_register_types": len(REGISTER_TYPE_REQUIRED_CATEGORIES),
    }


@router.get(
    "/dashboard",
    response_model=LiveRecordsDashboardResponse,
    summary="Dashboard 26 register_types con counts active/archived",
)
async def get_dashboard(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> LiveRecordsDashboardResponse:
    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    blocks, total_active = await svc.compute_dashboard(project_id=project_id)
    return LiveRecordsDashboardResponse(
        project_id=project_id,
        blocks=blocks,
        total_active=total_active,
    )


@router.get(
    "/{register_type}",
    response_model=LiveRecordListResponse,
    summary="List records by register_type (paginated)",
)
async def list_records(
    project_id: uuid.UUID,
    register_type: str,
    status_filter: str = Query("active", alias="status", pattern="^(active|archived|all)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> LiveRecordListResponse:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    effective_status = None if status_filter == "all" else status_filter
    rows, total = await svc.list_records(
        project_id=project_id,
        register_type=register_type,
        status=effective_status,
        limit=limit,
        offset=offset,
    )
    return LiveRecordListResponse(
        records=[_to_read(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{register_type}/{record_id}",
    response_model=LiveRecordRead,
    summary="Get single record by id",
)
async def get_record(
    project_id: uuid.UUID,
    register_type: str,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> LiveRecordRead:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    record = await svc.get_record(project_id=project_id, record_id=record_id)
    if record is None or record.register_type != register_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    return _to_read(record)


@router.post(
    "/{register_type}",
    response_model=LiveRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new record (validates entry_data shape)",
)
async def create_record(
    project_id: uuid.UUID,
    register_type: str,
    payload: LiveRecordCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> LiveRecordRead:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user has no id",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    try:
        record = await svc.create_record(
            project_id=project_id,
            register_type=register_type,
            entry_data=payload.entry_data,
            created_by=user_id,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    await db.commit()
    return _to_read(record)


@router.patch(
    "/{register_type}/{record_id}",
    response_model=LiveRecordRead,
    summary="Update record (partial entry_data + optional status)",
)
async def update_record(
    project_id: uuid.UUID,
    register_type: str,
    record_id: uuid.UUID,
    payload: LiveRecordUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> LiveRecordRead:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user has no id",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    try:
        record = await svc.update_record(
            project_id=project_id,
            record_id=record_id,
            updated_by=user_id,
            entry_data=payload.entry_data,
            status=payload.status,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    if record is None or record.register_type != register_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    await db.commit()
    return _to_read(record)


@router.delete(
    "/{register_type}/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft archive record (status='archived')",
)
async def archive_record(
    project_id: uuid.UUID,
    register_type: str,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> None:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user has no id",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    record = await svc.archive_record(
        project_id=project_id,
        record_id=record_id,
        updated_by=user_id,
    )
    if record is None or record.register_type != register_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )
    await db.commit()
    return None


@router.get(
    "/{register_type}/export/csv",
    summary="Export records as CSV (utf-8 BOM, includes archived)",
)
async def export_csv(
    project_id: uuid.UUID,
    register_type: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> StreamingResponse:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    data = await svc.export_csv(project_id=project_id, register_type=register_type)
    filename = f"{register_type}_{project_id}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{register_type}/export/xlsx",
    summary="Export records as XLSX (openpyxl)",
)
async def export_xlsx(
    project_id: uuid.UUID,
    register_type: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_marcos_or_client),
) -> StreamingResponse:
    if register_type not in ENTRY_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown register_type {register_type!r}",
        )

    await _set_project_context(db, project_id)
    svc = LiveRecordsService(db)
    data = await svc.export_xlsx(project_id=project_id, register_type=register_type)
    filename = f"{register_type}_{project_id}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
