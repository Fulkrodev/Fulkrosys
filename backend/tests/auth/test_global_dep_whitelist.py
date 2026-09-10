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
            "Endpoint /onboarding/consume bloqueado por global_dep - regresion H51"
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


@pytest.mark.asyncio
async def test_bloque_g_metrics_publico_sin_auth(async_client: AsyncClient) -> None:
    """BLOQUE G: GET /metrics debe servirse sin cookie de sesion.

    Criterio ADR-030 numero 3 (operacional estandar: monitoring/probes). Un
    raspador de metricas no tiene ni cookie ni segundo factor; sacarlo de la
    autenticacion de SESION no lo hace publico, porque tiene su propia puerta en
    main.py: en produccion exige `Authorization: Bearer $FULKRO_METRICS_TOKEN` y
    devuelve 503 si esa variable no esta configurada.

    Medido antes de este test: la ruta devolvia 401 "Authentication required"
    porque no estaba en la lista, y por tanto NINGUN raspador podia leerla.
    """
    response = await async_client.get("/metrics")
    assert response.status_code == 200, (
        f"/metrics bloqueado por global_dep: "
        f"{response.status_code} {response.text[:200]}"
    )
    assert response.headers["content-type"].startswith("text/plain"), (
        f"formato de exposicion incorrecto: {response.headers.get('content-type')}"
    )
    cuerpo = response.text
    # No basta con que responda: tiene que EMITIR. Un 200 con el cuerpo vacio
    # seria la version metrica de una pagina que carga y no funciona.
    assert "# TYPE fulkro_llm_llamadas_total counter" in cuerpo, (
        "no se emiten las metricas del registro de llamadas al modelo"
    )
    for estado in ("success", "estimado", "mock", "error"):
        assert f'fulkro_llm_llamadas_total{{estado="{estado}"}}' in cuerpo, (
            f"falta la serie del estado '{estado}' · los cuatro se emiten "
            f"siempre, aunque valgan cero, porque una serie que aparece y "
            f"desaparece rompe las alertas de quien la consume"
        )


@pytest.mark.asyncio
async def test_bloque_g_cabecera_de_correlacion(async_client: AsyncClient) -> None:
    """BLOQUE G: toda respuesta lleva X-Request-ID, y respeta el entrante.

    Reutilizar el identificador que llega de fuera es lo que evita que la traza
    se parta en la frontera del sistema, que es donde mas falta hace.
    """
    r1 = await async_client.get("/api/v1/health")
    assert r1.headers.get("X-Request-ID"), "la respuesta no lleva X-Request-ID"

    r2 = await async_client.get(
        "/api/v1/health", headers={"X-Request-ID": "el-mio-1234"}
    )
    assert r2.headers.get("X-Request-ID") == "el-mio-1234", (
        "no se reutiliza el identificador entrante"
    )

    # Viene de fuera: es entrada del usuario y hay que sanearla. Sin esto se
    # pueden inyectar saltos de linea en los registros y fabricar entradas
    # falsas.
    r3 = await async_client.get(
        "/api/v1/health", headers={"X-Request-ID": "malo\r\ninyectado <script>"}
    )
    devuelto = r3.headers.get("X-Request-ID", "")
    assert "\n" not in devuelto and "<" not in devuelto, (
        f"identificador sin sanear: {devuelto!r}"
    )


@pytest.mark.asyncio
async def test_bloque_i_dpa_template_publico_sin_auth(async_client: AsyncClient) -> None:
    """BLOQUE I6: GET /legal/dpa-template/download debe servirse sin sesion.

    Criterio ADR-030 numero 4 (publico por diseno, verificable por un tercero
    sin acceso al sistema), el mismo que ya exime a `/legal/compliance/status`
    y a `/legal/sub-processor-notifications/subscribe`.

    El endpoint SE DECLARA publico en su propio docstring («dpa_public_router
    (no auth)») y aun asi devolvia 401: la dependencia global lo paraba antes
    de llegar al handler. Nadie lo habia notado porque a la pagina
    /dpa-template no llegaba nadie — era una de las siete paginas legales sin
    un solo enlace entrante en todo el codigo. Al anadir esos enlaces al pie
    global, el recorrido automatico del bloque E lo encontro a la primera.

    Que sea publico es lo correcto: el contrato de encargo del tratamiento
    (art. 28 RGPD) es lo que un posible cliente quiere leer ANTES de contratar.
    Y no expone dato de nadie: devuelve la plantilla con los datos de FULKRO
    como responsable, huecos para el cliente, y los sub-encargados que ya estan
    publicados en /sub-processors.

    Este test existe para que el 401 no vuelva en silencio: si alguien saca la
    entrada de la lista blanca, la pagina legal sigue cargando con HTTP 200 y
    solo se rompe el boton de descarga. Es justo el tipo de fallo que no avisa.
    """
    response = await async_client.get("/api/v1/legal/dpa-template/download")
    assert response.status_code == 200, (
        f"BLOQUE I6 regresion - /legal/dpa-template/download bloqueado: "
        f"{response.status_code} {response.text[:200]}"
    )
    assert response.headers.get("content-type", "").startswith(
        "application/vnd.openxmlformats-officedocument"
    ), f"No devuelve un DOCX: {response.headers.get('content-type')}"
    # Un DOCX es un ZIP: los dos primeros bytes son 'PK'. Comprobarlo evita que
    # el test pase con un cuerpo vacio o con una pagina de error servida con 200.
    assert response.content[:2] == b"PK", (
        f"El cuerpo no es un DOCX (primeros bytes: {response.content[:8]!r})"
    )
