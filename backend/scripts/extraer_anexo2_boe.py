"""Extrae la tabla resumen del ANEXO II del RD 311/2022 desde el PDF del BOE.

Por que existe: el catalogo de medidas de `m03_dda/anexo2_rd311_2022.py` se dio
por contrastado contra la norma sin que nadie lo contrastara nunca contra el
texto oficial. Este script hace ese contraste reproducible.

Fuente (texto consolidado, PDF, NO raspado de HTML):
  https://www.boe.es/buscar/pdf/2022/BOE-A-2022-7191-consolidado.pdf

El PDF NO se versiona: se versiona su sha256 y el fixture que sale de aqui.
El texto del BOE es reproducible libremente -- art. 13 LPI excluye de propiedad
intelectual las disposiciones legales y sus correspondientes textos oficiales.

Uso:
    curl -sSL -o rd311.pdf \
      https://www.boe.es/buscar/pdf/2022/BOE-A-2022-7191-consolidado.pdf
    python backend/scripts/extraer_anexo2_boe.py rd311.pdf

Escribe backend/tests/fixtures/anexo2_boe_verificado.json y valida el PDF antes
de leerlo.

UNA TRAMPA QUE COSTO UN RATO, ANOTADA PARA EL SIGUIENTE
    `str.splitlines()` parte tambien por el salto de pagina (\\x0c) que mete
    pdftotext, asi que numera distinto que `grep -n` y desplaza cualquier corte
    por numero de linea. Aqui se usa `split("\\n")`. Una tabla cortada en
    silencio es exactamente el fallo del que este bloque desconfia.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# sha256 del PDF consolidado con el que se genero el fixture versionado.
# Si el BOE publica una consolidacion nueva, este hash cambia: NO es un fallo,
# es la senal de que hay que regenerar el fixture y volver a mirar el diferencial.
SHA256_CONOCIDO = "07a74608dce3a146890f444c73ef8f2ee04f49c101114e2e2642941e53a92211"

MARCADORES = ["ANEXO II", "org.1", "op.pl.1", "mp.s.2"]
DIMENSIONES = {"C": "confidencialidad", "I": "integridad", "T": "trazabilidad",
               "A": "autenticidad", "D": "disponibilidad"}

RE_CODIGO = re.compile(r"^\s*((?:org|op|mp)(?:\.[a-z]+)?\.\d+)\s+(.*)$")
# La 3a columna es "Categoria" o una combinacion de iniciales CITAD.
RE_EJE = re.compile(r"\s(Categoría|[CITAD]{1,5})\s")


def valida_pdf(ruta: Path) -> dict:
    """Comprueba que el PDF llego entero ANTES de extraer nada de el."""
    fallos: list[str] = []
    datos: dict = {}

    crudo = ruta.read_bytes()
    datos["sha256"] = hashlib.sha256(crudo).hexdigest()
    datos["bytes"] = len(crudo)

    if not crudo.startswith(b"%PDF-"):
        fallos.append("no empieza por %PDF-: no es un PDF")

    info = subprocess.run(["pdfinfo", str(ruta)], capture_output=True, text=True)
    if info.returncode != 0:
        fallos.append("pdfinfo no puede leerlo")
    for linea in info.stdout.splitlines():
        if linea.startswith("Pages:"):
            datos["paginas"] = int(linea.split()[1])
        if linea.startswith("Title:"):
            datos["titulo"] = linea.split(":", 1)[1].strip()
        if linea.startswith("Subject:"):
            datos["asunto"] = linea.split(":", 1)[1].strip()

    texto = subprocess.run(["pdftotext", "-layout", str(ruta), "-"],
                           capture_output=True, text=True).stdout
    datos["caracteres_texto"] = len(texto)
    # Un escaneo sin OCR da una capa de texto practicamente vacia.
    if len(texto) < 50_000:
        fallos.append(f"capa de texto de solo {len(texto)} caracteres: "
                      "parece un escaneo, no un PDF con texto")

    datos["marcadores"] = {}
    for m in MARCADORES:
        n = texto.count(m)
        datos["marcadores"][m] = n
        if n == 0:
            fallos.append(f"no aparece literalmente {m!r}")

    datos["fallos"] = fallos
    return datos, texto


def extrae_tabla(texto: str) -> list[dict]:
    """Parsea la tabla resumen del punto 4 del Anexo II.

    Devuelve por medida: el eje (categoria o dimension(es)) y si aplica en cada
    nivel. Convencion de la propia norma (punto 5.c): "n.a." = no exigible;
    cualquier otra celda ("aplica", "+ R1", "+ [R1 o R2]") = la medida aplica.
    """
    lineas = texto.split("\n")  # NO splitlines(): ver docstring del modulo
    ini = fin = None
    for i, l in enumerate(lineas):
        if ini is None and re.match(r"^org\.1\s", l):
            ini = i
        if ini is not None and re.match(r"^mp\.s\.4\s", l):
            fin = i
            break
    if ini is None or fin is None:
        raise SystemExit("ERROR: no se localizan los limites de la tabla "
                         "(org.1 ... mp.s.4). No se inventa nada: se para.")

    bloque = lineas[ini:fin + 1]
    filas = []
    for idx, l in enumerate(bloque):
        m = RE_CODIGO.match(l)
        if not m:
            continue
        codigo, resto = m.group(1), m.group(2)
        eje = RE_EJE.search(" " + resto + " ")
        if not eje:
            raise SystemExit(f"ERROR: no se reconoce el eje de {codigo}. Se para.")
        bruto = eje.group(1)
        cola = (" " + resto + " ")[eje.end():]
        celdas = [c.strip() for c in re.split(r"\s{2,}", cola) if c.strip()]

        if len(celdas) != 3:
            # op.acc.5 y op.acc.6 parten sus celdas en varias lineas del PDF.
            # No se adivinan: se recomponen con las lineas de continuacion
            # contiguas (las que no empiezan por codigo) y se exige que de ese
            # bloque se pueda decidir el booleano sin ambiguedad.
            ctx = [l]
            for j in (idx - 1, idx + 1, idx + 2):
                if 0 <= j < len(bloque) and not RE_CODIGO.match(bloque[j]):
                    ctx.append(bloque[j])
            junto = " ".join(ctx)
            if "n.a." in junto:
                raise SystemExit(
                    f"ERROR: {codigo} parte sus celdas en varias lineas Y alguna "
                    "dice n.a.: el parseo por columnas no es fiable aqui. Se para "
                    "en vez de adivinar.")
            # Ninguna celda es n.a. => la medida aplica en los tres niveles.
            aplica = [True, True, True]
            multilinea = True
        else:
            aplica = [c != "n.a." for c in celdas]
            multilinea = False

        fila = {
            "codigo": codigo,
            "aplica_basica": aplica[0],
            "aplica_media": aplica[1],
            "aplica_alta": aplica[2],
            "celdas_boe": celdas if not multilinea else "multilinea en el PDF",
        }
        if bruto == "Categoría":
            fila["eje"] = "categoria"
            fila["dimensiones"] = []
        else:
            fila["eje"] = "dimension"
            fila["dimensiones"] = sorted(DIMENSIONES[c] for c in bruto)
            fila["dimensiones_iniciales"] = bruto
        filas.append(fila)
    return filas


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ruta = Path(sys.argv[1])
    datos, texto = valida_pdf(ruta)

    print("== validacion del PDF ==")
    for k in ("sha256", "bytes", "paginas", "caracteres_texto", "titulo", "asunto"):
        print(f"  {k:18s} {datos.get(k)}")
    print(f"  marcadores         {datos['marcadores']}")
    if datos["fallos"]:
        print("\nFALLA la validacion. No se extrae nada:")
        for f in datos["fallos"]:
            print("  -", f)
        return 1
    if datos["sha256"] != SHA256_CONOCIDO:
        print(f"\n  AVISO: sha256 distinto del que genero el fixture "
              f"({SHA256_CONOCIDO}).\n  Puede ser una consolidacion nueva del BOE. "
              "Revisa el diferencial antes de dar por bueno el fixture.")

    filas = extrae_tabla(texto)
    por_eje = {"categoria": 0, "dimension": 0}
    for f in filas:
        por_eje[f["eje"]] += 1
    print("\n== extraccion ==")
    print(f"  medidas: {len(filas)}  (por categoria {por_eje['categoria']} · "
          f"por dimension {por_eje['dimension']})")
    print(f"  aplican BASICA {sum(f['aplica_basica'] for f in filas)} · "
          f"MEDIA {sum(f['aplica_media'] for f in filas)} · "
          f"ALTA {sum(f['aplica_alta'] for f in filas)}")

    salida = {
        "_fuente": "https://www.boe.es/buscar/pdf/2022/BOE-A-2022-7191-consolidado.pdf",
        "_sha256_pdf": datos["sha256"],
        "_asunto": datos.get("asunto"),
        "_paginas": datos.get("paginas"),
        "_generado_por": "backend/scripts/extraer_anexo2_boe.py",
        "_nota_licencia": "Art. 13 LPI: las disposiciones legales y sus textos "
                          "oficiales no son objeto de propiedad intelectual.",
        "total_medidas": len(filas),
        "medidas": filas,
    }
    destino = Path(__file__).resolve().parents[1] / "tests/fixtures/anexo2_boe_verificado.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"  escrito: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
