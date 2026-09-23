"""Catalogo de modelos: la UNICA declaracion de que modelos existen.

Por que existe este modulo
--------------------------
Antes de el, ``grep -rhoE 'claude-(sonnet|opus|haiku)-[0-9][a-z0-9-]*' backend/app
--include="*.py" | sort | uniq -c`` devolvia 8 identificadores distintos en 37
literales repartidos por 18 ficheros, y ``grep -rn "MODEL_CATALOG"`` no devolvia
nada: ningun sitio declaraba cuales eran validos. Debajo de eso habia cinco
defectos separados, y este modulo cierra los cinco:

(a) El mapa de alias estaba TRIPLICADO y las copias YA HABIAN DIVERGIDO:
    ``agents/base.py`` tenia 6 alias; ``copilot_admin_service.py`` y
    ``copilot_cliente_service.py`` tenian 4 — les faltaban ``opus-4`` y
    ``opus-4.6``. Era latente sólo porque ``docs/catalogs/copilot_personas_v1.yaml``
    recomienda ``sonnet-4.6``, que si estaba en las tres copias. Cambiar esa
    linea a ``opus-4.6`` —un alias legitimo que los agentes resuelven sin
    problema— hacia que el copiloto mandase la cadena ``opus-4.6`` cruda a la
    API. Eso es un 404, y llegaba a produccion sin que nada avisara.

(b) ``.get(alias, alias)`` es el mismo patron que ``getattr(obj, "nombre_mal",
    default)``: un alias desconocido no fallaba, pasaba entero como nombre de
    modelo, y el error aparecia a 300 ms de distancia en la respuesta del
    proveedor, sin decir de donde salio la cadena. Aqui ``resolver`` LEVANTA.

(c) La cadena de reserva estaba declarada y no existia. Ver ``llm_router.py``.

(d) ``_MODELS_WITHOUT_TEMPERATURE`` vivia en ``llm_router.py`` como lista
    aparte, y por tanto se actualizaba (o no) sin relacion con el sitio donde se
    anade un modelo. Aqui es un campo del propio modelo: no se puede declarar un
    modelo sin decir si admite ``temperature``.

(e) ``autopilot/orchestrator.py`` escribia el nombre del modelo A MANO en el
    manifiesto de la ejecucion de verificacion, que es el registro de
    procedencia de la evidencia. Ver ``modelo_que_respondio``.

Como se anade un modelo
-----------------------
Se anade una entrada a ``CATALOGO`` con sus seis campos. No hay segundo sitio
que tocar: los alias, los ids validos, la lista de los que no admiten
``temperature`` y la validacion de arranque se derivan todos de aqui. El test
``backend/tests/core/ai/test_model_catalog.py`` recorre ``backend/app`` con AST
y falla si aparece un identificador de modelo que no este declarado aqui.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


_FICHERO = "backend/app/core/ai/model_catalog.py"

#: Prefijo de la variable de entorno que sustituye el id de un alias.
#: Formato: ``FULKRO_MODEL_OVERRIDE__<alias>=<id>``, con los puntos del alias
#: escritos como guion bajo (``opus-4.7`` -> ``FULKRO_MODEL_OVERRIDE__opus-4_7``).
#: El valor SE VALIDA contra el catalogo: no es un passthrough. Sirve para fijar
#: un snapshot fechado sin tocar codigo, no para inventar modelos.
PREFIJO_OVERRIDE = "FULKRO_MODEL_OVERRIDE__"


class ModeloDesconocido(ValueError):
    """Un alias o id de modelo que el catalogo no declara.

    Se levanta en vez de dejar pasar la cadena. El mensaje lleva el alias que
    se pidio, los alias validos y el fichero donde se declaran, porque el
    sintoma de este fallo aparece muy lejos de su causa: un 404 del proveedor
    no dice que codigo construyo la cadena.
    """


@dataclass(frozen=True)
class ModeloDeclarado:
    """Un modelo del proveedor, con todo lo que hay que saber de el en un sitio."""

    #: El identificador real del proveedor, tal cual viaja en la peticion.
    id: str
    #: El nombre corto que usan el registry de agentes y las personas del copiloto.
    alias: str
    #: Si el modelo acepta el parametro ``temperature``. Algunos lo han
    #: deprecado y devuelven 400 "temperature is deprecated for this model".
    admite_temperature: bool
    #: "rapido" | "equilibrado" | "profundo"
    nivel: str
    #: La razon por la que este modelo y no otro.
    por_que: str
    #: Alias antiguos que siguen resolviendo a este modelo. Existen porque el
    #: codigo los usa; no se inventan alias nuevos aqui.
    alias_historicos: tuple[str, ...] = ()
    #: Ids fechados (snapshots) del MISMO modelo. Son ids validos del proveedor
    #: y el codigo los usa donde quiere fijar una version concreta.
    snapshots: tuple[str, ...] = ()
    #: Si ``admite_temperature`` se comprobo contra la API de verdad o se
    #: heredo del comportamiento anterior del codigo. Ver AVISO abajo.
    temperatura_verificada: bool = True


# ---------------------------------------------------------------------------
# El catalogo
# ---------------------------------------------------------------------------
#
# AVISO sobre ``temperatura_verificada``: este campo distingue lo comprobado de
# lo heredado. ``claude-opus-4-7`` esta marcado ``admite_temperature=False``
# porque el codigo ya lo trataba asi (era el unico miembro de la antigua
# ``_MODELS_WITHOUT_TEMPERATURE``, con el 400 del proveedor documentado en el
# comentario que la acompanaba). ``claude-opus-4-8`` esta marcado ``True`` y
# ``temperatura_verificada=False``: NO se ha comprobado si heredo la deprecacion
# de 4.7, y hoy se le envia ``temperature`` desde
# ``m08_verification/agent/triage_agent.py``. Comprobarlo exige una llamada real
# con ANTHROPIC_API_KEY; mientras no se haga, el campo dice que no se sabe en
# vez de fingir que si.

CATALOGO: tuple[ModeloDeclarado, ...] = (
    ModeloDeclarado(
        id="claude-haiku-4-5",
        alias="haiku-4.5",
        admite_temperature=True,
        nivel="rapido",
        por_que=(
            "Clasificacion corta sobre catalogo cerrado y triage de hallazgos: "
            "la salida es estructura, no prosa, y el coste por llamada manda "
            "porque el volumen es alto (A27 clasificador, m08 llm_classifier, "
            "m23 vigilancia)."
        ),
        snapshots=("claude-haiku-4-5-20251001",),
    ),
    ModeloDeclarado(
        id="claude-sonnet-4-5",
        alias="sonnet-4.5",
        admite_temperature=True,
        nivel="equilibrado",
        por_que=(
            "Default historico del router y de AgentBase. Equilibrio coste/"
            "calidad para agentes que redactan con citas obligatorias (R2)."
        ),
        snapshots=("claude-sonnet-4-5-20250929",),
    ),
    ModeloDeclarado(
        id="claude-sonnet-4-6",
        alias="sonnet-4.6",
        admite_temperature=True,
        nivel="equilibrado",
        por_que=(
            "El caballo de batalla: 7 de las 13 entradas del registry de agentes "
            "lo declaran, y es el que recomiendan las dos personas del copiloto "
            "en docs/catalogs/copilot_personas_v1.yaml."
        ),
    ),
    ModeloDeclarado(
        id="claude-opus-4-6",
        alias="opus-4.6",
        admite_temperature=True,
        nivel="profundo",
        por_que=(
            "Modelo de reserva del router (ANTHROPIC_FALLBACK_MODEL). Se eligio "
            "de familia distinta al default para que un fallo de capacidad del "
            "primario no arrastre tambien al de reserva."
        ),
        alias_historicos=("opus-4",),
    ),
    ModeloDeclarado(
        id="claude-opus-4-7",
        alias="opus-4.7",
        admite_temperature=False,
        nivel="profundo",
        por_que=(
            "Razonamiento largo donde el error cuesta una no conformidad de "
            "auditoria: A11 auditor virtual (audit dry-run) y A19 propuestas."
        ),
    ),
    ModeloDeclarado(
        id="claude-opus-4-8",
        alias="opus-4.8",
        # Verificado el 2026-09-23 con una llamada real: el proveedor responde
        # 400 «`temperature` is deprecated for this model». Hereda la
        # deprecacion de 4.7. Con True, el triage de m08 fallaba en CADA
        # llamada. El determinismo de ese triage no sale de la temperatura sino
        # de la salida estructurada y el modelo fijado.
        admite_temperature=False,
        nivel="profundo",
        por_que=(
            "Triage de hallazgos de seguridad en m08: decide si un hallazgo de "
            "un motor determinista se aplica, y esa decision entra en el "
            "expediente de evidencia. Se pinnea el modelo a proposito "
            "(triage_agent.py: temperatura 0, modelo fijo, salida estructurada)."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Indices derivados · NO se escriben a mano, se construyen del catalogo
# ---------------------------------------------------------------------------

def _construir_indice() -> dict[str, ModeloDeclarado]:
    indice: dict[str, ModeloDeclarado] = {}
    for m in CATALOGO:
        for clave in (m.alias, m.id, *m.alias_historicos, *m.snapshots):
            anterior = indice.get(clave)
            if anterior is not None and anterior is not m:
                raise RuntimeError(
                    f"catalogo de modelos incoherente: {clave!r} esta declarado "
                    f"por {anterior.id} y por {m.id} ({_FICHERO})"
                )
            indice[clave] = m
    return indice


_INDICE: dict[str, ModeloDeclarado] = _construir_indice()


def alias_validos() -> tuple[str, ...]:
    """Los alias que ``resolver`` acepta, alfabeticos (sin ids ni snapshots)."""
    nombres: list[str] = []
    for m in CATALOGO:
        nombres.append(m.alias)
        nombres.extend(m.alias_historicos)
    return tuple(sorted(nombres))


def ids_validos() -> frozenset[str]:
    """Todo identificador que el proveedor puede recibir, snapshots incluidos."""
    ids: set[str] = set()
    for m in CATALOGO:
        ids.add(m.id)
        ids.update(m.snapshots)
    return frozenset(ids)


# ---------------------------------------------------------------------------
# Resolucion
# ---------------------------------------------------------------------------

def _override_para(alias: str) -> str | None:
    """Lee ``FULKRO_MODEL_OVERRIDE__<alias>`` y lo VALIDA contra el catalogo."""
    variable = PREFIJO_OVERRIDE + alias.replace(".", "_")
    crudo = (os.environ.get(variable) or "").strip()
    if not crudo:
        return None
    if crudo not in ids_validos():
        raise ModeloDesconocido(
            f"{variable}={crudo!r} no es un identificador declarado. "
            f"Esta variable sustituye el id de un alias, pero se valida contra "
            f"el catalogo: no es un passthrough. Ids validos: "
            f"{sorted(ids_validos())}. Se declaran en {_FICHERO}."
        )
    return crudo


def resolver(alias: str) -> ModeloDeclarado:
    """Devuelve el modelo declarado para un alias o un id. LEVANTA si no existe.

    Acepta tanto el alias corto (``sonnet-4.6``) como el id del proveedor
    (``claude-sonnet-4-6``) o un snapshot fechado, porque el codigo usa las tres
    formas. Lo que NO acepta es una cadena desconocida: eso levanta
    ``ModeloDesconocido`` aqui, donde se sabe quien la construyo, en vez de
    viajar a la API y volver como un 404 sin procedencia.
    """
    clave = (alias or "").strip()
    modelo = _INDICE.get(clave)
    if modelo is None:
        raise ModeloDesconocido(
            f"modelo {alias!r} desconocido. Alias validos: "
            f"{list(alias_validos())}. Ids validos: {sorted(ids_validos())}. "
            f"Se declaran en {_FICHERO}."
        )
    return modelo


def resolver_id(alias: str) -> str:
    """El id del proveedor para un alias, con el override de entorno aplicado.

    Si el alias entra ya como un snapshot fechado se devuelve tal cual: quien
    pide una version concreta la quiere, y el override actua sobre el alias.
    """
    modelo = resolver(alias)
    clave = (alias or "").strip()
    if clave in modelo.snapshots:
        return clave
    override = _override_para(modelo.alias)
    return override or modelo.id


def admite_temperature(modelo: str) -> bool:
    """Si a este modelo se le puede enviar ``temperature``.

    Un modelo NO declarado devuelve True: el router no es el sitio donde se
    valida el catalogo (lo hace ``resolver``), y aqui una excepcion convertiria
    un default de entorno arbitrario en un fallo de arranque. Ver el test
    ``test_router_omits_temperature_for_opus_47``.
    """
    declarado = _INDICE.get((modelo or "").strip())
    return True if declarado is None else declarado.admite_temperature


# ---------------------------------------------------------------------------
# Validacion de arranque
# ---------------------------------------------------------------------------

#: Valores del campo ``model`` del registry que NO son modelos. A21 declara
#: "deterministic" porque no llama a ningun LLM; queda escrito aqui para que el
#: validador no lo confunda con un alias mal escrito.
NO_SON_MODELOS = frozenset({"deterministic"})


def verificar_registry_de_agentes() -> None:
    """Aborta si algun agente declara un alias que el catalogo no tiene.

    Esto es lo que convierte la deriva de (a) en un fallo de ARRANQUE en vez de
    un 404 del proveedor en produccion. Se engancha en ``run_startup_checks``.
    """
    from backend.app.agents.registry import AGENT_REGISTRY

    malos: list[str] = []
    for agente_id, entrada in AGENT_REGISTRY.items():
        declarado = entrada.get("model")
        if not declarado or declarado in NO_SON_MODELOS:
            continue
        try:
            resolver(declarado)
        except ModeloDesconocido:
            malos.append(f"A{agente_id} ({entrada.get('name', '?')}) -> {declarado!r}")
    if malos:
        raise ModeloDesconocido(
            "el registry de agentes declara modelos que el catalogo no tiene: "
            + " · ".join(malos)
            + f". Alias validos: {list(alias_validos())}. Se declaran en {_FICHERO}."
        )


def verificar_personas_del_copiloto(ruta_yaml: str | None = None) -> None:
    """Aborta si una persona del copiloto recomienda un alias inexistente.

    Es el otro camino que llega al proveedor: ``persona_service.model`` sale de
    ``docs/catalogs/copilot_personas_v1.yaml`` y antes se resolvia con un mapa
    propio, incompleto, que dejaba pasar la cadena cruda. Si el catalogo de
    personas no esta en disco (despliegue que no lo empaqueta) no se comprueba
    nada: este validador existe para cazar un alias mal escrito, no para exigir
    el fichero.
    """
    import re
    from pathlib import Path

    ruta = Path(
        ruta_yaml
        or Path(__file__).resolve().parents[4] / "docs/catalogs/copilot_personas_v1.yaml"
    )
    if not ruta.is_file():
        return
    malos: list[str] = []
    for numero, linea in enumerate(
        ruta.read_text(encoding="utf-8").splitlines(), start=1
    ):
        m = re.match(r"\s*model_recommended:\s*['\"]?([^'\"\s]+)", linea)
        if not m:
            continue
        try:
            resolver(m.group(1))
        except ModeloDesconocido:
            malos.append(f"{ruta.name}:{numero} -> {m.group(1)!r}")
    if malos:
        raise ModeloDesconocido(
            "hay personas del copiloto que recomiendan un modelo que el catalogo "
            "no tiene: " + " · ".join(malos)
            + f". Alias validos: {list(alias_validos())}. Se declaran en {_FICHERO}."
        )


# ---------------------------------------------------------------------------
# Procedencia
# ---------------------------------------------------------------------------

def modelo_que_respondio(respuesta: object, pedido: str) -> str:
    """El modelo que DEVOLVIO la llamada, no el que se tecleo.

    Existe por (e): ``autopilot/orchestrator.py`` escribia ``model_version``
    a mano en el manifiesto de la ejecucion de verificacion —el registro de
    procedencia de la evidencia— de modo que cambiar el modelo del triage
    dejaba el manifiesto diciendo el anterior. Un manifiesto que declara un
    modelo distinto del que genero el contenido es la reproducibilidad rota en
    el sitio donde mas duele.

    ``pedido`` es el ultimo recurso: se usa sólo si la respuesta no trae modelo
    (una llamada que fallo antes de empezar), y entonces lo que se registra es
    lo que se pidio, que sigue siendo verdad.
    """
    devuelto = getattr(respuesta, "model", None)
    if devuelto is None and isinstance(respuesta, dict):
        devuelto = respuesta.get("model")
    return str(devuelto or pedido)
