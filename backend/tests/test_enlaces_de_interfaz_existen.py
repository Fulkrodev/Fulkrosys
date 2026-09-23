"""Guardia: los enlaces de interfaz que emite el backend llevan a una página.

El backend fabrica rutas de NAVEGACIÓN, no de API: el botón «Ir» de las
tarjetas de siguiente acción (``workflow_templates.ACTION_TEMPLATES``), los
``cta_url`` de emails y notificaciones (``deep_links``), los ``target_url`` del
copiloto, los ``cta_url`` de las tareas del workflow... Nadie comprobaba que
esas rutas existieran en ``frontend/app``. Se medía así: 24 de las 25 acciones
de ``ACTION_TEMPLATES`` apuntaban a rutas inexistentes (/admin/proposals/new,
/admin/dda/entries, /admin/controls...), y los enlaces de los emails a tareas,
evidencias y auditorías también. Todos acababan en «no encontrado».

Este test calcula el árbol de páginas a partir de ``frontend/app/**/page.tsx``
(quitando los grupos de ruta ``(x)``; ``[x]`` es un segmento cualquiera y
``[...x]`` uno o más) y exige que cada enlace case con alguna. La query y el
fragmento no cuentan: una página ignora lo que no lee, no da 404 por ello.

No necesita base de datos: importa las constantes, llama a los constructores
de ``DeepLinkGenerator`` y lee el código fuente.
"""
from __future__ import annotations

import ast
import inspect
import re
from functools import lru_cache
from pathlib import Path

import pytest

from backend.app.agents.agent_14_copiloto.service import _ADMIN_NEXT_STEP
from backend.app.core.workflow_templates import ACTION_TEMPLATES
from backend.app.motors.m11_copiloto.workflow_state_scanner import (
    _GOV_STEP_URL,
    _PHASE_ACTIONS,
)
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    load_task_templates,
)
from backend.app.notifications.deep_links import DeepLinkGenerator


_RAIZ = Path(__file__).resolve().parents[2]
_APP = _RAIZ / "frontend" / "app"
_BACKEND = _RAIZ / "backend" / "app"

_BASE = "https://fulkro.test"
_UUID = "00000000-0000-4000-8000-000000000001"


# ─────────────────────────── árbol de páginas ───────────────────────────


_REDIRECT = re.compile(r"""\bredirect\(\s*[`"']([^`"'$]*)(\$?)""")
# Portadas genericas: una pagina que solo manda aqui con una ruta FIJA es una
# redireccion heredada (la seccion ya no existe) y no un destino.
_PORTADAS = {"/", "/admin/projects", "/admin/dashboard", "/client-portal",
             "/client-portal/dashboard"}


def _ruta_de(carpeta: Path, app: Path) -> tuple[str, ...]:
    return tuple(
        s
        for s in carpeta.relative_to(app).parts
        if not (s.startswith("(") and s.endswith(")"))
    )


def _redirige_fuera(fichero: Path) -> bool:
    """El fichero es una redireccion heredada a una portada generica.

    ``/admin/pipeline`` (layout) -> ``/admin/projects``: quien sigue ese enlace
    acaba en el selector. En cambio ``/admin/projects/[id]`` ->
    ``/admin/projects/${id}/summary`` o ``/ml/consume`` -> ``/sign/${token}``
    son enrutadores: redirigen a una ruta con parametros y cuentan como destino.
    """
    if not fichero.exists():
        return False
    m = _REDIRECT.search(fichero.read_text(encoding="utf-8"))
    if m is None or m.group(2):
        return False
    return (m.group(1).rstrip("/") or "/") in _PORTADAS


def _patrones_de(app: Path) -> list[tuple[str, ...]]:
    """Rutas a las que un enlace puede llevar de verdad.

    Se excluyen las redirecciones heredadas: una pagina que solo redirige a
    otra seccion, o todo lo que cuelga de un layout que lo hace (el pipeline
    comercial, dormido). Antes contaban como existentes y la guarda dejaba
    pasar enlaces que acababan en el selector de proyectos.
    """
    patrones = []
    for pagina in app.rglob("page.tsx"):
        if "node_modules" in pagina.parts:
            continue
        ruta = _ruta_de(pagina.parent, app)
        if _redirige_fuera(pagina):
            continue
        carpeta, fuera = pagina.parent, False
        while carpeta != app:
            if _redirige_fuera(carpeta / "layout.tsx"):
                fuera = True
                break
            carpeta = carpeta.parent
        if not fuera:
            patrones.append(ruta)
    return patrones


@lru_cache(maxsize=1)
def _paginas() -> tuple[tuple[str, ...], ...]:
    return tuple(_patrones_de(_APP))


def _casa(patron: tuple[str, ...], segmentos: tuple[str, ...]) -> bool:
    if not patron:
        return not segmentos
    cabeza, resto = patron[0], patron[1:]
    if cabeza.startswith("[[..."):
        # Opcional: cero o más segmentos.
        return any(_casa(resto, segmentos[i:]) for i in range(0, len(segmentos) + 1))
    if cabeza.startswith("[..."):
        return any(_casa(resto, segmentos[i:]) for i in range(1, len(segmentos) + 1))
    if not segmentos:
        return False
    if cabeza.startswith("["):
        return _casa(resto, segmentos[1:])
    return cabeza == segmentos[0] and _casa(resto, segmentos[1:])


def _segmentos(ruta: str) -> tuple[str, ...]:
    ruta = ruta.split("#", 1)[0].split("?", 1)[0]
    return tuple(s for s in ruta.split("/") if s)


def _existe(ruta: str, paginas=None) -> bool:
    paginas = _paginas() if paginas is None else paginas
    segmentos = _segmentos(ruta)
    return any(_casa(p, segmentos) for p in paginas)


def _sin_base(url: str) -> str:
    assert url.startswith(_BASE), f"{url!r} no lleva la base configurada"
    return url[len(_BASE):] or "/"


# ─────────────────────────── controles del comparador ───────────────────────────


def test_el_arbol_de_paginas_se_ha_leido():
    """Si el glob no encontrara nada, todo lo demás pasaría o fallaría en vano."""
    assert len(_paginas()) > 100
    assert ("admin", "projects", "[id]", "dda") in _paginas()


def test_el_comparador_rechaza_rutas_que_no_existen():
    """Control negativo: rutas que existían en el backend y no en el frontend."""
    assert not _existe("/admin/proposals/new")
    assert not _existe(f"/client-portal/evidences/{_UUID}")
    assert not _existe(f"/admin/projects/{_UUID}/verificacion")
    assert not _existe("/admin")
    assert not _existe(f"/admin/projects/{_UUID}/dda/extra")
    # Redirecciones heredadas: existen como fichero pero no son destino.
    assert not _existe("/admin/pipeline")
    assert not _existe(f"/admin/pipeline/leads/{_UUID}")
    assert not _existe("/admin/retainers")
    assert not _existe("/admin/retainers/churn-risk")
    # Un indice que redirige dentro de si mismo si lo es.
    assert _existe(f"/admin/projects/{_UUID}")


def test_el_comparador_acepta_segmentos_dinamicos_y_query():
    assert _existe(f"/admin/projects/{_UUID}/dda")
    assert _existe(f"/admin/projects/{_UUID}/audit?audit={_UUID}")
    assert _existe("/client-portal/")
    assert _existe("/client-portal/workflow#conformity")


def test_el_comparador_entiende_catch_all():
    paginas = [("docs", "[...slug]"), ("tienda", "[[...filtro]]")]
    assert _existe("/docs/a", paginas)
    assert _existe("/docs/a/b/c", paginas)
    assert not _existe("/docs", paginas)
    assert _existe("/tienda", paginas)
    assert _existe("/tienda/x/y", paginas)


# ─────────────────────────── fuentes de enlaces ───────────────────────────


def _enlaces_action_templates() -> list[tuple[str, str]]:
    fuera = []
    for fase, acciones in ACTION_TEMPLATES.items():
        for a in acciones:
            if a.endpoint:
                ruta = a.endpoint.replace("{project_id}", _UUID)
                fuera.append((f"ACTION_TEMPLATES[{fase.value}].{a.action_id}", ruta))
    return fuera


def _argumento_para(nombre: str) -> str:
    if nombre.endswith("_id"):
        return _UUID
    if nombre == "phase_name":
        return "operacion"
    if nombre == "magic_token":
        return "token-de-prueba"
    raise AssertionError(
        f"DeepLinkGenerator tiene un parámetro nuevo ({nombre!r}): dile a este "
        "test qué valor usar para poder comprobar la ruta que construye"
    )


def _enlaces_deep_links() -> list[tuple[str, str]]:
    gen = DeepLinkGenerator(base_url=_BASE)
    fuera = []
    for nombre, metodo in inspect.getmembers(gen, predicate=inspect.ismethod):
        if nombre.startswith("_"):
            continue
        params = [
            p for p in inspect.signature(metodo).parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        args = [_argumento_para(p.name) for p in params]
        fuera.append((f"DeepLinkGenerator.{nombre}", _sin_base(metodo(*args))))
        # Variantes con los opcionales rellenos (p.ej. project_id).
        opcionales = [
            p for p in inspect.signature(metodo).parameters.values()
            if p.default is not inspect.Parameter.empty
        ]
        if opcionales:
            kwargs = {p.name: _argumento_para(p.name) for p in opcionales}
            fuera.append(
                (f"DeepLinkGenerator.{nombre}(+opcionales)",
                 _sin_base(metodo(*args, **kwargs))),
            )
    return fuera


def _enlaces_copiloto() -> list[tuple[str, str]]:
    fuera = []
    for fase, por_rol in _PHASE_ACTIONS.items():
        for rol, hints in por_rol.items():
            for h in hints:
                ruta = h.target_url.replace("{project_id}", _UUID)
                fuera.append((f"_PHASE_ACTIONS[{fase.value}][{rol}].{h.action}", ruta))
    for paso, url in _GOV_STEP_URL.items():
        fuera.append((f"_GOV_STEP_URL[{paso}]", url.replace("{project_id}", _UUID)))
    for motor, (segmento, _label) in _ADMIN_NEXT_STEP.items():
        # Mismo formato que suggest_actions.
        fuera.append(
            (f"_ADMIN_NEXT_STEP[{motor}]", f"/admin/projects/{_UUID}/{segmento}"),
        )
    return fuera


def _enlaces_task_templates() -> list[tuple[str, str]]:
    return [
        (f"task_templates.yaml:{t.id}", t.cta_url.replace("{project_id}", _UUID))
        for t in load_task_templates().templates
        if t.cta_url
    ]


_ENLACES = (
    _enlaces_action_templates()
    + _enlaces_deep_links()
    + _enlaces_copiloto()
    + _enlaces_task_templates()
)


def test_se_recogen_enlaces_de_todas_las_fuentes():
    origenes = {o.split(".")[0].split("[")[0].split(":")[0] for o, _ in _ENLACES}
    assert {
        "ACTION_TEMPLATES", "DeepLinkGenerator", "_PHASE_ACTIONS",
        "_GOV_STEP_URL", "_ADMIN_NEXT_STEP", "task_templates",
    } <= origenes
    # Todo método público del generador se ha ejercitado.
    publicos = {
        n for n, _ in inspect.getmembers(DeepLinkGenerator, inspect.isfunction)
        if not n.startswith("_")
    }
    ejercitados = {
        o.split(".", 1)[1].split("(")[0] for o, _ in _ENLACES
        if o.startswith("DeepLinkGenerator.")
    }
    assert publicos == ejercitados


@pytest.mark.parametrize(("origen", "ruta"), _ENLACES, ids=[o for o, _ in _ENLACES])
def test_el_enlace_lleva_a_una_pagina(origen, ruta):
    assert _existe(ruta), (
        f"{origen} enlaza a {ruta!r}, que no es ninguna página de frontend/app. "
        "Apunta a la página donde se hace esa acción (casi siempre una pestaña "
        "de /admin/projects/{project_id}/..., ver ProjectTabs.tsx)."
    )


# ─────────────────────────── barrido del código fuente ───────────────────────────
#
# Lo anterior cubre las fuentes que se pueden importar. Los enlaces sueltos
# (`cta_url = deep_links._build("/admin/...")`, `href="/admin/..."`) se buscan
# leyendo el código: todo literal que empiece por una ruta de interfaz y que no
# sea la ruta de un endpoint (decoradores de FastAPI, `prefix=`), un docstring o
# el argumento de un `startswith`.

_PREFIJO_UI = re.compile(r"^/(admin|client-portal|auditor-portal)(/|$)")

# Enlaces que no se pueden comprobar leyendo el literal, con su motivo.
_EXCEPCIONES_BARRIDO = {
    # `/admin/projects/{project_id}/{segment}`: el segmento sale de
    # _ADMIN_NEXT_STEP, que se comprueba entero más arriba.
    ("agents/agent_14_copiloto/service.py", "/admin/projects/*/*"),
}


def _literales_de_ruta(fichero: Path) -> list[tuple[int, str]]:
    arbol = ast.parse(fichero.read_text(encoding="utf-8"))
    ignorar: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for deco in nodo.decorator_list:
                ignorar.update(id(n) for n in ast.walk(deco))
        if isinstance(nodo, ast.keyword) and nodo.arg == "prefix":
            ignorar.update(id(n) for n in ast.walk(nodo.value))
        if isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant):
            ignorar.add(id(nodo.value))  # docstrings
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in {"startswith", "endswith", "removeprefix", "add_api_route"}
        ):
            for arg in nodo.args:
                ignorar.update(id(n) for n in ast.walk(arg))
        if isinstance(nodo, ast.JoinedStr):
            # Los trozos de un f-string se evalúan con el f-string entero.
            ignorar.update(id(v) for v in nodo.values)

    fuera = []
    for nodo in ast.walk(arbol):
        if id(nodo) in ignorar:
            continue
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            texto = nodo.value
        elif isinstance(nodo, ast.JoinedStr):
            texto = "".join(
                v.value if isinstance(v, ast.Constant) else "*" for v in nodo.values
            )
        else:
            continue
        texto = texto.strip()
        if " " in texto or not _PREFIJO_UI.match(texto):
            continue
        texto = re.sub(r"\{[^}]*\}", "*", texto)  # marcadores {project_id}
        fuera.append((nodo.lineno, texto))
    return fuera


def _literales_del_backend() -> list[tuple[str, int, str]]:
    fuera = []
    for fichero in sorted(_BACKEND.rglob("*.py")):
        relativa = fichero.relative_to(_BACKEND).as_posix()
        for linea, texto in _literales_de_ruta(fichero):
            fuera.append((relativa, linea, texto))
    return fuera


def test_el_barrido_encuentra_enlaces():
    """Control: el barrido ve los enlaces conocidos (si no, no protege nada)."""
    textos = {t for _, _, t in _literales_del_backend()}
    assert "/admin/projects/*/verification" in textos
    assert "/client-portal/billing" in textos


def test_el_barrido_detecta_un_enlace_muerto(tmp_path):
    """Control negativo del barrido sobre un fichero sintético."""
    f = tmp_path / "x.py"
    f.write_text(
        'from fastapi import APIRouter\n'
        'router = APIRouter(prefix="/admin/solo-api")\n'
        '@router.get("/admin/tampoco")\n'
        'def h():\n'
        '    """/admin/docstring"""\n'
        '    ok = url.startswith("/admin")\n'
        '    return {"cta_url": f"/admin/projects/{pid}/inexistente"}\n',
        encoding="utf-8",
    )
    literales = [t for _, t in _literales_de_ruta(f)]
    assert literales == ["/admin/projects/*/inexistente"]
    assert not _existe(literales[0])


def test_ningun_literal_del_backend_es_un_enlace_muerto():
    muertos = [
        f"{fichero}:{linea} · {texto}"
        for fichero, linea, texto in _literales_del_backend()
        if (fichero, texto) not in _EXCEPCIONES_BARRIDO and not _existe(texto)
    ]
    assert not muertos, (
        "rutas de interfaz en el backend que no son ninguna página de "
        "frontend/app:\n  " + "\n  ".join(muertos)
    )
