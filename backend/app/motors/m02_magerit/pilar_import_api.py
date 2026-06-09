"""PILAR XML import API · SAN-C MB-11.4.

Endpoint
--------
POST /api/v1/magerit/analysis/{analysis_id}/import-xml
  multipart UploadFile XML · auto-detect formato (fulkro_native /
  pilar_compat) + persist + retorna ImportSummary.

NOTE: NO existe endpoint para importar PILAR ``.mgr`` (binario propietario
undocumented por CCN). Caller debe exportar XML legible desde PILAR
Desktop primero. Limitación documentada en docs/limitations/pilar_export.md.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.motors.m02_magerit.models import MageritAnalysis
from backend.app.motors.m02_magerit.pilar_importer import (
    PilarImportError,
    import_to_analysis,
    parse_xml,
)

router = APIRouter(prefix="/magerit", tags=["M02 - PILAR XML import (MB-11.4)"])


class ImportXmlResponse(BaseModel):
    detected_format: str
    assets_created: int
    threat_assessments_created: int
    safeguards_created: int


class ImportXmlPreviewResponse(BaseModel):
    detected_format: str
    assets_count: int
    threat_assessments_count: int
    safeguards_count: int
    sample_asset_codes: list[str]


_MAX_XML_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


async def _ensure_analysis_exists(
    db: AsyncSession, analysis_id: uuid.UUID,
) -> MageritAnalysis:
    analysis = await db.get(MageritAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(404, "Analysis not found")
    return analysis


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > _MAX_XML_SIZE_BYTES:
        raise HTTPException(
            413, f"XML supera tamaño máximo {_MAX_XML_SIZE_BYTES} bytes",
        )
    if not content:
        raise HTTPException(422, "File vacío")
    return content


@router.post(
    "/analysis/{analysis_id}/import-xml",
    response_model=ImportXmlResponse,
)
async def post_import_pilar_xml(
    analysis_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportXmlResponse:
    """Importa análisis MAGERIT desde XML (FULKRO native o PILAR-compatible)."""
    await _ensure_analysis_exists(db, analysis_id)
    content = await _read_upload(file)
    try:
        parsed = parse_xml(content)
    except PilarImportError as exc:
        raise HTTPException(422, str(exc)) from exc
    summary = await import_to_analysis(db, analysis_id, parsed)
    await db.commit()
    return ImportXmlResponse(
        detected_format=summary.detected_format,
        assets_created=summary.assets_created,
        threat_assessments_created=summary.threat_assessments_created,
        safeguards_created=summary.safeguards_created,
    )


@router.post(
    "/analysis/{analysis_id}/import-xml/preview",
    response_model=ImportXmlPreviewResponse,
)
async def post_preview_pilar_xml(
    analysis_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportXmlPreviewResponse:
    """Preview XML sin persistir (UI confirma antes de import)."""
    await _ensure_analysis_exists(db, analysis_id)
    content = await _read_upload(file)
    try:
        parsed = parse_xml(content)
    except PilarImportError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ImportXmlPreviewResponse(
        detected_format=parsed.detected_format,
        assets_count=len(parsed.assets),
        threat_assessments_count=len(parsed.threat_assessments),
        safeguards_count=len(parsed.safeguards),
        sample_asset_codes=[a.code for a in parsed.assets[:10]],
    )
