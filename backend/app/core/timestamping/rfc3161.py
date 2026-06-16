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


# =====================================================================
# Verificación COMPLETA RFC3161 · firma CMS + EKU + validez + cadena X.509
# =====================================================================

_HASH_BY_NAME = {
    "sha1": "SHA1", "sha224": "SHA224", "sha256": "SHA256",
    "sha384": "SHA384", "sha512": "SHA512",
}

_TIMESTAMPING_EKU_OID = "1.3.6.1.5.5.7.3.8"  # id-kp-timeStamping (RFC3161 §2.3)


def _bundled_freetsa_ca() -> Optional[bytes]:
    import pathlib
    p = pathlib.Path(__file__).with_name("freetsa_cacert.pem")
    try:
        return p.read_bytes()
    except OSError:  # pragma: no cover
        return None


def default_ca_bundle(tsa_url: Optional[str] = None) -> Optional[bytes]:
    """PEM del CA de confianza · env FULKRO_TSA_CA_BUNDLE > freeTSA bundled.

    Permite que la validación de cadena funcione out-of-the-box con freeTSA y
    que en prod se apunte a la CA de la TSA cualificada vía env.
    """
    path = os.environ.get("FULKRO_TSA_CA_BUNDLE")
    if path:
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError:  # pragma: no cover
            return None
    url = tsa_url or _config()["tsa_url"]
    if "freetsa.org" in (url or ""):
        return _bundled_freetsa_ca()
    return None


def _find_signer_cert_der(signed_data, signer_info) -> Optional[bytes]:
    certs = [c.chosen for c in signed_data["certificates"]]
    sid = signer_info["sid"]
    try:
        if sid.name == "issuer_and_serial_number":
            ias = sid.chosen
            serial = ias["serial_number"].native
            issuer = ias["issuer"]
            for c in certs:
                if c.serial_number == serial and c.issuer == issuer:
                    return c.dump()
        elif sid.name == "subject_key_identifier":
            want = sid.chosen.native
            for c in certs:
                if c.key_identifier == want:
                    return c.dump()
    except Exception:  # pragma: no cover
        pass
    # fallback robusto · la hoja = el primer cert no auto-firmado
    for c in certs:
        if c.subject != c.issuer:
            return c.dump()
    return certs[0].dump() if certs else None


def _pubkey_verify(pubkey, signature: bytes, data: bytes, hash_alg) -> None:
    """Verifica una firma · lanza si inválida (ECDSA / RSA-PKCS1v15 / Ed25519)."""
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding
    if isinstance(pubkey, ec.EllipticCurvePublicKey):
        pubkey.verify(signature, data, ec.ECDSA(hash_alg))
    elif isinstance(pubkey, ed25519.Ed25519PublicKey):
        pubkey.verify(signature, data)
    else:  # RSA
        pubkey.verify(signature, data, padding.PKCS1v15(), hash_alg)


def _cert_signed_by(cert, ca_cert) -> bool:
    try:
        _pubkey_verify(
            ca_cert.public_key(), cert.signature,
            cert.tbs_certificate_bytes, cert.signature_hash_algorithm,
        )
        return True
    except Exception:
        return False


def verify_timestamp_token(
    token_der: bytes,
    digest_hex: str,
    *,
    trusted_ca_pem: Optional[bytes] = None,
) -> tuple[bool, str]:
    """Verificación COMPLETA del sello RFC3161 · devuelve ``(ok, motivo)``.

    Comprueba, en orden:
      1. message imprint == digest del artefacto
      2. messageDigest signed-attr == hash del TSTInfo
      3. firma CMS del TSA sobre los signed_attrs (ECDSA/RSA) válida
      4. EKU id-kp-timeStamping en el cert firmante (RFC3161 §2.3)
      5. cert firmante vigente (no caducado) en gen_time
      6. (si hay CA de confianza) cadena: el cert firmante llega a la CA

    NUNCA lanza · cualquier fallo de parseo/firma → ``(False, motivo)``. Esto
    cierra el gap de la verificación previa, que solo comprobaba el imprint y
    por tanto aceptaba un token con firma forjada.
    """
    if not _ASN1_OK:
        return (False, "asn1crypto no disponible")
    try:
        import hashlib as _hl

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes

        # 1 · imprint (el sello cubre EXACTAMENTE este artefacto)
        if not verify_timestamp(token_der, digest_hex):
            return (False, "message imprint no coincide con el artefacto")

        ci = cms.ContentInfo.load(token_der)
        sd = ci["content"]
        si = sd["signer_infos"][0]

        signer_der = _find_signer_cert_der(sd, si)
        if signer_der is None:
            return (False, "token sin certificado firmante")
        signer = x509.load_der_x509_certificate(signer_der)

        digest_name = si["digest_algorithm"]["algorithm"].native
        hcls = getattr(hashes, _HASH_BY_NAME.get(digest_name, ""), None)
        if hcls is None:
            return (False, f"digest algo no soportado: {digest_name}")
        hash_alg = hcls()

        signed_attrs = si["signed_attrs"]
        if not signed_attrs or len(signed_attrs) == 0:
            return (False, "token sin signed_attrs")

        # 2 · messageDigest signed-attr == hash(TSTInfo)
        tst = _extract_tst_info(token_der)
        if tst is None:
            return (False, "TSTInfo ilegible")
        econtent = tst.dump()
        msg_digest_attr = None
        for attr in signed_attrs:
            if attr["type"].native == "message_digest":
                msg_digest_attr = attr["values"][0].native
                break
        if msg_digest_attr is None:
            return (False, "signed_attrs sin messageDigest")
        if msg_digest_attr != _hl.new(digest_name, econtent).digest():
            return (False, "messageDigest no coincide con el TSTInfo")

        # 3 · firma CMS sobre signed_attrs (re-tag [0] IMPLICIT 0xA0 → SET OF 0x31)
        attrs_der = signed_attrs.dump()
        attrs_der = b"\x31" + attrs_der[1:]
        try:
            _pubkey_verify(
                signer.public_key(), si["signature"].native, attrs_der, hash_alg,
            )
        except Exception:
            return (False, "firma CMS del TSA inválida")

        # 4 · EKU timeStamping
        try:
            eku = signer.extensions.get_extension_for_class(
                x509.ExtendedKeyUsage,
            ).value
            if _TIMESTAMPING_EKU_OID not in [o.dotted_string for o in eku]:
                return (False, "cert firmante sin EKU timeStamping")
        except x509.ExtensionNotFound:
            return (False, "cert firmante sin extendedKeyUsage")

        # 5 · validez en gen_time
        gen = _gen_time(token_der)
        if gen is not None:
            from datetime import timezone as _tz
            nb = getattr(signer, "not_valid_before_utc", None) or signer.not_valid_before
            na = getattr(signer, "not_valid_after_utc", None) or signer.not_valid_after
            g = gen if gen.tzinfo else gen.replace(tzinfo=_tz.utc)
            nbz = nb if nb.tzinfo else nb.replace(tzinfo=_tz.utc)
            naz = na if na.tzinfo else na.replace(tzinfo=_tz.utc)
            if not (nbz <= g <= naz):
                return (False, "cert firmante no vigente en gen_time")

        # 6 · cadena a CA de confianza (opcional pero recomendado para ENAC)
        if trusted_ca_pem:
            try:
                try:
                    roots = x509.load_pem_x509_certificates(trusted_ca_pem)
                except AttributeError:  # cryptography < 39
                    roots = [x509.load_pem_x509_certificate(trusted_ca_pem)]
            except Exception:
                return (False, "CA bundle ilegible")
            chained = any(
                ca.subject == signer.issuer and _cert_signed_by(signer, ca)
                for ca in roots
            )
            if not chained:
                # cadena 2+ niveles: el token puede traer un intermedio
                embedded = [
                    x509.load_der_x509_certificate(c.chosen.dump())
                    for c in sd["certificates"]
                ]
                inter = next(
                    (c for c in embedded
                     if c.subject == signer.issuer and _cert_signed_by(signer, c)),
                    None,
                )
                if inter is not None and any(
                    ca.subject == inter.issuer and _cert_signed_by(inter, ca)
                    for ca in roots
                ):
                    chained = True
            if not chained:
                return (False, "cadena del firmante no llega a la CA de confianza")

        return (True, "ok")
    except Exception as exc:  # degradación honesta · nunca rompe
        logger.warning("RFC3161 verify_timestamp_token error: %s", exc, exc_info=True)
        return (False, f"error de verificación: {exc}")
