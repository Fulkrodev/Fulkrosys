"""O2 · las 30 llamadas del cliente MAGERIT del navegador apuntaban a 404.

EL DEFECTO
    ``frontend/lib/api/magerit.ts`` abria con ``const BASE = "/api/v1"`` y
    construia las 30 rutas del motor 2 sobre esa base. Pero el router se
    declara con prefijo propio:

        backend/app/motors/m02_magerit/api.py:50
            router = APIRouter(prefix="/magerit", ...)
        backend/app/main.py:613
            app.include_router(magerit_router, prefix="/api/v1", ...)

    Es decir ``/api/v1/magerit/...``. Las 30 rutas del fichero daban 404 y la
    pagina de analisis de riesgos del ciclo ENS (fase 2) estaba muerta entera:
    ni crear analisis, ni cargar activos, ni calcular riesgo, ni exportar.

POR QUE UN TEST ESTATICO Y NO UNO DE INTEGRACION
    Porque el defecto es una DISCREPANCIA entre dos ficheros, y lo que hay que
    impedir es que vuelvan a separarse. Un test que llame a un endpoint prueba
    ese endpoint; este compara las dos listas enteras, asi que cubre las 30 y
    cubrira las que se anyadan.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
CLIENTE_TS = RAIZ / "frontend" / "lib" / "api" / "magerit.ts"


def _base_del_cliente() -> str:
    m = re.search(r'const BASE = "([^"]+)"', CLIENTE_TS.read_text("utf-8"))
    assert m, "no se encontro `const BASE` en magerit.ts"
    return m.group(1)


def _rutas_del_cliente() -> list[str]:
    """Rutas que el navegador pide, con los `${...}` normalizados a `{}`."""
    texto = CLIENTE_TS.read_text("utf-8")
    base = _base_del_cliente()
    rutas = []
    for m in re.finditer(r"`\$\{BASE\}([^`]*)`", texto):
        cola = re.sub(r"\$\{[^}]+\}", "{}", m.group(1))
        rutas.append(base + cola)
    return sorted(set(rutas))


def _paths_del_backend() -> dict[str, set[str]]:
    """Rutas reales de la app, normalizadas a `{}`, con sus metodos.

    Se leen del esquema OpenAPI y no de ``app.routes``: esta version de FastAPI
    deja los routers incluidos como objetos ``_IncludedRouter`` perezosos que
    todavia no han expandido sus rutas, asi que ``app.routes`` devolveria cinco
    entradas y el test pasaria sin medir nada.
    """
    from backend.app.main import app

    fuera: dict[str, set[str]] = {}
    for path, ops in app.openapi()["paths"].items():
        clave = re.sub(r"\{[^}]+\}", "{}", path)
        fuera.setdefault(clave, set()).update(m.upper() for m in ops)
    return fuera


def _rutas_del_backend() -> set[str]:
    return {p for p in _paths_del_backend() if p.startswith("/api/v1/")}


def test_el_fichero_declara_rutas_que_medir():
    """Anti-vacuidad: si el parseo deja de encontrar rutas, este test no vale
    nada y hay que enterarse por aqui, no por un verde falso."""
    rutas = _rutas_del_cliente()
    assert len(rutas) >= 30, f"solo se parsearon {len(rutas)} rutas del cliente"


def test_cada_ruta_del_cliente_existe_en_el_backend():
    reales = _rutas_del_backend()
    assert len(reales) > 500, f"la app solo expone {len(reales)} rutas /api/v1"

    huerfanas = [r for r in _rutas_del_cliente() if r not in reales]
    assert not huerfanas, (
        f"{len(huerfanas)} rutas del cliente MAGERIT no existen en el backend "
        f"(BASE = {_base_del_cliente()!r}):\n  " + "\n  ".join(huerfanas)
    )


def test_existe_la_ruta_que_resuelve_el_analisis_del_proyecto():
    """Sin ella el panel no puede saber que el proyecto YA tiene analisis.

    El id vivia en un `useState` que se vaciaba en cada recarga: el panel
    mostraba "no hay analisis MAGERIT activo" sobre un proyecto que si lo
    tenia, y el unico boton a mano creaba OTRO. En el demo habia un proyecto
    con tres analisis por esta via.
    """
    assert "/api/v1/magerit/projects/{}/analysis" in _rutas_del_backend()

    metodos = _paths_del_backend()["/api/v1/magerit/projects/{}/analysis"]
    assert "GET" in metodos, f"la ruta existe pero no admite GET: {metodos}"
