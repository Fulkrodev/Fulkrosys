"""Motor 26 — Backup Engine schemas (Pydantic).

Patron consistente con M12 Magic Link y M3 DdA Engine.
Models use ConfigDict(from_attributes=True) for ORM mapping.
"""
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === BackupJob ===

class BackupJobCreate(BaseModel):
    backup_type: str = Field(
        ...,
        description="postgres_full | postgres_incremental | minio_snapshot | config_snapshot | audit_log_export",
    )
    location: str | None = None
    encryption_key_id: str | None = None


class BackupJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    backup_type: str
    started_at: datetime | None
    completed_at: datetime | None
    status: str
    size_bytes: int | None
    location: str | None
    hash_sha256: str | None
    encryption_key_id: str | None
    error_message: str | None
    created_at: datetime


# === RetentionPolicy ===

class RetentionPolicyUpsert(BaseModel):
    backup_type: str
    daily_keep: int = Field(30, ge=0)
    weekly_keep: int = Field(12, ge=0)
    monthly_keep: int = Field(12, ge=0)
    yearly_keep: int = Field(3, ge=0)


class RetentionPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    backup_type: str
    daily_keep: int
    weekly_keep: int
    monthly_keep: int
    yearly_keep: int
    created_at: datetime


# === RestoreTest ===

class RestoreTestCreate(BaseModel):
    test_type: str = Field(..., description="partial_db | full_db | minio | archived_project")
    backup_job_id: UUID | None = None


class RestoreTestComplete(BaseModel):
    rto_seconds: int
    validation_report: dict[str, Any]
    sandbox_destroyed: bool = True


class RestoreTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_type: str
    backup_job_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    status: str
    rto_seconds: int | None
    validation_report: dict[str, Any] | None
    sandbox_destroyed: bool | None
    created_at: datetime


# === DrDrill ===

class DrDrillCreate(BaseModel):
    rto_objective_seconds: int = Field(14400, description="RTO objetivo en segundos (default 4h)")
    rpo_objective_seconds: int = Field(86400, description="RPO objetivo en segundos (default 24h)")


class DrDrillComplete(BaseModel):
    rto_actual_seconds: int
    rpo_actual_seconds: int
    report_path: str
    issues_found: dict[str, Any] | None = None


class DrDrillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drill_date: date
    initiated_by: str | None
    rto_objective_seconds: int | None
    rpo_objective_seconds: int | None
    rto_actual_seconds: int | None
    rpo_actual_seconds: int | None
    status: str
    report_path: str | None
    issues_found: dict[str, Any] | None
    created_at: datetime


# === IntegrityVerification ===

class IntegrityCheckCreate(BaseModel):
    verification_type: str = Field(..., description="hash_sampling | restore_validation | bit_rot")
    sample_size: int = Field(100, ge=1)


class IntegrityCheckComplete(BaseModel):
    discrepancies_found: int
    report: dict[str, Any]


class IntegrityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    verification_type: str
    verified_at: datetime | None
    status: str
    sample_size: int | None
    discrepancies_found: int | None
    report: dict[str, Any] | None
    created_at: datetime


# === Dashboard Status ===

class BackupHealthDetail(BaseModel):
    completed_at: str | None
    status: str
    size_bytes: int | None = None
    age_hours: float | None = None
    rto_seconds: int | None = None


class BackupStatusOut(BaseModel):
    health: str  # green, yellow, red
    last_full_backup: BackupHealthDetail
    last_incremental_backup: BackupHealthDetail
    last_restore_test: BackupHealthDetail
