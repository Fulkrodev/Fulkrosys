"""D1 · una llamada al modelo que falla NO puede quedar registrada como exito.

Que se demuestra aqui, y con que comando
----------------------------------------
    docker run --rm -v "$PWD:/app" -w /app --network fulkro-demo_default \
      -e PYTHONPATH=/app -e FULKRO_USE_LIVE_DB=1 \
      -e DATABASE_URL='postgresql+asyncpg://fulkro_app:...@postgres:5432/fulkro' \
      fulkro/backend:test \
      python -m pytest backend/tests/agents/test_agent_base_no_finge_exito.py -v

Los cuatro primeros tests NO necesitan base de datos (usan una sesion espia) y
por tanto corren en el job `test` de CI, que va con `-m "not requires_db"`.
El ultimo SI la necesita: comprueba sobre PostgreSQL real que el coste agregado
no se mueve y que los CHECK de la migracion rechazan una fila que mienta.

Comportamiento anterior (medido sobre backend/app/agents/base.py@c8ece1c):
`_call_llm` capturaba CUALQUIER excepcion y devolvia `_mock_response(...)`, que
fabricaba `tokens_output=50` fijo y `tokens_input` contando palabras;
`_log_interaction` grababa eso con `status="success"` y `cost_usd` calculado
sobre los tokens inventados. Un corte de red sumaba dinero al coste del mes.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from backend.app.agents.base import AgentBase, LLMCallFailed


# ───────────────────────────────────────────────────────────────────────────
# Andamiaje: una sesion espia que solo implementa lo que `_log_interaction` usa
# ───────────────────────────────────────────────────────────────────────────
class _SavepointFalso:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _SesionEspia:
    """Sustituto de AsyncSession. Guarda lo que se le anade, no habla con nadie."""

    def __init__(self) -> None:
        self.anadidas: list = []

    def begin_nested(self):
        return _SavepointFalso()

    def add(self, entry) -> None:
        self.anadidas.append(entry)

    async def flush(self) -> None:
        return None


class _AgenteDePrueba(AgentBase):
    AGENT_ID = 99
    AGENT_NAME = "Agente de prueba D1"
    SPECIFIC_PROMPT = "Prompt de prueba."


def _con_clave(monkeypatch, clave: str = "sk-ant-de-mentira") -> None:
    """Hace creer a `_call_llm` que hay clave, para que tome el camino de red."""
    import backend.app.agents.base as modulo_base

    falso = SimpleNamespace(
        anthropic_api_key=SimpleNamespace(get_secret_value=lambda: clave),
    )
    monkeypatch.setattr(modulo_base, "get_settings", lambda: falso)


def _proveedor_que_revienta(monkeypatch, excepcion: Exception) -> None:
    """Rompe el router del LLM en el punto exacto donde `_call_llm` lo pide."""
    import backend.app.core.ai.llm_router as router_mod

    def _explota():
        raise excepcion

    monkeypatch.setattr(router_mod, "get_default_llm_router", _explota)


# ───────────────────────────────────────────────────────────────────────────
# 1. El fallo del proveedor se propaga
# ───────────────────────────────────────────────────────────────────────────
async def test_fallo_del_proveedor_se_propaga(monkeypatch):
    _con_clave(monkeypatch)
    _proveedor_que_revienta(monkeypatch, ConnectionError("proveedor caido"))
    db = _SesionEspia()

    with pytest.raises(LLMCallFailed) as capturado:
        await _AgenteDePrueba().invoke(db, user_message="hola")

    # El mensaje tiene que nombrar la causa: sin esto el fallo sigue siendo mudo.
    assert "ConnectionError" in str(capturado.value)
    assert "proveedor caido" in str(capturado.value)


# ───────────────────────────────────────────────────────────────────────────
# 2. La fila del fallo NO queda como success (este es el defecto de D1)
# ───────────────────────────────────────────────────────────────────────────
async def test_la_fila_del_fallo_no_queda_como_success(monkeypatch):
    _con_clave(monkeypatch)
    _proveedor_que_revienta(monkeypatch, TimeoutError("se agoto el tiempo"))
    db = _SesionEspia()

    with pytest.raises(LLMCallFailed):
        await _AgenteDePrueba().invoke(db, user_message="hola")

    assert len(db.anadidas) == 1, "el fallo tiene que dejar rastro, no desaparecer"
    fila = db.anadidas[0]
    assert fila.status == "error"
    assert fila.status != "success"
    # Nada que sumar: ni coste ni tokens.
    assert fila.cost_usd is None
    assert fila.prompt_tokens is None
    assert fila.completion_tokens is None
    assert fila.total_tokens is None
    # Y el motivo queda escrito.
    assert "TimeoutError" in (fila.error_message or "")


# ───────────────────────────────────────────────────────────────────────────
# 3. Modo degradado sin clave: mock, coste 0, tokens NULL
# ───────────────────────────────────────────────────────────────────────────
async def test_sin_clave_la_fila_es_mock_con_coste_cero(monkeypatch):
    import backend.app.agents.base as modulo_base

    falso = SimpleNamespace(
        anthropic_api_key=SimpleNamespace(get_secret_value=lambda: ""),
    )
    monkeypatch.setattr(modulo_base, "get_settings", lambda: falso)
    db = _SesionEspia()

    resultado = await _AgenteDePrueba().invoke(db, user_message="hola")

    fila = db.anadidas[0]
    assert fila.status == "mock"
    assert fila.cost_usd == 0
    assert fila.prompt_tokens is None
    assert fila.completion_tokens is None
    assert fila.total_tokens is None
    # El diccionario que ve quien llama dice explicitamente que no esta medido.
    assert resultado["mock"] is True
    assert resultado["tokens_medidos"] is False
    # Y ya no trae la constante inventada de 50 tokens de salida.
    assert resultado["tokens_output"] == 0


# ───────────────────────────────────────────────────────────────────────────
# 4. La llamada que SI funciona se sigue registrando como success y con medida
# ───────────────────────────────────────────────────────────────────────────
async def test_llamada_correcta_sigue_siendo_success(monkeypatch):
    _con_clave(monkeypatch)
    import backend.app.core.ai.llm_router as router_mod

    respuesta = SimpleNamespace(
        content="respuesta de verdad",
        prompt_tokens=1234,
        completion_tokens=77,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        model="claude-sonnet-4-5",
    )
    router_falso = SimpleNamespace(complete=lambda **kw: respuesta)
    monkeypatch.setattr(router_mod, "get_default_llm_router", lambda: router_falso)
    db = _SesionEspia()

    resultado = await _AgenteDePrueba().invoke(db, user_message="hola")

    fila = db.anadidas[0]
    assert fila.status == "success"
    assert fila.prompt_tokens == 1234
    assert fila.completion_tokens == 77
    assert fila.total_tokens == 1234 + 77
    assert fila.cost_usd is not None and float(fila.cost_usd) > 0
    assert resultado["tokens_medidos"] is True
    assert resultado["mock"] is False


# ───────────────────────────────────────────────────────────────────────────
# 5. Contra PostgreSQL real: el coste agregado no se mueve, y la base rechaza
#    una fila que se declare mock con coste.
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.requires_db
async def test_coste_agregado_no_se_mueve_con_filas_mock_y_error(db):
    from sqlalchemy import text

    from backend.app.motors.m_observability.llm_observability_service import (
        get_cost_summary,
    )

    antes = await get_cost_summary(db, period="all")

    def _insertar(status: str, coste, tokens) -> str:
        return (
            "INSERT INTO llm_interaction_log "
            "(feature, model, prompt_hash, prompt_tokens, completion_tokens, "
            " total_tokens, cost_usd, latency_ms, status) VALUES "
            f"('prueba_d1', 'claude-sonnet-4-5', '{uuid.uuid4().hex}', "
            f"{tokens}, {tokens}, {tokens}, {coste}, 1, '{status}')"
        )

    await db.execute(text(_insertar("mock", "0", "NULL")))
    await db.execute(text(_insertar("error", "NULL", "NULL")))
    await db.flush()

    despues = await get_cost_summary(db, period="all")

    assert despues["cost_usd"] == antes["cost_usd"], (
        "dos filas que no gastaron nada han movido el coste agregado"
    )
    assert despues["total_tokens"] == antes["total_tokens"]
    assert despues["n_calls"] == antes["n_calls"], (
        "una fila mock/error no es una llamada contabilizable"
    )
    # Pero no desaparecen: se publican aparte.
    assert despues["n_calls_no_contabilizados"] == (
        antes["n_calls_no_contabilizados"] + 2
    )


@pytest.mark.requires_db
async def test_la_base_rechaza_una_fila_mock_con_coste(db):
    """El CHECK de la migracion es la ultima linea: no depende del codigo Python."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    sql = text(
        "INSERT INTO llm_interaction_log "
        "(feature, model, prompt_hash, prompt_tokens, completion_tokens, "
        " total_tokens, cost_usd, latency_ms, status) VALUES "
        "('prueba_d1', 'claude-sonnet-4-5', :h, NULL, NULL, NULL, 0.42, 1, 'mock')"
    )
    with pytest.raises(IntegrityError) as capturado:
        await db.execute(sql, {"h": uuid.uuid4().hex})
        await db.flush()
    assert "ck_llm_log_sin_coste_inventado" in str(capturado.value)


@pytest.mark.requires_db
async def test_la_base_rechaza_un_success_sin_tokens(db):
    """La contrapartida de permitir NULL: `success` sigue obligado a medir."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    sql = text(
        "INSERT INTO llm_interaction_log "
        "(feature, model, prompt_hash, prompt_tokens, completion_tokens, "
        " total_tokens, cost_usd, latency_ms, status) VALUES "
        "('prueba_d1', 'claude-sonnet-4-5', :h, NULL, NULL, NULL, 0, 1, 'success')"
    )
    with pytest.raises(IntegrityError) as capturado:
        await db.execute(sql, {"h": uuid.uuid4().hex})
        await db.flush()
    assert "ck_llm_log_tokens_medidos_no_nulos" in str(capturado.value)
