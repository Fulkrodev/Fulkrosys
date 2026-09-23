"""Guardia: los identificadores de modelo se declaran en UN sitio.

Antes del catalogo, ``grep -rhoE 'claude-(sonnet|opus|haiku)-[0-9][a-z0-9-]*'
backend/app --include="*.py" | sort | uniq -c`` devolvia 8 identificadores en 37
literales repartidos por 18 ficheros, y ``grep -rn "MODEL_CATALOG"`` no devolvia
nada. Estas cuatro pruebas blindan los cuatro sintomas de eso, y las cuatro
fallan sobre el commit padre:

1. Un literal de modelo que el catalogo no declara.
2. Un SEGUNDO mapa de alias, que es como volvio la duplicacion la vez anterior.
3. Un alias desconocido que pasa en silencio (``.get(alias, alias)``).
4. El camino del copiloto, que no resolvia ``opus-4`` ni ``opus-4.6``.

Ninguna necesita base de datos ni clave de API: leen el arbol con AST.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.core.ai.model_catalog import (
    CATALOGO,
    ModeloDesconocido,
    alias_validos,
    ids_validos,
    resolver,
    resolver_id,
    verificar_registry_de_agentes,
)


_RAIZ = Path(__file__).resolve().parents[4]
_APP = _RAIZ / "backend/app"
_CATALOGO_PY = _APP / "core/ai/model_catalog.py"

_ES_MODELO = re.compile(r"^claude-(sonnet|opus|haiku)-\d")

# Excepciones justificadas UNA A UNA. Cada entrada dice por que ese literal NO
# tiene que estar en el catalogo. Una excepcion sin motivo escrito no es una
# excepcion: es el defecto otra vez.
_EXCEPCIONES: dict[str, str] = {
    "backend/app/config.py": (
        "Los defaults de ANTHROPIC_DEFAULT_MODEL y ANTHROPIC_FALLBACK_MODEL. "
        "Son ids del catalogo, pero viven aqui como valor por omision de una "
        "variable de entorno que el operador puede cambiar sin tocar codigo; "
        "el test comprueba abajo que siguen siendo ids declarados."
    ),
    "backend/app/core/ai/llm_router.py": (
        "Mismos dos defaults que config.py, leidos con os.environ.get. Idem."
    ),
}


def _cadenas_de_modelo_en(ruta: Path) -> list[tuple[int, str]]:
    """Toda constante de cadena del fichero que parezca un id de modelo."""
    try:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    except SyntaxError as exc:  # pragma: no cover — un .py roto es otro fallo
        pytest.fail(f"{ruta} no parsea: {exc}")
    encontradas: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            if _ES_MODELO.match(nodo.value.strip()):
                encontradas.append((nodo.lineno, nodo.value.strip()))
    return encontradas


def _ficheros_de_la_app() -> list[Path]:
    return sorted(p for p in _APP.rglob("*.py") if "__pycache__" not in p.parts)


# ---------------------------------------------------------------------------
# 1 · todo identificador declarado
# ---------------------------------------------------------------------------

def test_todo_identificador_de_modelo_esta_en_el_catalogo():
    """Ningun literal de modelo fuera del catalogo, salvo excepcion escrita."""
    validos = ids_validos()
    intrusos: list[str] = []
    for ruta in _ficheros_de_la_app():
        if ruta == _CATALOGO_PY:
            continue
        relativa = ruta.relative_to(_RAIZ).as_posix()
        for linea, cadena in _cadenas_de_modelo_en(ruta):
            if cadena in validos:
                continue
            if relativa in _EXCEPCIONES:
                continue
            intrusos.append(f"{relativa}:{linea} -> {cadena!r}")
    assert not intrusos, (
        "hay identificadores de modelo que el catalogo no declara:\n  "
        + "\n  ".join(intrusos)
        + f"\nDeclaralos en {_CATALOGO_PY.relative_to(_RAIZ)} o justifica la "
        "excepcion una a una en _EXCEPCIONES."
    )


def test_los_defaults_exceptuados_siguen_siendo_ids_declarados():
    """Las dos excepciones son ids del catalogo, no cadenas libres."""
    validos = ids_validos()
    for relativa in _EXCEPCIONES:
        ruta = _RAIZ / relativa
        cadenas = {c for _, c in _cadenas_de_modelo_en(ruta)}
        assert cadenas, f"{relativa} ya no tiene literales: quita su excepcion"
        malas = sorted(c for c in cadenas if c not in validos)
        assert not malas, (
            f"{relativa} usa como default un modelo no declarado: {malas}"
        )


# ---------------------------------------------------------------------------
# 2 · un solo mapa de alias
# ---------------------------------------------------------------------------

def test_solo_hay_un_mapa_de_alias():
    """Falla si reaparece una segunda estructura alias -> id fuera del catalogo.

    Es la prueba que impide que vuelva la duplicacion, que es exactamente lo
    que paso antes: ``agents/base.py`` tenia el mapa bueno y las dos copias del
    copiloto se quedaron sin ``opus-4`` ni ``opus-4.6``. Se detecta por la
    forma, no por el nombre de la variable: cualquier diccionario literal cuya
    clave parezca un alias (``sonnet-4.5``) y cuyo valor sea un id de modelo.
    """
    alias_conocidos = set(alias_validos())
    duplicados: list[str] = []
    for ruta in _ficheros_de_la_app():
        if ruta == _CATALOGO_PY:
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Dict):
                continue
            for clave, valor in zip(nodo.keys, nodo.values):
                if not (isinstance(clave, ast.Constant) and isinstance(clave.value, str)):
                    continue
                if not (isinstance(valor, ast.Constant) and isinstance(valor.value, str)):
                    continue
                if clave.value in alias_conocidos and _ES_MODELO.match(valor.value):
                    duplicados.append(
                        f"{ruta.relative_to(_RAIZ).as_posix()}:{nodo.lineno} -> "
                        f"{clave.value!r}: {valor.value!r}"
                    )
    assert not duplicados, (
        "hay un segundo mapa alias -> id fuera del catalogo:\n  "
        + "\n  ".join(duplicados)
        + "\nEl catalogo es el unico sitio. Un mapa paralelo deriva en cuanto "
        "alguien anade un alias en un solo lado, y la resolucion no falla: la "
        "cadena viaja cruda al proveedor y vuelve como 404."
    )


# ---------------------------------------------------------------------------
# 3 · un alias desconocido aborta
# ---------------------------------------------------------------------------

def test_alias_desconocido_aborta():
    """``resolver`` LEVANTA. Antes era ``.get(alias, alias)``: pasaba en silencio."""
    with pytest.raises(ModeloDesconocido) as exc:
        resolver("gpt-5")
    mensaje = str(exc.value)
    assert "gpt-5" in mensaje, "el mensaje tiene que decir que alias se pidio"
    assert "sonnet-4.6" in mensaje, "y cuales son validos"
    assert "model_catalog.py" in mensaje, "y donde se declaran"


def test_el_arranque_aborta_con_un_registry_que_declara_un_alias_inventado(monkeypatch):
    """La deriva del registry se caza en el arranque, no en produccion."""
    from backend.app.agents import registry as modulo_registry

    falso = dict(modulo_registry.AGENT_REGISTRY)
    falso[99] = {"name": "Agente inventado", "status": "activo", "model": "opus-9.9"}
    monkeypatch.setattr(modulo_registry, "AGENT_REGISTRY", falso)

    with pytest.raises(ModeloDesconocido) as exc:
        verificar_registry_de_agentes()
    assert "opus-9.9" in str(exc.value)
    assert "A99" in str(exc.value)


def test_el_registry_de_verdad_declara_solo_modelos_del_catalogo():
    verificar_registry_de_agentes()


# ---------------------------------------------------------------------------
# 4 · el copiloto resuelve TODOS los alias del catalogo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("alias", alias_validos())
@pytest.mark.parametrize("cual", ["admin", "cliente"])
def test_el_copiloto_resuelve_todos_los_alias_del_catalogo(alias, cual, monkeypatch):
    """Sobre el padre falla en ``opus-4`` y ``opus-4.6``, que es la deriva (a).

    No mira el codigo: ejercita el camino REAL del copiloto y captura que
    ``model`` llega al router. El copiloto tomaba ``persona_service.model`` del
    catalogo de personas y lo traducia con un mapa propio de 4 entradas, copia
    incompleta del de ``agents/base.py``, que tiene 6. Con
    ``.get(alias, alias)``, los dos alias que faltaban no fallaban: salian de
    aqui SIN TRADUCIR y viajaban asi al proveedor.
    """
    import asyncio

    if cual == "admin":
        import backend.app.agents.copilot_admin_service as modulo
        servicio = modulo.CopilotAdminLLMService.__new__(
            modulo.CopilotAdminLLMService
        )
    else:
        import backend.app.agents.copilot_cliente_service as modulo
        servicio = modulo.CopilotClienteLLMService.__new__(
            modulo.CopilotClienteLLMService
        )

    class _PersonaFalsa:
        model = alias
        max_tokens = 16
        temperature = 0.1
        enable_prompt_caching = False

    servicio.persona_service = _PersonaFalsa()

    capturado: dict[str, str] = {}

    class _RouterFalso:
        def complete(self, **kwargs):
            capturado["model"] = kwargs["model"]
            return SimpleNamespace(
                content="ok", prompt_tokens=1, completion_tokens=1,
                model=kwargs["model"],
            )

    monkeypatch.setattr(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        lambda: _RouterFalso(),
    )

    async def _sin_log(*a, **k):
        return None

    monkeypatch.setattr(servicio, "_log_interaction", _sin_log)

    asyncio.run(
        servicio._call_llm(
            system_prompt="s", user_message="u", db=None, project_id=None,
        )
    )

    assert capturado["model"] == resolver_id(alias), (
        f"el copiloto {cual} mando {capturado['model']!r} al proveedor para el "
        f"alias {alias!r}. Si es el alias sin traducir, es la copia del mapa "
        f"que habia divergido: eso es un 404 de la API, a 300 ms de distancia y "
        f"sin decir que codigo construyo la cadena."
    )
    assert capturado["model"] in ids_validos()


def test_las_personas_del_copiloto_recomiendan_modelos_declarados():
    """El yaml de personas es el otro camino que llega al proveedor."""
    from backend.app.core.ai.model_catalog import verificar_personas_del_copiloto

    yaml = _RAIZ / "docs/catalogs/copilot_personas_v1.yaml"
    assert yaml.is_file(), "el catalogo de personas tiene que estar en el repo"
    verificar_personas_del_copiloto(str(yaml))


def test_la_persona_puede_cambiarse_a_cualquier_alias_del_catalogo(tmp_path):
    """Este es el escenario concreto que llevaba un 404 a produccion.

    ``copilot_personas_v1.yaml`` recomienda hoy ``sonnet-4.6``, que las tres
    copias del mapa conocian. Cambiarlo a ``opus-4.6`` —un alias legitimo que
    los agentes resuelven sin problema— hacia que el copiloto mandase la cadena
    cruda. Aqui se comprueba que ya no.
    """
    from backend.app.core.ai.model_catalog import verificar_personas_del_copiloto

    for alias in alias_validos():
        falso = tmp_path / "personas.yaml"
        falso.write_text(
            f'personas:\n  - id: admin\n    model_recommended: "{alias}"\n',
            encoding="utf-8",
        )
        verificar_personas_del_copiloto(str(falso))
        assert resolver_id(alias) in ids_validos()


# ---------------------------------------------------------------------------
# Coherencia del propio catalogo
# ---------------------------------------------------------------------------

def test_el_catalogo_no_tiene_ids_ni_alias_repetidos():
    ids = [m.id for m in CATALOGO]
    assert len(ids) == len(set(ids))
    alias = list(alias_validos())
    assert len(alias) == len(set(alias))


def test_cada_modelo_declara_por_que_existe():
    for m in CATALOGO:
        assert m.nivel in {"rapido", "equilibrado", "profundo"}, m.id
        assert len(m.por_que) > 40, f"{m.id} no dice por que este modelo y no otro"
