"""O1.2 · ninguna puerta de autorizacion se queda fuera de la cifra publicada.

EL DEFECTO
    `scripts/medir_autorizacion.py` recorre el arbol de dependencias de cada
    ruta y publica "el 76,8 % de las rutas con puerta exigen ser el
    administrador". Esa cifra dejaba fuera dos puertas reales, porque no son
    dependencias: `require_ens_role` (m03_dda/api.py) y
    `require_ens_role_asignado` (m02_magerit/api.py) se llaman desde el CUERPO
    del endpoint, asi que no estan en el `dependant` ni en el esquema OpenAPI.

POR QUE ESTAN EN EL CUERPO, que no es descuido
    Consultan `client_contacts JOIN projects`, y `projects` tiene RLS por
    `current_project_id()`. Solo ven algo DESPUES de que el endpoint fije el
    contexto de inquilino. Como dependencia se ejecutarian antes y devolverian
    "no hay titular" siempre: 403 tambien para quien si tiene el rol.

    La contrapartida queda escrita en la cabecera del script: al no ser
    dependencias, un consumidor de la API no las ve en OpenAPI.

LO QUE ESTE TEST IMPIDE
    Que alguien anyada una tercera puerta de este tipo y la cifra publicada siga
    sin contarla. Si aparece un `await require_ens_role_loquesea(...)` que no
    este declarado en `PUERTAS_EN_CUERPO`, falla aqui.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "scripts/medir_autorizacion.py"
APP = RAIZ / "backend/app"


def _declaradas() -> set[str]:
    texto = SCRIPT.read_text("utf-8")
    m = re.search(r"PUERTAS_EN_CUERPO\s*=\s*\(([^)]*)\)", texto, re.S)
    assert m, "PUERTAS_EN_CUERPO no existe en medir_autorizacion.py"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def _llamadas_en_el_codigo() -> dict[str, list[str]]:
    """Toda llamada `await require_*` que levante 403 por rol ENS."""
    encontradas: dict[str, list[str]] = {}
    ficheros = list(APP.rglob("*.py"))
    assert len(ficheros) > 500, (
        f"solo {len(ficheros)} ficheros barridos: la ruta esta mal y este test "
        "no comprueba nada"
    )
    for py in ficheros:
        if py.name == "require_ens_role.py":
            continue  # su definicion, no una llamada
        for i, linea in enumerate(py.read_text("utf-8", errors="ignore").splitlines(), 1):
            sin_com = linea.split("#", 1)[0]
            for m in re.finditer(r"\bawait\s+(require_ens_role\w*)\s*\(", sin_com):
                encontradas.setdefault(m.group(1), []).append(
                    f"{py.relative_to(RAIZ)}:{i}"
                )
    return encontradas


def test_toda_puerta_de_rol_ens_llamada_en_el_cuerpo_esta_declarada():
    declaradas = _declaradas()
    usadas = _llamadas_en_el_codigo()
    sin_declarar = {k: v for k, v in usadas.items() if k not in declaradas}
    assert not sin_declarar, (
        "puertas llamadas desde el cuerpo que la cifra publicada NO cuenta:\n"
        + "\n".join(f"  {k}: {', '.join(v)}" for k, v in sorted(sin_declarar.items()))
        + "\nDeclaralas en PUERTAS_EN_CUERPO de scripts/medir_autorizacion.py."
    )


def test_el_test_no_es_vacuo_hay_al_menos_dos_puertas_en_el_cuerpo():
    """Si el barrido dejara de encontrar nada, este fichero seria decorativo."""
    usadas = _llamadas_en_el_codigo()
    total = sum(len(v) for v in usadas.values())
    assert total >= 2, (
        f"solo {total} llamadas encontradas · se esperaban al menos las dos de "
        "m02_magerit y m03_dda"
    )


def test_el_script_explica_por_que_no_son_dependencias():
    """La contrapartida tiene que constar, no solo el numero."""
    texto = SCRIPT.read_text("utf-8")
    assert "OpenAPI" in texto
    assert "RLS" in texto or "current_project_id" in texto
