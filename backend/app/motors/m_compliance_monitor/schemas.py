"""Pydantic schemas for the FULKRO Self-Monitoring System admin API."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_name: str
    category: str
    frequency: str
    severity_threshold: str
    status: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    consecutive_failures: int
    description: str | None
    regulatory_basis: str | None
    last_result: dict[str, Any] | None


class CheckRunResult(BaseModel):
    check_name: str
    status: str
    severity: str | None
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    ran_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    check_id: UUID
    check_name: str
    severity: str
    status: str
    message: str
    details: dict[str, Any] | None
    triggered_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None
    auto_resolved: bool | None
    email_sent_at: datetime | None


class AlertResolveBody(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=2000)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_type: str
    period_start: datetime
    period_end: datetime
    summary: dict[str, Any]
    storage_mode: str
    storage_path: str | None
    signed_url: str | None
    signed_url_expires_at: datetime | None
    email_sent_to: str | None
    email_sent_at: datetime | None
    generated_at: datetime


class MonitorStatusOut(BaseModel):
    """Aggregate status snapshot for the admin dashboard."""

    overall: str
    green: int
    yellow: int
    red: int
    unknown: int
    total: int
    open_alerts: int
    last_run_at: datetime | None
    last_report_at: datetime | None


class TriggerCheckOut(BaseModel):
    check_name: str
    result: CheckRunResult
    alert_created: bool
    alert_id: UUID | None
