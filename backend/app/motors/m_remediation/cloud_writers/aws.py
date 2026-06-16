"""Writer de remediación AWS (boto3) · m_remediation (ADR-055).

Implementa las acciones AWS del catálogo contra la API REAL vía AssumeRole
(mismo modelo de credenciales que el conector M16 · OPS-026 DRY). Para escritura,
el rol asumido debe tener permisos de escritura (los concede el cliente en su IAM).

Cada acción declara read_state/apply/rollback. boto3 es síncrono → se envuelve en
asyncio.to_thread. read_state devuelve la clave `desired_assertion` (bool) que el
motor usa para idempotencia y verificación.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Política de contraseñas "fuerte" canónica (op.acc.5/6 · CCN-STIC).
_STRONG_PWD = {
    "MinimumPasswordLength": 14,
    "RequireSymbols": True,
    "RequireNumbers": True,
    "RequireUppercaseCharacters": True,
    "RequireLowercaseCharacters": True,
    "AllowUsersToChangePassword": True,
    "MaxPasswordAge": 90,
    "PasswordReusePrevention": 24,
}


class AwsRemediationWriter:
    """Writer AWS · provider='aws'."""

    provider = "aws"

    def __init__(self, credentials: dict) -> None:
        self.creds = credentials
        self.region = credentials.get("region", "eu-west-1")

    # ── sesión (AssumeRole · espejo del conector) ─────────────────────────

    def _session(self):
        import boto3

        sts = boto3.client("sts", region_name=self.region)
        params: dict[str, Any] = {
            "RoleArn": self.creds["role_arn"],
            "RoleSessionName": "fulkro-remediation",
            "DurationSeconds": 900,
        }
        if self.creds.get("external_id"):
            params["ExternalId"] = self.creds["external_id"]
        c = sts.assume_role(**params)["Credentials"]
        return boto3.Session(
            aws_access_key_id=c["AccessKeyId"],
            aws_secret_access_key=c["SecretAccessKey"],
            aws_session_token=c["SessionToken"],
            region_name=self.region,
        )

    # ── interfaz async (envuelve dispatch síncrono) ──────────────────────

    async def read_state(self, action_type, target_ref, params):
        return await asyncio.to_thread(self._read, action_type, target_ref, params or {})

    async def apply(self, action_type, target_ref, params):
        return await asyncio.to_thread(self._apply, action_type, target_ref, params or {})

    async def rollback(self, action_type, target_ref, state_before):
        return await asyncio.to_thread(
            self._rollback, action_type, target_ref, state_before or {},
        )

    # ── dispatch ──────────────────────────────────────────────────────────

    def _dispatch(self, action_type: str) -> dict[str, Callable]:
        table = {
            "enable_bucket_encryption": {
                "read": self._read_encryption,
                "apply": self._apply_encryption,
                "rollback": self._rollback_encryption,
            },
            "block_public_access": {
                "read": self._read_public_block,
                "apply": self._apply_public_block,
                "rollback": self._rollback_public_block,
            },
            "enable_bucket_versioning": {
                "read": self._read_versioning,
                "apply": self._apply_versioning,
                "rollback": self._rollback_versioning,
            },
            "enforce_password_policy": {
                "read": self._read_pwd_policy,
                "apply": self._apply_pwd_policy,
                "rollback": self._rollback_pwd_policy,
            },
            "enable_audit_logging": {
                "read": self._read_cloudtrail,
                "apply": self._apply_cloudtrail,
                "rollback": self._rollback_cloudtrail,
            },
            "rotate_access_key": {
                "read": self._read_access_key,
                "apply": self._apply_rotate_key,
                "rollback": self._rollback_rotate_key,
            },
        }
        if action_type not in table:
            raise ValueError(f"Acción AWS no soportada por el writer: {action_type}")
        return table[action_type]

    def _read(self, action_type, target_ref, params):
        return self._dispatch(action_type)["read"](self._session(), target_ref, params)

    def _apply(self, action_type, target_ref, params):
        return self._dispatch(action_type)["apply"](self._session(), target_ref, params)

    def _rollback(self, action_type, target_ref, state_before):
        return self._dispatch(action_type)["rollback"](
            self._session(), target_ref, state_before,
        )

    # ── S3 · cifrado en reposo ────────────────────────────────────────────

    def _read_encryption(self, sess, bucket, _params) -> dict:
        s3 = sess.client("s3")
        try:
            enc = s3.get_bucket_encryption(Bucket=bucket)
            rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            return {"encryption_enabled": len(rules) > 0, "rules": rules}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if "NotFound" in code or code == "ServerSideEncryptionConfigurationNotFoundError":
                return {"encryption_enabled": False, "rules": []}
            raise

    def _apply_encryption(self, sess, bucket, _params) -> dict:
        s3 = sess.client("s3")
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}},
                ],
            },
        )
        return {"applied": "AES256"}

    def _rollback_encryption(self, sess, bucket, state_before) -> dict:
        s3 = sess.client("s3")
        rules = state_before.get("rules") or []
        if rules:
            s3.put_bucket_encryption(
                Bucket=bucket,
                ServerSideEncryptionConfiguration={"Rules": rules},
            )
        else:
            s3.delete_bucket_encryption(Bucket=bucket)
        return {"restored": bool(rules)}

    # ── S3 · bloqueo de acceso público ────────────────────────────────────

    _ALL_BLOCK = {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }

    def _read_public_block(self, sess, bucket, _params) -> dict:
        s3 = sess.client("s3")
        try:
            cfg = s3.get_public_access_block(Bucket=bucket)
            conf = cfg.get("PublicAccessBlockConfiguration", {})
            blocked = all(conf.get(k) for k in self._ALL_BLOCK)
            return {"public_access_blocked": blocked, "config": conf}
        except ClientError as exc:
            if "NoSuch" in exc.response.get("Error", {}).get("Code", ""):
                return {"public_access_blocked": False, "config": {}}
            raise

    def _apply_public_block(self, sess, bucket, _params) -> dict:
        sess.client("s3").put_public_access_block(
            Bucket=bucket, PublicAccessBlockConfiguration=dict(self._ALL_BLOCK),
        )
        return {"applied": True}

    def _rollback_public_block(self, sess, bucket, state_before) -> dict:
        s3 = sess.client("s3")
        conf = state_before.get("config") or {}
        if conf:
            s3.put_public_access_block(
                Bucket=bucket, PublicAccessBlockConfiguration=conf,
            )
        else:
            s3.delete_public_access_block(Bucket=bucket)
        return {"restored": bool(conf)}

    # ── S3 · versionado ────────────────────────────────────────────────────

    def _read_versioning(self, sess, bucket, _params) -> dict:
        v = sess.client("s3").get_bucket_versioning(Bucket=bucket)
        return {"versioning_enabled": v.get("Status") == "Enabled", "status": v.get("Status")}

    def _apply_versioning(self, sess, bucket, _params) -> dict:
        sess.client("s3").put_bucket_versioning(
            Bucket=bucket, VersioningConfiguration={"Status": "Enabled"},
        )
        return {"applied": "Enabled"}

    def _rollback_versioning(self, sess, bucket, state_before) -> dict:
        # No se puede "desversionar"; lo más cercano seguro es Suspended.
        sess.client("s3").put_bucket_versioning(
            Bucket=bucket, VersioningConfiguration={"Status": "Suspended"},
        )
        return {"restored": "Suspended"}

    # ── IAM · política de contraseñas ──────────────────────────────────────

    def _read_pwd_policy(self, sess, _target, _params) -> dict:
        iam = sess.client("iam")
        try:
            p = iam.get_account_password_policy().get("PasswordPolicy", {})
            strong = (
                p.get("MinimumPasswordLength", 0) >= 14
                and p.get("RequireSymbols")
                and p.get("RequireNumbers")
                and p.get("RequireUppercaseCharacters")
                and p.get("RequireLowercaseCharacters")
            )
            return {"password_policy_strong": bool(strong), "policy": p}
        except ClientError as exc:
            if "NoSuch" in exc.response.get("Error", {}).get("Code", ""):
                return {"password_policy_strong": False, "policy": None}
            raise

    def _apply_pwd_policy(self, sess, _target, _params) -> dict:
        sess.client("iam").update_account_password_policy(**_STRONG_PWD)
        return {"applied": True}

    def _rollback_pwd_policy(self, sess, _target, state_before) -> dict:
        iam = sess.client("iam")
        prev = state_before.get("policy")
        if prev:
            # Reaplica los campos editables previos (best-effort).
            editable = {
                k: prev[k]
                for k in _STRONG_PWD
                if k in prev
            }
            if editable:
                iam.update_account_password_policy(**editable)
                return {"restored": True}
        iam.delete_account_password_policy()
        return {"restored": False}

    # ── CloudTrail · auditoría ──────────────────────────────────────────────

    def _read_cloudtrail(self, sess, _target, _params) -> dict:
        ct = sess.client("cloudtrail")
        trails = ct.describe_trails().get("trailList", [])
        return {"audit_log_enabled": len(trails) > 0, "trails": [t.get("Name") for t in trails]}

    def _apply_cloudtrail(self, sess, _target, params) -> dict:
        bucket = params.get("s3_bucket")
        if not bucket:
            raise ValueError("enable_audit_logging requiere params.s3_bucket")
        ct = sess.client("cloudtrail")
        name = params.get("trail_name", "fulkro-ens-trail")
        ct.create_trail(Name=name, S3BucketName=bucket, IsMultiRegionTrail=True)
        ct.start_logging(Name=name)
        return {"applied": name}

    def _rollback_cloudtrail(self, sess, _target, _state_before) -> dict:
        ct = sess.client("cloudtrail")
        # Borra el trail que se CREÓ en _apply (su nombre se persiste en el
        # snapshot como `applied`), no un literal hardcoded. Si _apply usó un
        # trail_name custom, el rollback borra ese mismo trail (no el equivocado).
        name = (_state_before or {}).get("applied") or "fulkro-ens-trail"
        ct.delete_trail(Name=name)
        return {"restored": True, "deleted_trail": name}

    # ── IAM · rotación de clave (GUARDED) ───────────────────────────────────

    def _read_access_key(self, sess, target, _params) -> dict:
        import datetime

        iam = sess.client("iam")
        keys = iam.list_access_keys(UserName=target).get("AccessKeyMetadata", [])
        now = datetime.datetime.now(datetime.timezone.utc)
        oldest_days = 0
        # FIX: computar la edad SOLO sobre claves Activas. list_access_keys
        # también devuelve las Inactive, y la desactivación NO cambia CreateDate.
        # Antes, tras rotar (crear nueva + desactivar la vieja), la vieja seguía
        # contando → oldest_days>90 → key_age_ok=False → verify fallaba →
        # _rollback REACTIVABA la clave caducada (op.acc.5 nunca se cerraba).
        for k in keys:
            if k.get("Status") != "Active":
                continue
            created = k.get("CreateDate")
            if created is not None:
                age = (now - created).days
                oldest_days = max(oldest_days, age)
        return {
            "key_age_ok": oldest_days <= 90,
            "oldest_days": oldest_days,
            "keys": [k.get("AccessKeyId") for k in keys],
        }

    def _apply_rotate_key(self, sess, target, params) -> dict:
        iam = sess.client("iam")
        old_key_id = params.get("old_key_id")
        new_key = iam.create_access_key(UserName=target)["AccessKey"]
        if old_key_id:
            iam.update_access_key(
                UserName=target, AccessKeyId=old_key_id, Status="Inactive",
            )
        return {"new_key_id": new_key["AccessKeyId"], "deactivated_old": bool(old_key_id)}

    def _rollback_rotate_key(self, sess, target, state_before) -> dict:
        # Reactivar la clave previa es lo más seguro (no borramos la nueva aquí).
        iam = sess.client("iam")
        keys = state_before.get("keys") or []
        for k in keys:
            try:
                iam.update_access_key(UserName=target, AccessKeyId=k, Status="Active")
            except ClientError:
                pass
        return {"reactivated": keys}
