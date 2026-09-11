"""O2 · quien recibe un enlace para firmar recibia 401 antes de llegar al handler.

EL DEFECTO
    Los documentos del ciclo ENS se firman por magic-link: el acta E-012, el
    informe E-028 de MAGERIT, la DdA E-040 y las actas de reunion. El firmante
    NO tiene sesion -- por eso se le manda un enlace -- y la credencial es el
    token del enlace mas el OTP, que el propio endpoint valida con
    ``consume_magic_link`` (caducidad, revocacion, usos, OTP).

    Pero la dependencia global de autenticacion corre ANTES que el handler sobre
    todo lo que no este en la lista blanca, y estos dos prefijos no estaban:

        POST /api/v1/document-signing/sign   -> 401 {"detail":"Authentication required"}
        POST /api/v1/minutes-signing/approve -> 401 (identico)

    Es decir: la firma de los documentos del ciclo estaba cerrada entera. El
    hermano de al lado, ``/api/v1/contract-signing/``, SI estaba en la lista --
    se anyadio cuando se descubrio el mismo fallo en la firma del contrato
    comercial -- y el arreglo no se extendio a los documentos del ciclo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]


# ================================================================
# Por HTTP, sin sesion · el camino del firmante
# ================================================================


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_firmar_un_documento_no_pide_sesion(async_client):
    r = await async_client.post(
        "/api/v1/document-signing/sign",
        json={"token": "token-de-prueba-suficientemente-largo", "accepted": True},
    )
    assert r.status_code != 401, (
        "el firmante recibe 401 antes de que el endpoint mire su token: "
        f"{r.text[:120]}"
    )


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_aprobar_un_acta_de_reunion_no_pide_sesion(async_client):
    r = await async_client.post(
        "/api/v1/minutes-signing/approve",
        json={"token": "token-de-prueba-suficientemente-largo", "accepted": True},
    )
    assert r.status_code != 401, (
        f"el aprobador recibe 401 antes de mirar su token: {r.text[:120]}"
    )


@pytest.mark.real_auth
@pytest.mark.asyncio
async def test_un_token_invalido_sigue_sin_valer(async_client):
    """La lista blanca abre la puerta al handler, no al documento.

    Sin esta comprobacion el arreglo podria ser "quitar la autenticacion", que
    no es un arreglo sino un agujero: el token falso tiene que seguir siendo
    rechazado, ahora por quien sabe juzgarlo.
    """
    r = await async_client.post(
        "/api/v1/document-signing/sign",
        json={"token": "token-de-prueba-suficientemente-largo", "accepted": True},
    )
    assert r.status_code in (401, 403, 404, 422), r.status_code
    assert r.status_code != 200, "un token inventado no puede firmar nada"
    # 401 ya no puede venir de la dependencia global: si viene, trae el motivo
    # del endpoint, no "Authentication required".
    assert "Authentication required" not in r.text


# ================================================================
# Que no se repita con el proximo endpoint publico
# ================================================================


def _prefijos_en_lista_blanca() -> tuple[set[str], list[str]]:
    from backend.app.auth.global_dep import WHITELIST_EXACT, WHITELIST_PREFIX

    return set(WHITELIST_EXACT), list(WHITELIST_PREFIX)


def test_todo_router_publico_esta_en_la_lista_blanca():
    """Un modulo ``*_public_api.py`` declara un router publico por su nombre.

    Si su prefijo no esta en la lista blanca, la dependencia global lo tapa y
    el endpoint es inalcanzable para el unico publico al que sirve. Eso es lo
    que le paso a la firma de documentos y a la aprobacion de actas.
    """
    modulos = sorted((RAIZ / "backend" / "app").rglob("*public_api*.py"))
    assert len(modulos) >= 6, f"solo {len(modulos)} modulos publicos encontrados"

    exactos, prefijos = _prefijos_en_lista_blanca()

    # Se comprueba RUTA A RUTA y no por prefijo: `/api/v1/legal/` no esta como
    # prefijo, pero sus dos rutas publicas si estan una a una en WHITELIST_EXACT,
    # y eso basta para que el visitante anonimo llegue al handler. Un guard por
    # prefijo las daria por tapadas y seria un falso positivo.
    fuera = []
    for mod in modulos:
        texto = mod.read_text("utf-8")
        m = re.search(r"APIRouter\((?:\s|\n)*prefix=[\"']([^\"']+)", texto)
        prefijo = m.group(1) if m else ""
        rutas = [
            f"/api/v1{prefijo}{r}".rstrip("/") or f"/api/v1{prefijo}"
            for r in re.findall(
                r"@\w*router\.(?:get|post)\(\s*[\"']([^\"']+)", texto
            )
        ]
        assert rutas, f"{mod.relative_to(RAIZ)}: no se parseo ninguna ruta"
        for ruta in rutas:
            if ruta in exactos or any(ruta.startswith(p) for p in prefijos):
                continue
            fuera.append(f"{mod.relative_to(RAIZ)} -> {ruta}")

    assert not fuera, (
        "routers publicos que la dependencia global tapa (el publico al que "
        "sirven no tiene sesion, asi que reciben 401 antes del handler):\n  "
        + "\n  ".join(fuera)
    )


def test_los_dos_prefijos_del_ciclo_estan_declarados():
    """Anti-vacuidad del guard anterior, por nombre y no por barrido."""
    _, prefijos = _prefijos_en_lista_blanca()
    for p in ("/api/v1/document-signing/", "/api/v1/minutes-signing/"):
        assert p in prefijos, f"{p} no esta en la lista blanca"
