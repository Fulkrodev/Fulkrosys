"""Guardia de completitud de `.env.example`.

QUÉ MIDE ESTE TEST (y qué NO)
=============================
El código Python de `backend/app` lee **muchos** nombres de variable de entorno
(la suma de los campos de ``Settings`` y del barrido AST pasa de 120). Exigir
que los 120 estén en `.env.example` sería absurdo: la mayoría son interruptores
internos con un default sano que nadie necesita tocar.

Este test mide un subconjunto concreto y defendible, el **suelo mínimo**: las
variables que, si faltan de la plantilla, dejan al lector atascado o con un
sistema inseguro. Cuatro reglas, las cuatro derivadas por reflexión del código
(ninguna lista de nombres escrita a mano):

  R1 · ARRANQUE. Las de ``backend.app.startup_checks._REQUIRED_ENV_VARS``. Sin
       ellas ``run_startup_checks()`` aborta el arranque: son, literalmente, la
       diferencia entre "arranca" y "no arranca".

  R2 · CREDENCIALES DECLARADAS. Todo campo de ``Settings`` cuyo tipo sea
       ``SecretStr``. Un secreto no se puede adivinar leyendo el código, así que
       tiene que estar enumerado en la plantilla (aunque sea vacío o comentado)
       para que el operador sepa que existe.

  R3 · APUNTAN A ESTA MÁQUINA. Todo campo de ``Settings`` cuyo valor por defecto
       contenga ``localhost`` o ``127.0.0.1``. Cualquier despliegue que no sea el
       portátil de quien lo escribió tiene que sobreescribirlas, y para eso hay
       que saber que están.

  R4 · CREDENCIALES LEÍDAS A PELO. Nombres hallados por el barrido AST
       (``os.environ[...]`` / ``os.environ.get`` / ``os.getenv`` con literal de
       cadena sobre ``backend/app``) cuyo nombre delate material secreto
       (SECRET, PASSWORD, TOKEN, PRIVATE_KEY, SIGNING_KEY, ENCRYPTION_KEY,
       FERNET_KEY, CREDENTIALS). Se excluyen los que terminan en ``_PATH``:
       ésos son rutas a un fichero, no el secreto.

Lo que este test NO hace, dicho explícitamente:

  · NO exige documentar los interruptores con default sano (p. ej.
    ``FULKRO_TIMESTAMP_ENABLED``). `.env.example` documenta muchos de ellos por
    cortesía; documentar de más nunca hace fallar a este test.
  · NO hace la comprobación inversa completa ("toda variable de `.env.example`
    la lee alguien"): la plantilla documenta a propósito variables que este
    barrido no ve — las del frontend (``FULKRO_AUTH_PUBLIC_KEY``), las que se
    leen como argumento ``env_var=`` de ``load_signing_private_key``
    (``FULKRO_M05/M06/M07_SIGNING_PRIVATE_KEY``) y las que sólo lee la suite
    (``FULKRO_RUN_LLM_TESTS``). Sí hay una comprobación inversa ESTRECHA: que no
    reaparezcan las ``ENS_RADAR_*`` del subsistema retirado.
  · NO valida los VALORES. Que ``DATABASE_URL`` esté documentada no significa
    que su valor conecte con nada.

Una variable cuenta como documentada tanto si la línea está activa (``VAR=...``)
como si está comentada (``# VAR=...``): la plantilla no puede traer secretos
reales, así que muchas van comentadas a propósito.

Detalle que importa (y que el propio `.env.example` explica en su cabecera):
``backend/app/config.py`` NO declara ``env_prefix``, de modo que el campo
``minio_secret_key`` se lee de ``MINIO_SECRET_KEY``. Los nombres de R2/R3 se
derivan con la API de pydantic-settings (``EnvSettingsSource._extract_field_info``),
no reconstruyéndolos a mano, y ``test_el_nombre_de_env_se_deriva_sin_prefijo``
deja constancia de ese hecho.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_settings.sources import EnvSettingsSource

from backend.app.config import Settings
from backend.app.startup_checks import _REQUIRED_ENV_VARS

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_EXAMPLE = _REPO_ROOT / ".env.example"
_APP_DIR = _REPO_ROOT / "backend" / "app"

# Línea que documenta una variable: activa (``VAR=``) o comentada (``# VAR=``).
_DOCUMENTED_LINE = re.compile(r"^\s*(?:#\s*)?([A-Z][A-Z0-9_]*)\s*=")

# R4 · nombres que delatan material secreto.
_SECRET_NAME = re.compile(
    r"(SECRET|PASSWORD|TOKEN|PRIVATE_KEY|SIGNING_KEY|ENCRYPTION_KEY"
    r"|FERNET_KEY|CREDENTIALS)"
)

# -----------------------------------------------------------------------------
# EXCEPCIONES · una línea de comentario por excepción, diciendo POR QUÉ.
# Regla común: el nombre lo impone el SDK de un tercero, no FULKRO. Ponerlas en
# `.env.example` sugeriría que son configuración de FULKRO cuando en realidad las
# fija el entorno del proveedor (perfil de AWS, cuenta de servicio de GCP) y las
# herramientas las heredan del proceso.
# El test `test_las_excepciones_siguen_siendo_necesarias` falla si alguna deja
# de ser alcanzada por las reglas: así no se pudren aquí para siempre.
# -----------------------------------------------------------------------------
_EXCEPCIONES: dict[str, str] = {
    # Credencial estándar del SDK de AWS · la exporta el operador o la inyecta el
    # perfil/rol de la máquina; prowler_runner y scoutsuite_runner sólo la leen
    # para pasarla al subproceso del escáner (M08, sólo con USE_MCP_REAL=true).
    "AWS_SECRET_ACCESS_KEY": "nombre impuesto por el SDK de AWS",
    # Ruta a la cuenta de servicio de GCP · convención de la librería de Google
    # (la fija `gcloud auth application-default login`); scoutsuite_runner la
    # propaga tal cual al subproceso.
    "GOOGLE_APPLICATION_CREDENTIALS": "nombre impuesto por el SDK de Google",
}


# =============================================================================
# Extracción
# =============================================================================

def _documented_names() -> set[str]:
    """Variables que `.env.example` documenta (línea activa o comentada)."""
    names: set[str] = set()
    for line in _ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        match = _DOCUMENTED_LINE.match(line)
        if match:
            names.add(match.group(1))
    return names


def _settings_env_names() -> dict[str, str]:
    """Mapa ``NOMBRE_ENV -> campo`` derivado de ``Settings`` por reflexión.

    Usa la API de pydantic-settings en vez de reconstruir el nombre a mano, para
    que un futuro ``env_prefix`` o un ``validation_alias`` se reflejen aquí solos.
    El nombre se normaliza a MAYÚSCULAS porque ``case_sensitive=False``: la
    fuente devuelve la forma en minúsculas y la convención del fichero es
    mayúsculas.
    """
    source = EnvSettingsSource(Settings)
    out: dict[str, str] = {}
    for field_name, field in Settings.model_fields.items():
        for _, env_name, _ in source._extract_field_info(field, field_name):
            out[env_name.upper()] = field_name
    return out


def _ast_env_names() -> dict[str, list[str]]:
    """Barrido AST de ``backend/app``: ``NOMBRE_ENV -> ["fichero:línea", ...]``.

    Sólo cuenta accesos con literal de cadena: ``os.environ["X"]``,
    ``os.environ.get("X")``, ``os.getenv("X")``. Un acceso con nombre calculado
    en tiempo de ejecución es invisible para este barrido (limitación conocida;
    ver el docstring del módulo).
    """
    found: dict[str, list[str]] = {}
    for path in sorted(_APP_DIR.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover
            continue
        for node in ast.walk(tree):
            name = _env_name_of(node)
            if name:
                rel = path.relative_to(_REPO_ROOT)
                found.setdefault(name, []).append(f"{rel}:{node.lineno}")
    return found


def _env_name_of(node: ast.AST) -> str | None:
    """Devuelve el literal leído del entorno en este nodo, o None."""
    # os.environ["X"]
    if isinstance(node, ast.Subscript):
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "environ"
            and isinstance(value.value, ast.Name)
            and value.value.id == "os"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            return node.slice.value
        return None
    # os.environ.get("X") / os.getenv("X")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        func = node.func
        is_environ_get = (
            func.attr in {"get", "setdefault", "pop"}
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "environ"
        )
        is_getenv = (
            func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        )
        if (is_environ_get or is_getenv) and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value
    return None


def _required_names() -> dict[str, str]:
    """Suelo mínimo: ``NOMBRE_ENV -> regla que lo exige`` (R1..R4)."""
    required: dict[str, str] = {}

    # R1 · el arranque aborta sin ellas.
    for name in _REQUIRED_ENV_VARS:
        required[name] = "R1 arranque (startup_checks._REQUIRED_ENV_VARS)"

    settings_names = _settings_env_names()
    for env_name, field_name in settings_names.items():
        field = Settings.model_fields[field_name]
        # R2 · credencial declarada como SecretStr.
        if field.annotation is SecretStr:
            required.setdefault(env_name, f"R2 secreto declarado (Settings.{field_name})")
        # R3 · el default apunta a esta máquina.
        default = field.default
        if isinstance(default, str) and ("localhost" in default or "127.0.0.1" in default):
            required.setdefault(
                env_name, f"R3 default local (Settings.{field_name}={default!r})"
            )

    # R4 · credencial leída a pelo con os.environ.
    for env_name, sites in _ast_env_names().items():
        if env_name.endswith("_PATH"):
            continue  # ruta a un fichero, no el secreto
        if _SECRET_NAME.search(env_name):
            required.setdefault(env_name, f"R4 secreto leído en {sites[0]}")

    return required


# =============================================================================
# Tests
# =============================================================================

def test_env_example_existe_y_es_legible() -> None:
    assert _ENV_EXAMPLE.is_file(), f"No existe {_ENV_EXAMPLE}"
    assert _ENV_EXAMPLE.read_text(encoding="utf-8").strip(), ".env.example está vacío"


def test_la_extraccion_no_es_vacia() -> None:
    """Antivacuidad: si cualquiera de las tres extracciones se rompiera y
    devolviera un conjunto vacío, el test principal pasaría sin comprobar nada.
    Aquí fijamos suelos holgados y un centinela conocido por cada fuente.
    """
    documented = _documented_names()
    settings_names = _settings_env_names()
    ast_names = _ast_env_names()

    assert len(documented) >= 40, f"`.env.example` documenta sólo {len(documented)} variables"
    assert "DATABASE_URL" in documented

    assert len(settings_names) >= 50, f"Settings expone sólo {len(settings_names)} campos"
    assert "ANTHROPIC_API_KEY" in settings_names

    assert len(ast_names) >= 30, f"El barrido AST sólo encontró {len(ast_names)} nombres"
    assert "FULKRO_AUTH_PRIVATE_KEY" in ast_names

    assert len(_required_names()) >= 20


def test_el_nombre_de_env_se_deriva_sin_prefijo() -> None:
    """`config.py` no declara ``env_prefix``: el campo ``minio_secret_key`` se
    lee de ``MINIO_SECRET_KEY``, NO de ``FULKRO_MINIO_SECRET_KEY``. Si alguien
    añade un prefijo, este test lo cantará y habrá que revisar `.env.example`
    (y `startup_checks._INSECURE_DEFAULTS`, que hoy vigila el nombre con
    prefijo y por tanto no vigila nada).
    """
    assert Settings.model_config.get("env_prefix", "") == ""
    settings_names = _settings_env_names()
    assert settings_names.get("MINIO_SECRET_KEY") == "minio_secret_key"
    assert "FULKRO_MINIO_SECRET_KEY" not in settings_names


def test_las_excepciones_siguen_siendo_necesarias() -> None:
    """Una excepción que ya no exceptúa nada es basura acumulada: si la variable
    dejó de ser alcanzada por las reglas, hay que borrarla de la lista.
    """
    required = _required_names()
    obsoletas = sorted(name for name in _EXCEPCIONES if name not in required)
    assert not obsoletas, (
        "Excepciones obsoletas en _EXCEPCIONES (ninguna regla las alcanza ya; "
        f"bórralas): {obsoletas}"
    )


def test_el_radar_retirado_no_reaparece() -> None:
    """Comprobación inversa ESTRECHA: el subsistema ENS Radar se retiró y sus
    variables no las lee nadie; que no vuelvan a colarse en la plantilla.
    """
    resucitadas = sorted(n for n in _documented_names() if n.startswith("ENS_RADAR_"))
    assert not resucitadas, (
        "`.env.example` documenta variables del ENS Radar RETIRADO "
        f"(ningún fichero de código las lee): {resucitadas}"
    )


def test_variables_de_arranque_y_credenciales_estan_documentadas() -> None:
    """El test que da nombre al fichero: el suelo mínimo R1..R4 ⊆ `.env.example`."""
    required = _required_names()
    documented = _documented_names()

    faltan = {
        name: motivo
        for name, motivo in sorted(required.items())
        if name not in documented and name not in _EXCEPCIONES
    }

    if faltan:
        detalle = "\n".join(f"  · {name:38s} ← {motivo}" for name, motivo in faltan.items())
        pytest.fail(
            f"{len(faltan)} variable(s) que el código lee NO están documentadas en "
            f"{_ENV_EXAMPLE.relative_to(_REPO_ROOT)}:\n{detalle}\n\n"
            "Añade una línea por cada una (activa `VAR=valor` o comentada "
            "`# VAR=valor`, ambas cuentan). Si de verdad no debe estar en la "
            "plantilla, añádela a _EXCEPCIONES en este mismo fichero CON su "
            "comentario explicando por qué."
        )
