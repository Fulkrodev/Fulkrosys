"""O2 · el acta E-012 no inventa un nivel para una dimension no afectada.

EL FLECO, encontrado recorriendo el ciclo por navegador
    Un proyecto MEDIA con la DISPONIBILIDAD no afectada producia un acta E-012
    en PDF y DOCX que declaraba **"Disponibilidad (D): MEDIO"**. Un documento
    firmado con un dato que nadie decidio y que la norma prohibe: el Anexo I
    punto 3 dice que una dimension no afectada NO se adscribe a ningun nivel.

LA CADENA, dos eslabones
    1. `acta_e012_generator.py` hacia `_max_level(vals) or ""`. `_max_level`
       rankea contra {'BAJO':1,'MEDIO':2,'ALTO':3}, asi que tanto None como el
       literal 'NO_AFECTADA' caen a rango 0 y devuelven None -> cadena vacia.
       (Guardar NO_AFECTADA explicito en la base NO lo arreglaba: el problema es
       que `_max_level` no conoce la cuarta opcion del Anexo I.)
    2. La plantilla imprimia `{{ dims.X if dims.X else 'MEDIO' }}`. En Jinja la
       cadena vacia es falsa, asi que salia MEDIO. Cinco veces, una por
       dimension.

LA CAUSA DE FONDO, que es la que se arregla para que no vuelva
    Los TRES formatos del MISMO documento corrian por DOS implementaciones de la
    regla del maximo del Anexo I:
      · el .json usaba `CategorizationService.compute_for_system`, que filtra
        por `ImpactLevel.esta_afectada` -> decia NO_AFECTADA, correcto.
      · el .pdf y el .docx usaban `_max_level` -> decian MEDIO.
    El mismo acta, tres ficheros, dos verdades. Es el patron de O1 otra vez, y
    esta vez sobre el documento que se firma.

Y LA PLANTILLA HERMANA YA LO HACIA BIEN
    `E155_documento_alcance_sgsi.md` imprime `else '—'` en esas mismas cinco
    filas. E-012 era la unica que inventaba un nivel.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
M06 = RAIZ / "backend/app/motors/m06_document_factory"
PLANTILLA_E012 = (
    M06 / "templates/deliverables"
    / "E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad.md"
)


def test_la_plantilla_no_inventa_un_nivel_por_defecto():
    texto = PLANTILLA_E012.read_text("utf-8")
    inventados = re.findall(r"else\s+'(BAJO|MEDIO|ALTO)'", texto)
    assert not inventados, (
        "la plantilla del acta E-012 rellena con un nivel inventado cuando no "
        f"hay dato: {inventados}. Un acta firmada no puede declarar un nivel "
        "que nadie decidio (RD 311/2022 Anexo I punto 3)."
    )


def test_ninguna_plantilla_de_entregable_inventa_un_nivel():
    """El mismo patron, barrido a todas las plantillas."""
    plantillas = list((M06 / "templates").rglob("*.md"))
    assert len(plantillas) > 20, f"solo {len(plantillas)} plantillas: ruta mal"
    culpables = []
    for p in plantillas:
        for i, linea in enumerate(p.read_text("utf-8", errors="ignore").splitlines(), 1):
            if re.search(r"else\s+'(BAJO|MEDIO|ALTO)'", linea):
                culpables.append(f"{p.relative_to(RAIZ)}:{i}: {linea.strip()[:88]}")
    assert not culpables, (
        "plantillas que inventan un nivel de dimension:\n" + "\n".join(culpables)
    )


def test_el_generador_dice_no_afectada_en_vez_de_callar():
    """`_max_level(...) or ""` convertia la ausencia en cadena vacia."""
    fuente = (M06 / "acta_e012_generator.py").read_text("utf-8")
    assert '_max_level(vals) or ""' not in fuente, (
        "el generador sigue convirtiendo 'no afectada' en cadena vacia, que es "
        "lo que dispara el valor inventado de la plantilla"
    )
    assert "NO_AFECTADA" in fuente, (
        "el generador tiene que nombrar explicitamente la cuarta opcion del "
        "Anexo I, no dejarla caer al else de la plantilla"
    )


def test_max_level_conoce_la_cuarta_opcion():
    """El literal 'NO_AFECTADA' tenia que dejar de caer a rango 0 en silencio."""
    from backend.app.motors.m06_document_factory.alcance_generator import _max_level

    # Sin ninguna dimension afectada no hay nivel: eso esta bien.
    assert _max_level([None]) is None
    assert _max_level(["NO_AFECTADA"]) is None
    # Pero una afectada manda sobre las no afectadas.
    assert _max_level([None, "MEDIO"]) == "MEDIO"
    assert _max_level(["NO_AFECTADA", "BAJO"]) == "BAJO"
