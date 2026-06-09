"""Motor 2 — MAGERIT v3 Risk Engine: Pydantic schemas."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# === ENUMS as Literal types (match CHECK constraints) ===

CalculationMode = Literal["qualitative", "quantitative", "hybrid"]
AnalysisStatus = Literal["draft", "in_progress", "completed", "approved"]
ProbabilityLevel = Literal["MB", "B", "M", "A", "MA"]
RiskLevel = Literal["MB", "B", "M", "A", "MA"]
Dimension = Literal["D", "I", "C", "A", "T"]
SafeguardEffectType = Literal["preventive", "palliative", "both"]
SafeguardStatus = Literal["planned", "partial", "deployed", "verified"]
TreatmentType = Literal["mitigar", "transferir", "aceptar", "eliminar"]
TreatmentStatus = Literal["pending", "in_progress", "completed"]


# === ANALYSIS ===

class AnalysisCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    calculation_mode: CalculationMode = "qualitative"
    description: str | None = None


class AnalysisOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    version: int
    status: AnalysisStatus
    calculation_mode: CalculationMode
    methodology_version: str
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === ASSETS ===

class AssetIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    asset_type_code: str = Field(..., min_length=1, max_length=20)
    description: str | None = None
    owner: str | None = None
    value_d: int = Field(0, ge=0, le=10)
    value_i: int = Field(0, ge=0, le=10)
    value_c: int = Field(0, ge=0, le=10)
    value_a: int = Field(0, ge=0, le=10)
    value_t: int = Field(0, ge=0, le=10)


class AssetOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    asset_type_code: str
    value_d: int | None
    value_i: int | None
    value_c: int | None
    value_a: int | None
    value_t: int | None
    accumulated_d: float | None
    accumulated_i: float | None
    accumulated_c: float | None
    accumulated_a: float | None
    accumulated_t: float | None

    model_config = ConfigDict(from_attributes=True)


class AssetInventoryRequest(BaseModel):
    assets: list[AssetIn] = Field(..., min_length=1)


# === DEPENDENCIES ===

class DependencyIn(BaseModel):
    superior_asset_id: uuid.UUID
    inferior_asset_id: uuid.UUID
    dependency_degree: float = Field(1.0, ge=0.0, le=1.0)
    reason: str | None = None


class DependencyGraphRequest(BaseModel):
    dependencies: list[DependencyIn] = Field(..., min_length=1)


# === THREATS ===

class ThreatAssessmentIn(BaseModel):
    asset_id: uuid.UUID
    threat_code: str = Field(..., min_length=1, max_length=10)
    probability: ProbabilityLevel
    degradation_d: int = Field(0, ge=0, le=100)
    degradation_i: int = Field(0, ge=0, le=100)
    degradation_c: int = Field(0, ge=0, le=100)
    degradation_a: int = Field(0, ge=0, le=100)
    degradation_t: int = Field(0, ge=0, le=100)


class ThreatAssessmentRequest(BaseModel):
    assessments: list[ThreatAssessmentIn] = Field(..., min_length=1)


# === SAFEGUARDS ===

class SafeguardDeploymentIn(BaseModel):
    safeguard_code: str = Field(..., min_length=1, max_length=20)
    efficacy: int = Field(0, ge=0, le=100)
    effect_type: SafeguardEffectType = "both"
    status: SafeguardStatus = "planned"
    responsible: str | None = None
    notes: str | None = None


class SafeguardDeploymentRequest(BaseModel):
    deployments: list[SafeguardDeploymentIn] = Field(..., min_length=1)


# === RISK CALCULATIONS ===

class RiskCalculationOut(BaseModel):
    asset_id: uuid.UUID
    threat_code: str
    dimension: Dimension
    impact_intrinsic: float | None
    risk_intrinsic_accumulated: float | None
    risk_intrinsic_repercuted: float | None
    impact_effective: float | None
    risk_effective: float | None
    risk_residual: float | None
    risk_level: str | None

    model_config = ConfigDict(from_attributes=True)


# === TREATMENT PLAN ===

class TreatmentPlanRequest(BaseModel):
    risk_tolerance_threshold: RiskLevel = "M"


class TreatmentActionOut(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    threat_code: str
    dimension: Dimension
    current_risk_level: str
    current_risk_value: float | None
    treatment: TreatmentType
    action_description: str | None
    proposed_safeguards: list[str] | None
    target_risk_level: str | None
    responsible: str | None
    deadline: date | None
    status: TreatmentStatus

    model_config = ConfigDict(from_attributes=True)


# === REPORT ===

class AnalysisReportOut(BaseModel):
    analysis: AnalysisOut
    assets: list[AssetOut]
    risk_calculations: list[RiskCalculationOut]
    treatment_actions: list[TreatmentActionOut]
    summary: dict


# === PILAR EXPORT ===

class PilarExportOut(BaseModel):
    content_type: str = "application/xml"
    xml: str


# === GENERIC RESPONSES ===

class OperationResult(BaseModel):
    analysis_id: uuid.UUID
    operation: str
    rows_affected: int
    message: str


# === SIGNATURE RE-INTEGRATION M2+M12 (M12-G2) ===

class RequestE028SignatureBody(BaseModel):
    recipient_email: EmailStr
    recipient_name: str | None = Field(None, max_length=120)
    recipient_role: str = Field("Responsable del Sistema", max_length=120)


class RequestE028SignatureResponse(BaseModel):
    link_id: uuid.UUID
    magic_link_url: str
    otp: str
    expires_at: datetime
    recipient_email: str
    previous_link_revoked: bool
    report_snapshot_hash: str
    frozen_at: datetime


class E028SignatureStatusResponse(BaseModel):
    analysis_id: uuid.UUID
    has_signature_request: bool
    is_frozen: bool
    link_id: uuid.UUID | None = None
    state: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    consumed_at: datetime | None = None
    recipient_email: str | None = None
