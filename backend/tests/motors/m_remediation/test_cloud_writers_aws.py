"""Tests end-to-end del writer AWS con moto (boto3 REAL contra backend simulado).

moto reproduce la semántica real de S3/IAM → esto prueba "de verdad" que el motor
aplica el cambio y lo verifica sobre el recurso (no un mock trivial). Cubre el ciclo
completo del motor (preflight idempotente → snapshot → apply → verify) con el writer
AWS real inyectado, y comprueba el ESTADO resultante en el recurso.
"""
from __future__ import annotations

import uuid

import boto3
import pytest
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
)
from backend.app.motors.m_remediation.cloud_writers.aws import AwsRemediationWriter
from backend.app.motors.m_remediation.service import RemediationService
from backend.tests.conftest import _admin_setup, setup_test_project

REGION = "eu-west-1"
ROLE = {"role_arn": "arn:aws:iam::123456789012:role/fulkro-remediation", "region": REGION}


@pytest.fixture(autouse=True)
def _global_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")


async def _aws_connector(db: AsyncSession, project_uuid: uuid.UUID) -> CloudConnector:
    async with _admin_setup(db):
        c = CloudConnector(
            project_id=project_uuid,
            provider=CloudConnectorProvider.AWS.value,
            status=CloudConnectorStatus.CONNECTED.value,
            remediation_enabled=True,
            auto_remediation_policy="full",
        )
        db.add(c)
        await db.flush()
    return c


@pytest.mark.asyncio
async def test_encryption_apply_verify_real_state(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _aws_connector(db, project_uuid)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket="demo-bucket",
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="enable_bucket_encryption",
            source_kind="cloud_gap", connector_id=connector.id,
            target_ref="demo-bucket",
        )
        job = await svc.execute_job(job.id, writer=AwsRemediationWriter(ROLE))
        assert job.status == "succeeded"
        # Estado REAL del bucket: cifrado aplicado de verdad.
        enc = s3.get_bucket_encryption(Bucket="demo-bucket")
        assert enc["ServerSideEncryptionConfiguration"]["Rules"]


@pytest.mark.asyncio
async def test_encryption_idempotent_skip(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _aws_connector(db, project_uuid)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket="demo-bucket",
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        # Ya cifrado de antemano.
        s3.put_bucket_encryption(
            Bucket="demo-bucket",
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}},
                ],
            },
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="enable_bucket_encryption",
            source_kind="cloud_gap", connector_id=connector.id,
            target_ref="demo-bucket",
        )
        job = await svc.execute_job(job.id, writer=AwsRemediationWriter(ROLE))
        assert job.status == "skipped_compliant"


@pytest.mark.asyncio
async def test_block_public_access_real_state(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _aws_connector(db, project_uuid)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket="open-bucket",
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="block_public_access",
            source_kind="cloud_gap", connector_id=connector.id,
            target_ref="open-bucket",
        )
        job = await svc.execute_job(job.id, writer=AwsRemediationWriter(ROLE))
        assert job.status == "succeeded"
        cfg = s3.get_public_access_block(Bucket="open-bucket")
        conf = cfg["PublicAccessBlockConfiguration"]
        assert conf["BlockPublicAcls"] and conf["RestrictPublicBuckets"]


@pytest.mark.asyncio
async def test_versioning_real_state(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _aws_connector(db, project_uuid)
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket="ver-bucket",
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="enable_bucket_versioning",
            source_kind="cloud_gap", connector_id=connector.id,
            target_ref="ver-bucket",
        )
        job = await svc.execute_job(job.id, writer=AwsRemediationWriter(ROLE))
        assert job.status == "succeeded"
        v = s3.get_bucket_versioning(Bucket="ver-bucket")
        assert v["Status"] == "Enabled"


@pytest.mark.asyncio
async def test_password_policy_real_state(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    connector = await _aws_connector(db, project_uuid)
    with mock_aws():
        svc = RemediationService(db)
        job = await svc.create_job(
            project_id=project_uuid, action_type="enforce_password_policy",
            source_kind="cloud_gap", connector_id=connector.id, target_ref="account",
        )
        job = await svc.execute_job(job.id, writer=AwsRemediationWriter(ROLE))
        assert job.status == "succeeded"
        iam = boto3.client("iam", region_name=REGION)
        pol = iam.get_account_password_policy()["PasswordPolicy"]
        assert pol["MinimumPasswordLength"] >= 14
