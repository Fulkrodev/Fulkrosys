"""Una sesion recien emitida no se rechaza por un desfase de reloj de segundos.

Medido el 2026-09-23: con la pila levantada, 1 de cada 50 entradas de admin
acababa en el login. La traza de Playwright lo mostro: la cookie viajaba, el
middleware la aceptaba y el backend respondia 401 "Invalid session token" a
``/auth/me``, porque el ``iat`` del token quedaba una fraccion de segundo en
el futuro respecto a la hora de verificar (el reloj habia retrocedido). PyJWT
rechaza un ``iat`` futuro sin tolerancia.
"""
from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from backend.app.auth import crypto


def _token(iat_offset: float) -> str:
    ahora = int(time.time() + iat_offset)
    return pyjwt.encode(
        {"sub": "u", "jti": "j", "typ": "session", "iat": ahora, "exp": ahora + 3600},
        crypto._PRIVATE_PEM, algorithm=crypto.JWT_ALGORITHM,
    )


def test_un_iat_unos_segundos_en_el_futuro_se_acepta():
    assert crypto.decode_token(_token(+3))["sub"] == "u"


def test_la_tolerancia_no_es_un_cheque_en_blanco():
    with pytest.raises(pyjwt.ImmatureSignatureError):
        crypto.decode_token(_token(+120))


def test_un_token_caducado_sigue_rechazandose():
    ahora = int(time.time())
    viejo = pyjwt.encode(
        {"sub": "u", "jti": "j", "typ": "session", "iat": ahora - 7200, "exp": ahora - 60},
        crypto._PRIVATE_PEM, algorithm=crypto.JWT_ALGORITHM,
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        crypto.decode_token(viejo)
