"""Cliente RFC 3161 (Trusted Timestamping) · feat/fulkro-100 Ola D.

Sella el hash SHA-256 de un artefacto contra una TSA (Time Stamping Authority)
RFC 3161 y verifica el token. Para ENS ALTA / valor probatorio: las evidencias y
firmas llevan un sello de tiempo de un tercero confiable.

Diseño:
- TSA CONFIGURABLE vía env ``FULKRO_TSA_URL`` (default freeTSA.org en dev · FNMT o
  TSA cualificada en prod).
- OPCIONAL + DEGRADACIÓN HONESTA: ``FULKRO_TIMESTAMP_ENABLED`` (default false). Si
  está apagado, o la lib ASN.1 no está, o la TSA no responde → status != 'success'
  pero NUNCA rompe el flujo que lo invoca (firma/evidencia siguen válidas).
- Import lazy de ``asn1crypto`` (pure-python) → ausencia degrada, no crashea.

    SHA-256(artefacto) → TimeStampReq (DER) → POST application/timestamp-query →
    TimeStampResp → TimeStampToken (DER, CMS SignedData firmado por la TSA).
"""
from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:  # import lazy · su ausencia degrada (no rompe el arranque de la app)
    from asn1crypto import algos, cms, tsp
    _ASN1_OK = True
except Exception:  # pragma: no cover · entorno mínimo sin asn1crypto
    algos = cms = tsp = None  # type: ignore
    _ASN1_OK = False


DEFAULT_TSA_URL = "https://freetsa.org/tsr"


@dataclass
class TimestampResult:
    """Resultado de una solicitud de sello de tiempo.

    status: 'success' | 'disabled' | 'unavailable' | 'failed'
      - success: token obtenido y verificado
      - disabled: FULKRO_TIMESTAMP_ENABLED=false (no se intentó · honesto)
      - unavailable: lib ASN.1 ausente
      - failed: TSA no respondió / respuesta inválida
    """

    status: str
    tsa_url: str
    token_der: Optional[bytes] = None
    gen_time: Optional[datetime] = None


def _config() -> dict:
    enabled = os.environ.get("FULKRO_TIMESTAMP_ENABLED", "false").lower() in (
        "1", "true", "yes", "on",
    )
    return {
        "enabled": enabled,
        "tsa_url": os.environ.get("FULKRO_TSA_URL", DEFAULT_TSA_URL),
        "timeout": float(os.environ.get("FULKRO_TSA_TIMEOUT", "10")),
    }


def build_timestamp_request(
    digest: bytes, *, nonce: Optional[int] = None,
) -> bytes:
    """Construye el TimeStampReq DER con el digest SHA-256 + nonce anti-replay."""
    if not _ASN1_OK:
        raise RuntimeError("asn1crypto no disponible")
    if nonce is None:
        nonce = int.from_bytes(secrets.token_bytes(8), "big")
    req = tsp.TimeStampReq({
        "version": "v1",
        "message_imprint": tsp.MessageImprint({
            "hash_algorithm": algos.DigestAlgorithm({"algorithm": "sha256"}),
            "hashed_message": digest,
        }),
        "nonce": nonce,
        "cert_req": True,
    })
    return req.dump()


def _extract_tst_info(token_der: bytes):
    """Devuelve el TSTInfo del TimeStampToken (CMS) · None si no se puede."""
    if not _ASN1_OK:
        return None
    try:
        ci = cms.ContentInfo.load(token_der)
        signed_data = ci["content"]
        encap = signed_data["encap_content_info"]
        content = encap["content"]
        # content es un ParsableOctetString cuyo .parsed es el TSTInfo.
        try:
            return content.parsed
        except Exception:
            return tsp.TSTInfo.load(content.native)
    except Exception:  # pragma: no cover · token malformado
        return None


def _gen_time(token_der: bytes) -> Optional[datetime]:
    tst = _extract_tst_info(token_der)
    if tst is None:
        return None
    try:
        return tst["gen_time"].native
    except Exception:  # pragma: no cover
        return None


def verify_timestamp(token_der: bytes, digest_hex: str) -> bool:
    """Verifica que el sello cubre EXACTAMENTE este hash (message imprint match).

    NO valida la cadena de certificación de la TSA (eso requiere el cert raíz de
    la TSA · fuera del MVP) · sí garantiza que el token corresponde al artefacto.
    """
    tst = _extract_tst_info(token_der)
    if tst is None:
        return False
    try:
        hashed = tst["message_imprint"]["hashed_message"].native
        return hashed == bytes.fromhex(digest_hex)
    except Exception:
        return False


async def request_timestamp(
    digest_hex: str,
    *,
    tsa_url: Optional[str] = None,
    timeout: Optional[float] = None,
) -> TimestampResult:
    """Pide un sello de tiempo para el hash SHA-256 (hex) dado.

    Best-effort · NUNCA lanza: devuelve un ``TimestampResult`` con el status.
    """
    cfg = _config()
    url = tsa_url or cfg["tsa_url"]

    if not cfg["enabled"]:
        return TimestampResult(status="disabled", tsa_url=url)
    if not _ASN1_OK:
        return TimestampResult(status="unavailable", tsa_url=url)

    try:
        digest = bytes.fromhex(digest_hex)
        req_der = build_timestamp_request(digest)

        import httpx

        async with httpx.AsyncClient(timeout=timeout or cfg["timeout"]) as client:
            resp = await client.post(
                url, content=req_der,
                headers={"Content-Type": "application/timestamp-query"},
            )
        resp.raise_for_status()

        ts_resp = tsp.TimeStampResp.load(resp.content)
        token = ts_resp["time_stamp_token"]
        token_der = token.dump()

        if not verify_timestamp(token_der, digest_hex):
            logger.warning("RFC3161: el sello no cubre el hash esperado")
            return TimestampResult(status="failed", tsa_url=url)

        return TimestampResult(
            status="success", tsa_url=url,
            token_der=token_der, gen_time=_gen_time(token_der),
        )
    except Exception:  # pragma: no cover · red / parsing · degradación honesta
        logger.warning("RFC3161 timestamp best-effort failed", exc_info=True)
        return TimestampResult(status="failed", tsa_url=url)
