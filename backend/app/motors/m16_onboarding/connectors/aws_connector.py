"""AWS connector via cross-account AssumeRole + boto3."""
from __future__ import annotations

import asyncio
import logging

from .base import BaseConnector, ConnectorProvider, DiscoveredAssetDTO, DiscoveredIdentityDTO
from .registry import register_connector

logger = logging.getLogger(__name__)


class AWSConnector(BaseConnector):
    """Connector using boto3 (sync calls wrapped in asyncio.to_thread)."""

    provider = ConnectorProvider.AWS

    def __init__(self, credentials: dict):
        super().__init__(credentials)
        self.role_arn = credentials["role_arn"]
        self.external_id = credentials.get("external_id", "")
        self.region = credentials.get("region", "eu-west-1")
        self._session = None

    def _get_assumed_session(self):
        import boto3
        sts = boto3.client("sts", region_name=self.region)
        params = {"RoleArn": self.role_arn, "RoleSessionName": "fulkro-discovery", "DurationSeconds": 900}
        if self.external_id:
            params["ExternalId"] = self.external_id
        resp = sts.assume_role(**params)
        creds = resp["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=self.region,
        )

    async def validate_credentials(self) -> bool:
        try:
            await asyncio.to_thread(self._get_assumed_session)
            return True
        except Exception as exc:
            logger.warning(f"AWS validate failed: {exc}")
            return False

    async def discover_identities(self) -> list[DiscoveredIdentityDTO]:
        identities = []
        try:
            sess = await asyncio.to_thread(self._get_assumed_session)
            iam = sess.client("iam")
            users = await asyncio.to_thread(lambda: iam.list_users(MaxItems=200).get("Users", []))
            for u in users:
                identities.append(DiscoveredIdentityDTO(
                    external_id=u["UserId"],
                    email=None,
                    display_name=u["UserName"],
                    identity_type="user",
                    provider="aws",
                    raw_data={"UserName": u["UserName"], "CreateDate": str(u.get("CreateDate"))},
                ))
            roles = await asyncio.to_thread(lambda: iam.list_roles(MaxItems=100).get("Roles", []))
            for r in roles:
                identities.append(DiscoveredIdentityDTO(
                    external_id=r["RoleId"],
                    email=None,
                    display_name=r["RoleName"],
                    identity_type="service_account",
                    provider="aws",
                    raw_data={"RoleName": r["RoleName"]},
                ))
        except Exception as exc:
            logger.warning(f"AWS identities failed: {exc}")
        return identities

    async def discover_assets(self) -> list[DiscoveredAssetDTO]:
        assets = []
        try:
            sess = await asyncio.to_thread(self._get_assumed_session)
            # EC2
            ec2 = sess.client("ec2")
            instances = await asyncio.to_thread(lambda: ec2.describe_instances().get("Reservations", []))
            for res in instances:
                for inst in res.get("Instances", []):
                    name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
                    assets.append(DiscoveredAssetDTO(
                        external_id=inst["InstanceId"],
                        name=name_tag,
                        asset_type="server",
                        provider="aws",
                        tags=[inst.get("InstanceType", ""), inst.get("State", {}).get("Name", "")],
                        raw_data={"InstanceId": inst["InstanceId"], "InstanceType": inst.get("InstanceType")},
                    ))
            # S3
            s3 = sess.client("s3")
            buckets = await asyncio.to_thread(lambda: s3.list_buckets().get("Buckets", []))
            for b in buckets:
                assets.append(DiscoveredAssetDTO(
                    external_id=b["Name"],
                    name=b["Name"],
                    asset_type="storage",
                    provider="aws",
                    raw_data={"BucketName": b["Name"], "CreationDate": str(b.get("CreationDate"))},
                ))
        except Exception as exc:
            logger.warning(f"AWS assets failed: {exc}")
        return assets


register_connector(ConnectorProvider.AWS, AWSConnector)
