"""Motor 26 - Backup & Disaster Recovery models."""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, Integer, BigInteger, Boolean, Date
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class BackupJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_jobs"
    backup_type: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    location: Mapped[str | None] = mapped_column(String(500))
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    encryption_key_id: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)


class BackupRetentionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_retention_policies"
    backup_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    daily_keep: Mapped[int] = mapped_column(Integer, default=30)
    weekly_keep: Mapped[int] = mapped_column(Integer, default=12)
    monthly_keep: Mapped[int] = mapped_column(Integer, default=12)
    yearly_keep: Mapped[int] = mapped_column(Integer, default=3)


class BackupRestoreTest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_restore_tests"
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)
    backup_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("backup_jobs.id"))
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    rto_seconds: Mapped[int | None] = mapped_column(Integer)
    validation_report: Mapped[dict | None] = mapped_column(JSONB)
    sandbox_destroyed: Mapped[bool | None] = mapped_column(Boolean)


class DrDrill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dr_drills"
    drill_date: Mapped[date] = mapped_column(Date, nullable=False)
    initiated_by: Mapped[str | None] = mapped_column(String(255))
    rto_objective_seconds: Mapped[int | None] = mapped_column(Integer)
    rto_actual_seconds: Mapped[int | None] = mapped_column(Integer)
    rpo_objective_seconds: Mapped[int | None] = mapped_column(Integer)
    rpo_actual_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    report_path: Mapped[str | None] = mapped_column(String(500))
    issues_found: Mapped[dict | None] = mapped_column(JSONB)


class IntegrityVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integrity_verifications"
    verification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sample_size: Mapped[int | None] = mapped_column(Integer)
    discrepancies_found: Mapped[int | None] = mapped_column(Integer, default=0)
    report: Mapped[dict | None] = mapped_column(JSONB)
