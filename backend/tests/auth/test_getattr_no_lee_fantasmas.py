"""O2 · barrido: ningun ``getattr`` con defecto lee un atributo inexistente.

EL DEFECTO DEL QUE SALE ESTE BARRIDO
    ``getattr(x, "nombre", defecto)`` sobre un atributo que no existe NO falla:
    devuelve el defecto. Si ese defecto alimenta una decision de autorizacion,
    el error se convierte en silencio.

    Eso es lo que paso en ``m01_categorization/dimensions_api`` y en
    ``m_workflow_engine/api``: los dos leian un campo "pool" sobre el sujeto o
    su usuario y una bandera de administrador sobre el usuario. Ninguno de los
    dos nombres existe. Los ``getattr`` devolvian siempre su defecto, la rama de
    administracion era codigo inalcanzable y Marcos recibia 403 en doce rutas.

    SEIS ocurrencias, tres por fichero:

        dimensions_api.py:93   getattr(subject, "pool", None) or getattr(
        dimensions_api.py:94       subject.user, "pool", None)
        dimensions_api.py:109  getattr(subject.user, "is_marcos", False)
        m_workflow_engine/api.py:84, 85, 101   las mismas tres

QUE COMPRUEBA
    Todo ``getattr(sujeto, "attr", defecto)`` de ``backend/app`` donde el objeto
    sea un sujeto de autenticacion, contra los atributos REALES de
    ``AuthSubject``, ``User`` y ``ClientUser``. Si el nombre no existe en
    ninguno de los tres, el lector esta leyendo un fantasma.

    Se excluye ``request.state``: ahi el defecto es el idioma correcto, porque
    el atributo puede faltar de verdad (peticion sin autenticar).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

_OBJETO_SUJETO = re.compile(
    r"\b(subject|user|actor|principal|current_user|auth_\w+|client_user)\b"
)


def _atributos_reales() -> set[str]:
    from backend.app.auth.global_dep import AuthSubject
    from backend.app.models.auth import User
    from backend.app.models.client_portal import ClientUser

    nombres: set[str] = set()
    for cls in (AuthSubject, User, ClientUser):
        nombres |= set(getattr(cls, "__slots__", ()) or ())
        nombres |= set(getattr(cls, "__annotations__", {}))
        nombres |= {k for k in dir(cls) if not k.startswith("__")}
        mapper = getattr(cls, "__mapper__", None)
        if mapper is not None:
            nombres |= {c.key for c in mapper.attrs}
    return nombres


def _lecturas_sobre_sujetos() -> list[tuple[str, int, str, str]]:
    fuera = []
    for py in (RAIZ / "backend" / "app").rglob("*.py"):
        try:
            arbol = ast.parse(py.read_text("utf-8", errors="ignore"))
        except SyntaxError:  # pragma: no cover
            continue
        for n in ast.walk(arbol):
            if not (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "getattr"
                and len(n.args) == 3
                and isinstance(n.args[1], ast.Constant)
                and isinstance(n.args[1].value, str)
            ):
                continue
            obj = ast.unparse(n.args[0])
            if "request.state" in obj or not _OBJETO_SUJETO.search(obj):
                continue
            fuera.append(
                (str(py.relative_to(RAIZ)), n.lineno, obj, n.args[1].value)
            )
    return fuera


def test_hay_lecturas_que_medir():
    """Anti-vacuidad: si el parseo deja de encontrarlas, el guard no vale."""
    lecturas = _lecturas_sobre_sujetos()
    assert len(lecturas) >= 30, f"solo {len(lecturas)} lecturas parseadas"


def test_ninguna_lectura_apunta_a_un_atributo_inexistente():
    reales = _atributos_reales()
    assert "role_pool" in reales and "client_id" in reales, (
        "el conjunto de atributos reales se construyo mal"
    )
    assert "pool" not in reales, (
        "si 'pool' existiera, este guard no probaria nada: era justo el "
        "nombre inventado que dejo muerta la rama de administracion"
    )

    fantasmas = [
        f"{f}:{l}  getattr({o}, {a!r}, ...)"
        for f, l, o, a in _lecturas_sobre_sujetos()
        if a not in reales
    ]
    assert not fantasmas, (
        f"{len(fantasmas)} lecturas de atributos que no existen en "
        "AuthSubject/User/ClientUser; devuelven siempre su valor por defecto "
        "y convierten un error en un silencio:\n  " + "\n  ".join(fantasmas)
    )
