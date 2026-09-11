"""Un test que dice probar HTTP y no llama a nadie deja la capa sin cubrir.

EL DEFECTO QUE ORIGINA ESTE ARNES
    ``tests/motors/m01_categorization/test_dimensions.py`` anuncia en su
    cabecera:

        Cubre:
          ...
          - HTTP endpoints (GET reader · PATCH admin)

    y no hacia UNA SOLA llamada HTTP: sus catorce tests entran por el service.
    El control de acceso de esos endpoints vivia en el endpoint, asi que no se
    ejecutaba nunca -- y ahi se quedo, durante meses, el fallo por el que Marcos
    recibia 403 en sus propias rutas (la rama de administracion leia dos
    atributos que no existen).

    La cabecera no es decoracion: es lo que lee quien decide si hace falta
    cobertura nueva. Una cabecera que promete una capa que nadie toca es peor
    que no tener test, porque apaga la pregunta.

COMO FUNCIONA
    Se marcan los ficheros cuya cabecera menciona HTTP, endpoint o ruta y que no
    usan cliente HTTP en el cuerpo. Salen 29 de 135. No todos mienten: en
    bastantes la palabra es incidental ("la ruta de conformidad", "rutas a un
    fichero") o la cabecera dice EXPLICITAMENTE que trabaja por debajo ("no HTTP
    client", "NO DB · NO HTTP"). Esos van a la lista de mencion incidental.

    Los que si prometen cobertura de endpoint sin tocarlo quedan en la otra
    lista, ABIERTOS con su promesa citada. Las dos listas estan CONGELADAS: un
    fichero nuevo que caiga en el barrido y no este declarado rompe el build, y
    quien lo anyada tiene que decidir a cual pertenece.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
TESTS = RAIZ / "backend" / "tests"

_MENCION = re.compile(r"\b(HTTP|endpoints?|ruta|rutas|API REST)\b", re.I)
_CLIENTE = re.compile(
    r"\b(async_client|client|httpx|TestClient|ASGITransport)\b"
)

# ── ABIERTOS · la cabecera promete una capa que el fichero no toca ──────
# Cada uno con la promesa citada. No estan justificados: estan medidos.
PROMETEN_HTTP_Y_NO_LO_TOCAN = {
    # "Tests integración RBAC per-endpoint" · el RBAC se comprueba leyendo
    # dependencias, no ejercitando rutas.
    "tests/auth/test_rbac_per_endpoint.py",
    # "23 admin endpoints ... ahora exigen Depends(require_owner)"
    "tests/motors/m16_onboarding/test_rbac_admin_endpoints.py",
    # "Endpoint GET /projects/{id}/action-plans · 404 NO existe + 200 con data"
    # -- dos codigos de estado que nadie pide.
    "tests/api/test_action_plans.py",
    # "Endpoint retorna {lead, stage_history, proposals, contract}"
    "tests/motors/m13_commercial/test_lead_detail_api.py",
    # "+ 5 cliente endpoints (questionnaire CRUD + drafts list + approve + comment)"
    "tests/motors/m19_risk/test_cluster_2_phase_2f_continuidad.py",
    # "Tests M21 Portal Cliente · auth + endpoints · single-user-RW"
    "tests/motors/m21_portal_cliente/test_portal_cliente_paso3.py",
    # "Endpoint GET /api/v1/projects/{id}/recent-activity retorna actividades"
    "tests/motors/m21_portal_cliente/test_recent_activity_api.py",
    # "SSE emit m02.magerit.updated dispatched on freeze_analysis endpoint"
    "tests/motors/m21_portal_cliente/test_m02_magerit_sync.py",
    # "All 5 endpoints respond consistently · project-scoped · idempotent"
    "tests/motors/m_cloud_connectors/test_cloud_integrations_cross_motor_consistency.py",
    # "RGPD cliente endpoints + services tests"
    "tests/motors/m_compliance/test_rgpd_endpoints.py",
    # "API status endpoint sanity" + "API manual trigger endpoint sanity"
    "tests/motors/m_compliance_monitor/test_service.py",
    # "the expected endpoints, so the motor stays covered"
    "tests/motors/m11_copiloto/test_m11_smoke.py",
}

# ── LEGITIMOS · la palabra sale, pero no hay promesa que incumplir ──────
MENCION_NO_ES_PROMESA = {
    # Dicen EXPLICITAMENTE que trabajan por debajo de HTTP.
    "tests/admin_settings/test_email_config.py",            # "(no HTTP client)"
    # Decia "Cubre: ... HTTP endpoints (GET reader · PATCH admin)" y era falso.
    # Ahora la cabecera dice que NO los cubre y donde esta la cobertura real:
    # por eso sigue mencionandolos, y por eso ya no es una promesa incumplida.
    "tests/motors/m01_categorization/test_dimensions.py",
    "tests/security/test_llm_prompt_injection.py",          # "NO DB · NO HTTP"
    "tests/agents/test_system_knowledge_behavior_llm.py",   # "bypass del rate-limit"
    "tests/motors/m21_portal_cliente/test_approve_plan.py",  # "como el endpoint real"
    # Analisis estatico SOBRE las rutas: su objeto son los endpoints, y por eso
    # los leen del codigo en vez de llamarlos.
    "tests/motors/m02_magerit/test_rutas_magerit_coinciden.py",
    "tests/scripts/test_puertas_en_cuerpo_se_cuentan.py",
    "tests/auth/test_getattr_no_lee_fantasmas.py",
    "tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py",
    # "ruta" en otro sentido: camino de negocio, ruta de fichero, ruta de
    # conformidad, familia de plantillas.
    "tests/integration/test_sim_alta.py",
    "tests/integration/test_sim_basica.py",
    "tests/test_env_example_completeness.py",
    "tests/motors/m27_conformity/test_bienio_una_sola_fuente.py",
    "tests/motors/m27_conformity/test_r26_distintivo.py",
    "tests/motors/m10_audit_sim/test_umbrales_con_cita.py",
    "tests/motors/m06_document_factory/test_sgsi_core_templates_render.py",
    # Narra el efecto de un defecto sobre un endpoint; prueba el service.
    "tests/api/test_client_compliance_summary_savepoint.py",
}


def _sospechosos() -> tuple[list[str], int]:
    marcados: list[str] = []
    con_mencion = 0
    for py in sorted(TESTS.rglob("test_*.py")):
        try:
            arbol = ast.parse(py.read_text("utf-8", errors="ignore"))
        except SyntaxError:  # pragma: no cover
            continue
        doc = ast.get_docstring(arbol) or ""
        if not _MENCION.search(doc):
            continue
        con_mencion += 1
        texto = py.read_text("utf-8", errors="ignore")
        cuerpo = texto[texto.index(doc) + len(doc):] if doc in texto else texto
        if not _CLIENTE.search(cuerpo):
            marcados.append(str(py.relative_to(RAIZ / "backend")))
    return marcados, con_mencion


def test_el_barrido_encuentra_ficheros():
    """Anti-vacuidad: sin ficheros marcados este arnes no mide nada."""
    marcados, con_mencion = _sospechosos()
    assert con_mencion > 100, f"solo {con_mencion} cabeceras mencionan HTTP"
    assert len(marcados) >= 20, f"solo {len(marcados)} marcados"


def test_ningun_fichero_nuevo_promete_una_capa_que_no_toca():
    marcados, _ = _sospechosos()
    declarados = PROMETEN_HTTP_Y_NO_LO_TOCAN | MENCION_NO_ES_PROMESA
    sin_declarar = sorted(set(marcados) - declarados)
    assert not sin_declarar, (
        "la cabecera de estos tests menciona HTTP/endpoint/ruta y el cuerpo no "
        "usa cliente HTTP. Decide a cual de las dos listas pertenece cada uno "
        "en backend/tests/scripts/test_tests_no_mienten_sobre_su_capa.py:\n  "
        + "\n  ".join(sin_declarar)
    )


def test_la_linea_base_no_tapa_ficheros_que_ya_no_existen():
    """Una lista congelada que nombra ficheros muertos afloja sola."""
    marcados, _ = _sospechosos()
    declarados = PROMETEN_HTTP_Y_NO_LO_TOCAN | MENCION_NO_ES_PROMESA
    sobran = sorted(declarados - set(marcados))
    assert not sobran, (
        "declarados en la linea base pero el barrido ya no los marca (o los "
        "arreglaron, o cambiaron de nombre): quitalos de la lista:\n  "
        + "\n  ".join(sobran)
    )
