"""N3 · una pregunta de auditoria no afirma un umbral numerico sin cita normativa.

EL DEFECTO
    `audit_questions.py` ponia en boca de la norma umbrales que la norma NO
    dice: MFA al 95 %, retencion de 6 meses y 2 anyos, estrategia 3-2-1,
    revision cada 12 meses, cobertura del 100 % de endpoints, cero criticos.
    Un cliente que lee "criterio: MFA universal (>=95% cobertura)" entiende que
    el RD 311/2022 exige ese 95 %. No lo exige. No aparece.

    Comprobado contra el PDF del BOE verificado en N0. Sobre op.exp.8, que es la
    medida de registro de actividad, lo que la norma dice es:

      "[op.exp.8.r3.1] En la documentacion de seguridad del sistema se deberan
       indicar los eventos de seguridad que seran auditados y el tiempo de
       retencion de los registros antes de ser eliminados."

    O sea: la organizacion DOCUMENTA su periodo. La norma no lo fija.

LAS DOS PERIODICIDADES QUE SI SON NORMATIVAS (y por eso se pueden citar)
    - Anexo I punto 1: "Anualmente, o siempre que se produzcan modificaciones
      significativas [...] debera re-evaluarse la categoria de seguridad".
    - Anexo III punto 1.d: "Que se ha realizado un analisis de riesgos, con
      revision y aprobacion anual".

LA REGLA QUE IMPONE ESTE TEST
    Si el texto de una pregunta o de su criterio afirma un umbral numerico,
    tiene que llevar al lado una de estas dos cosas:
      a) una cita normativa -- codigo de medida entre corchetes, "RD 311/2022",
         "Anexo I/II/III" --, o
      b) la marca explicita de que es criterio propio: "recomendacion FULKRO".
    Lo que no se admite es el numero a secas, que es lo que habia.
"""
from __future__ import annotations

import re

from backend.app.motors.m10_audit_sim.audit_questions import AUDIT_QUESTIONS

# Umbrales numericos: porcentajes, plazos, periodicidades, "3-2-1", "cero X".
UMBRAL = re.compile(
    r"(\d+\s?%"
    r"|\b\d+\s*(?:mes|meses|año|años|anyo|anyos)\b"
    r"|\b\d+-\d+-\d+\b"
    r"|\banual(?:es|mente)?\b"
    r"|\bcero\s+\w+)",
    re.IGNORECASE,
)

# Cita normativa aceptable, o marca de criterio propio.
CITA = re.compile(
    r"(\[[a-z]{2,3}(?:\.[a-z]+)?\.\d+"          # [op.exp.8], [org.1]
    r"|RD\s*311/2022"
    r"|Anexo\s+(?:I|II|III|IV)\b"
    r"|recomendaci[oó]n\s+FULKRO)",
    re.IGNORECASE,
)

CAMPOS = ("pregunta", "criterio")


def test_ningun_umbral_numerico_sin_cita_ni_marca():
    huerfanos = []
    for codigo, q in sorted(AUDIT_QUESTIONS.items()):
        for campo in CAMPOS:
            texto = q.get(campo) or ""
            umbrales = UMBRAL.findall(texto)
            if umbrales and not CITA.search(texto):
                huerfanos.append(
                    f"{codigo}.{campo}: umbral {sorted(set(u.strip() for u in umbrales))} "
                    f"sin cita ni marca -> {texto[:110]}"
                )
    assert not huerfanos, (
        "umbrales numericos puestos en boca de la norma sin respaldo:\n"
        + "\n".join(huerfanos)
    )


def test_la_norma_no_menciona_PILAR_ni_MAGERIT_y_las_preguntas_tampoco_los_exigen():
    """Cero apariciones de ambos en el RD 311/2022 (verificado sobre el PDF).

    op.pl.1 exige para ALTA "un analisis formal, usando un lenguaje especifico,
    con un fundamento matematico reconocido internacionalmente" (refuerzo R2).
    PILAR es UNA herramienta que lo satisface y MAGERIT UNA metodologia; ninguna
    de las dos es obligatoria, asi que no se pueden exigir como si lo fueran.
    """
    exigencias = []
    for codigo, q in sorted(AUDIT_QUESTIONS.items()):
        for campo in CAMPOS:
            texto = (q.get(campo) or "")
            bajo = texto.lower()
            for herramienta in ("pilar", "magerit"):
                if herramienta not in bajo:
                    continue
                # Mencionarlas como ejemplo es legitimo; EXIGIRLAS no.
                if re.search(r"(tiene el export|export\s+pilar|metodolog[ií]a\s+magerit"
                             r"|con\s+magerit|obligatori)", bajo):
                    exigencias.append(f"{codigo}.{campo}: {texto[:120]}")
    assert not exigencias, (
        "se exige una herramienta/metodologia que la norma no menciona nunca:\n"
        + "\n".join(exigencias)
    )


def test_los_codigos_de_las_preguntas_son_los_del_rd_311_2022():
    """Sin fosiles del RD 3/2010 (op.exp.11, op.acc.7) colados como medida."""
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[2] / "fixtures/anexo2_boe_verificado.json"
    boe = {m["codigo"] for m in json.loads(fixture.read_text("utf-8"))["medidas"]}
    intrusos = sorted(set(AUDIT_QUESTIONS) - boe)
    assert not intrusos, f"codigos que no existen en el Anexo II: {intrusos}"
