"""Tests global_dep whitelist - regresion H49/H51/H52/H53/H54.

Cubre todos los endpoints publicos que dependen exclusivamente del whitelist
(identificados en audit cross-motor 10.C):
- POST /api/v1/magic-links/consume         (H49)
- POST /api/v1/onboarding/consume          (H51)
- GET  /api/v1/magic-links/by-token/{tok}  (H52 - 10.C trigger)
- GET  /api/v1/evidence/public-key         (H53 - router refactor + whitelist)
- GET  /api/v1/onboarding/lms/courses      (H54 - audit cross-motor)
- GET  /api/v1/onboarding/lms/courses/{c}  (H54 cont.)

H53 fix arquitectonico: m07_evidence tenia dependencies=[require_marcos_or_client]
router-level + global_dep sin whitelist -> doble bloqueo. Refactor: endpoint
movido a public_router.py sin dependencies + entrada whitelist global_dep.

Patron: cualquier 401 = bloqueado por global_dep (whitelist faltante).
Status esperados: 200 / 404 / 403(business) / 410 / 422. NUNCA 401.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_h52_magic_link_by_token_publico_sin_auth(async_client: AsyncClient) -> None:
    """H52: GET /by-token debe ser publico (sign-flows pre-consume).

    Cliente abre /sign/{token} -> frontend llama /by-token ->
    debe retornar 200 (token valido) o 404 (no existe), NUNCA 401.
    """
    response = await async_client.get(
        "/api/v1/magic-links/by-token/test-token-no-existe-h52-regresion",
    )
    assert response.status_code != 401, (
        f"Endpoint /by-token bloqueado por global_dep - regresion H52 "
        f"(got {response.status_code})"
    )
    assert response.status_code in {200, 404, 410, 422}


@pytest.mark.asyncio
async def test_h49_magic_link_consume_publico_sin_auth(async_client: AsyncClient) -> None:
    """H49 regresion: POST /consume debe ser publico sin auth (no 401)."""
    response = await async_client.post(
        "/api/v1/magic-links/consume",
        json={"token": "test-no-existe-h49-regresion-token-largo", "otp": "000000"},
    )
    assert response.status_code != 401, (
        f"Endpoint /consume bloqueado por global_dep - regresion H49 "
        f"(got {response.status_code})"
    )


@pytest.mark.asyncio
async def test_h51_onboarding_consume_publico_sin_auth(async_client: AsyncClient) -> None:
    """H51 regresion: POST /onboarding/consume debe ser publico sin auth.

    Endpoint puede devolver 401 desde dentro (OnboardingAuthError business)
    pero con detail distinto a "Authentication required" (que viene de
    global_dep). Distingue bloqueo whitelist vs error business.
    """
    response = await async_client.post(
        "/api/v1/onboarding/consume",
        json={"token": "test-no-existe-h51-regresion-token-largo"},
    )
    # Whitelist OK si NO viene del global_dep: detail "Authentication required".
    if response.status_code == 401:
        detail = response.json().get("detail", "")
        assert detail != "Authentication required", (
            f"Endpoint /onboarding/consume bloqueado por global_dep - regresion H51"
        )
    else:
        # Business response (token invalido -> 401 business, 410, 422 etc.).
        assert response.status_code in {200, 401, 410, 422}


@pytest.mark.asyncio
async def test_h54_lms_courses_catalog_publico_sin_auth(async_client: AsyncClient) -> None:
    """H54: GET /onboarding/lms/courses catalogo publico sin respuestas."""
    response = await async_client.get("/api/v1/onboarding/lms/courses")
    assert response.status_code != 401, (
        f"Endpoint /lms/courses bloqueado por global_dep - regresion H54 "
        f"(got {response.status_code})"
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_h54_lms_courses_individual_publico_sin_auth(async_client: AsyncClient) -> None:
    """H54 cont.: GET /onboarding/lms/courses/{codigo} catalogo individual."""
    response = await async_client.get(
        "/api/v1/onboarding/lms/courses/curso-no-existe-h54",
    )
    assert response.status_code != 401, (
        f"Endpoint /lms/courses/{{codigo}} bloqueado por global_dep - regresion H54 "
        f"(got {response.status_code})"
    )
    assert response.status_code in {200, 404, 422}


@pytest.mark.asyncio
async def test_h53_evidence_public_key_publico_sin_auth(async_client: AsyncClient) -> None:
    """H53: GET /evidence/public-key debe ser publico sin auth.

    Bug pre-existente: router m07_evidence tenia dependencies=[require_marcos_or_client]
    a nivel router bloqueando /public-key aunque disenado publico para
    verificacion criptografica firmas Ed25519 externas.

    Fix arquitectonico (10.C): router separado public_router.py sin dependencies
    incluido aparte en main.py + entrada whitelist global_dep para
    `/api/v1/evidence/public-key`.
    """
    response = await async_client.get("/api/v1/evidence/public-key")
    assert response.status_code == 200, (
        f"H53 regresion - /evidence/public-key bloqueado: "
        f"{response.status_code} {response.text}"
    )
    data = response.json()
    assert "public_key_pem" in data, f"Schema invalido (sin public_key_pem): {data}"
    assert data.get("algorithm") == "Ed25519", (
        f"Schema invalido (algorithm != Ed25519): {data.get('algorithm')}"
    )
    assert "BEGIN PUBLIC KEY" in data["public_key_pem"], (
        f"PEM mal formado: {data['public_key_pem'][:50]}"
    )
