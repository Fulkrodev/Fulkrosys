"""Guardia: todo ``fetch`` directo del frontend que ESCRIBE lleva cabecera CSRF.

El backend exige ``X-CSRF-Token`` igual a la cookie ``fulkro_csrf`` en toda
peticion que no sea GET/HEAD/OPTIONS (``backend/app/auth/csrf.py``, aplicado a
todas las rutas fuera de la lista blanca por ``auth/global_dep.py``). Los
envoltorios ``api`` y ``clientApi`` la ponen solos; un ``fetch`` directo no.

Medido el 2026-09-23 con la pila levantada, tres ``fetch`` directos que no la
ponian y fallaban con 403 «csrf token mismatch» sin que nadie lo viera:

- ``lib/api/copiloto.ts``: el copiloto del portal de cliente. No respondio
  nunca a ningun cliente, con clave de API o sin ella.
- ``hooks/useLogout.ts``: cerrar sesion (admin). La interfaz decia «Sesión
  cerrada», la sesion seguia viva en el servidor y la cookie httpOnly seguia
  en el navegador. El del cliente, ademas, apuntaba a una ruta sin ``/api/v1``
  que Next no reenvia (404).
- ``lib/api/draft-report.ts``: el borrador de informe de auditoria.

Este test no sabe si una peticion concreta llega al backend: sabe si el codigo
que la construye incluye el token. Por eso las excepciones van una a una, con
el motivo por el que ese ``fetch`` no necesita el token.
"""
from __future__ import annotations

import re
from pathlib import Path

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
_CARPETAS = ("app", "components", "hooks", "lib")
_METODOS_QUE_ESCRIBEN = {"POST", "PUT", "PATCH", "DELETE"}

# fichero relativo a frontend/ -> por que no lleva token
_EXCEPCIONES = {
    "lib/admin-messages/api.ts": (
        "PUT directo a MinIO con URL prefirmada: no va a /api/v1, no lleva "
        "cookies y la autorizacion es la firma de la propia URL."
    ),
    "lib/client-messages/api.ts": (
        "PUT directo a MinIO con URL prefirmada (mismo caso que admin-messages)."
    ),
    "lib/api/diagnostico-precliente.ts": (
        "Lead sin cuenta: /api/v1/onboarding/consume y /api/v1/onboarding/me/ "
        "estan en la lista blanca de global_dep.py; se autentica con cabeceras "
        "X-Onboarding-Session-*, no con la cookie de sesion."
    ),
    "lib/api/public-portals.ts": (
        "Portales por enlace firmado bajo /api/v1/public/, en la lista blanca: "
        "el token va en la URL, no hay cookie de sesion."
    ),
}


def _argumentos(texto: str, inicio: int) -> str:
    """Texto entre el parentesis de ``fetch(`` y su cierre, respetando anidamiento."""
    nivel = 0
    for i in range(inicio, len(texto)):
        c = texto[i]
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
            if nivel == 0:
                return texto[inicio + 1 : i]
    return texto[inicio + 1 :]


def fetch_sin_csrf(texto: str) -> list[tuple[int, str]]:
    """``(linea, metodo)`` de cada ``fetch`` que escribe sin token CSRF.

    El token cuenta si aparece en los argumentos o en las 25 lineas previas
    (el patron del repo monta ``headers`` justo antes de la llamada).
    """
    hallazgos: list[tuple[int, str]] = []
    for m in re.finditer(r"(?<![\w.])fetch\(", texto):
        args = _argumentos(texto, m.end() - 1)
        metodo = re.search(r"\bmethod:\s*[\"'`]([A-Za-z]+)[\"'`]", args)
        if metodo is None:
            if re.search(r"\bmethod:", args) is None:
                continue  # sin `method` → GET
            nombre = "dinamico"
        else:
            nombre = metodo.group(1).upper()
            if nombre not in _METODOS_QUE_ESCRIBEN:
                continue
        linea = texto.count("\n", 0, m.start()) + 1
        previas = "\n".join(texto.splitlines()[max(0, linea - 26) : linea - 1])
        if re.search(r"csrf", args + previas, re.IGNORECASE):
            continue
        hallazgos.append((linea, nombre))
    return hallazgos


def test_el_detector_salta_con_un_fetch_sin_token():
    """Control negativo: sin esto, un detector que no detecta nada pasaria."""
    sin = 'await fetch("/api/v1/x", {\n  method: "POST",\n  credentials: "include",\n});'
    con = (
        'await fetch("/api/v1/x", {\n  method: "POST",\n'
        '  headers: { ...csrfHeaders() },\n});'
    )
    lectura = 'await fetch("/api/v1/x", { credentials: "include" });'
    assert fetch_sin_csrf(sin) == [(1, "POST")]
    assert fetch_sin_csrf(con) == []
    assert fetch_sin_csrf(lectura) == []


def test_ningun_fetch_que_escribe_va_sin_csrf():
    fallos: list[str] = []
    for carpeta in _CARPETAS:
        for ruta in sorted((_FRONTEND / carpeta).rglob("*.ts*")):
            if ruta.suffix not in {".ts", ".tsx"}:
                continue
            relativa = ruta.relative_to(_FRONTEND).as_posix()
            if relativa in _EXCEPCIONES:
                continue
            for linea, metodo in fetch_sin_csrf(ruta.read_text(encoding="utf-8")):
                fallos.append(f"frontend/{relativa}:{linea} · {metodo}")
    assert not fallos, (
        "fetch directo que escribe sin X-CSRF-Token (el backend responde 403 "
        "«csrf token mismatch»). Usa `csrfHeaders()` de frontend/lib/csrf.ts o "
        "el envoltorio `api`/`clientApi`; si de verdad no hace falta, anade el "
        "fichero a _EXCEPCIONES con el motivo:\n  " + "\n  ".join(fallos)
    )


def test_las_excepciones_siguen_existiendo():
    """Una excepcion de un fichero borrado es una puerta abierta sin motivo."""
    for relativa in _EXCEPCIONES:
        assert (_FRONTEND / relativa).exists(), f"excepcion huerfana: {relativa}"
