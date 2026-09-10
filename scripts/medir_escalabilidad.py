#!/usr/bin/env python3
"""Inventario de lo que ata la aplicacion a UN proceso o a UN disco · D4.

Responde con datos, no con adjetivos, a las cuatro preguntas del bloque D4:

  1. escrituras a disco fuera de /tmp desde backend/app: ¿a MinIO o al sistema
     de ficheros del contenedor?
  2. las claves Ed25519: ¿de donde salen y que pasa si no estan?
  3. sesiones: ¿Redis o memoria del proceso?
  4. estado en proceso: cachés, singletons, cualquier cosa que suponga una sola
     instancia.

Uso:
    python3 scripts/medir_escalabilidad.py            # tabla legible
    python3 scripts/medir_escalabilidad.py --json     # para tratarlo

No necesita la aplicacion levantada: lee el codigo. La parte que SI necesita la
aplicacion en marcha (dos replicas de verdad) esta en
scripts/probar_dos_replicas.sh, y el resultado de ambas en
docs/adr/ADR-003-escalabilidad-horizontal.md.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "backend" / "app"

# ── 1 · escrituras a disco ──────────────────────────────────────────────────
# Se buscan las llamadas que escriben, no las menciones. La etiqueta dice lo que
# el comando mide: son SITIOS DE LLAMADA, no ejecuciones.
_ESCRITURAS = re.compile(
    r"\.write_bytes\(|\.write_text\(|open\([^)]*['\"](?:w|a|wb|ab)\b"
    r"|shutil\.(?:copy|copy2|move)\(|logging\.FileHandler\(|\.to_csv\(",
)
# Raices conocidas, en orden de especificidad.
_RAICES = (
    ("/tmp",              "/tmp (efimero · no cuenta)"),
    ("var/evidences",     "disco del contenedor · var/evidences"),
    ("var/quarantine",    "disco del contenedor · var/quarantine"),
    ("var/keys",          "disco del contenedor · var/keys  <-- CLAVES"),
    ("var/documents",     "disco del contenedor · var/documents"),
    ("var/",              "disco del contenedor · var/ (otros)"),
    ("Path.home()",       "disco del contenedor · HOME del usuario"),
)


def _sitios_de_escritura() -> list[dict]:
    salida = []
    for fichero in sorted(APP.rglob("*.py")):
        try:
            lineas = fichero.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        texto = "\n".join(lineas)
        for n, linea in enumerate(lineas, 1):
            if not _ESCRITURAS.search(linea):
                continue
            # Contexto: 25 lineas arriba + el fichero entero para las constantes.
            ventana = "\n".join(lineas[max(0, n - 26):n])
            destino = "sin clasificar"
            for aguja, etiqueta in _RAICES:
                if aguja in ventana or aguja in linea:
                    destino = etiqueta
                    break
            else:
                for aguja, etiqueta in _RAICES:
                    if aguja in texto:
                        destino = etiqueta + " (raiz declarada en el modulo)"
                        break
            salida.append({
                "fichero": str(fichero.relative_to(RAIZ)),
                "linea": n,
                "destino": destino,
                "codigo": linea.strip()[:90],
            })
    return salida


def _usa_minio() -> dict:
    """¿Hay alguna escritura que vaya de verdad a MinIO/S3?"""
    patron = re.compile(r"put_object\(|upload_fileobj\(|upload_file\(|\.Bucket\(")
    sitios = []
    for fichero in sorted(APP.rglob("*.py")):
        try:
            for n, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
                if patron.search(linea):
                    sitios.append(f"{fichero.relative_to(RAIZ)}:{n}")
        except OSError:
            continue
    return {"sitios_de_subida_a_objetos": sitios}


# ── 2 · claves Ed25519 ──────────────────────────────────────────────────────
def _claves() -> list[dict]:
    filas = []
    for var, quien, donde in (
        ("FULKRO_AUTH_PRIVATE_KEY", "sesion (cookie fulkro_session)", "entorno"),
        ("FULKRO_ML_PRIVATE_KEY", "enlaces magicos / portales", "entorno"),
        ("FULKRO_BACKUP_SIGNING_KEY", "firma de backups (M26)", "entorno"),
        ("FULKRO_M05_SIGNING_PRIVATE_KEY", "firma de documentos (M05)", "entorno o disco"),
        ("FULKRO_M06_SIGNING_PRIVATE_KEY", "document factory (M06)", "entorno o disco"),
        ("FULKRO_M07_SIGNING_PRIVATE_KEY", "firma de evidencias (M07)", "entorno o disco"),
    ):
        obligatoria = var in (RAIZ / "backend/app/startup_checks.py").read_text(
            encoding="utf-8")
        filas.append({
            "variable": var, "para": quien, "origen": donde,
            "el_arranque_aborta_si_falta": obligatoria,
        })
    return filas


# ── 3 · sesiones ────────────────────────────────────────────────────────────
def _sesiones() -> dict:
    csrf = (RAIZ / "backend/app/auth/csrf.py").read_text(encoding="utf-8")
    return {
        "mecanismo": "cookie firmada Ed25519 (JWT), sin estado en el servidor",
        "cookie": re.search(r'SESSION_COOKIE = "([^"]+)"', csrf).group(1),
        "guardada_en_redis": False,
        "guardada_en_memoria_del_proceso": False,
        "consecuencia": (
            "la sesion no ata a ninguna replica: la firma la valida cualquiera "
            "que tenga la MISMA FULKRO_AUTH_PRIVATE_KEY"
        ),
    }


# ── 4 · estado en proceso ───────────────────────────────────────────────────
def _estado_en_proceso() -> list[dict]:
    patron = re.compile(
        r"^_[A-Za-z0-9_]*\s*(?::[^=]+)?=\s*(?:\{\}|\[\]|defaultdict|deque|set\(\)|OrderedDict)",
    )
    filas = []
    for fichero in sorted(APP.rglob("*.py")):
        try:
            lineas = fichero.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for n, linea in enumerate(lineas, 1):
            if patron.match(linea):
                filas.append({
                    "fichero": str(fichero.relative_to(RAIZ)),
                    "linea": n,
                    "codigo": linea.strip()[:100],
                })
    return filas


def main() -> int:
    escrituras = _sitios_de_escritura()
    resumen = {}
    for e in escrituras:
        resumen[e["destino"]] = resumen.get(e["destino"], 0) + 1
    datos = {
        "1_escrituras_a_disco": {
            "sitios_de_llamada": len(escrituras),
            "por_destino": resumen,
            "detalle": escrituras,
            "objetos_minio_s3": _usa_minio(),
        },
        "2_claves_ed25519": _claves(),
        "3_sesiones": _sesiones(),
        "4_estado_en_proceso": _estado_en_proceso(),
    }
    if "--json" in sys.argv:
        print(json.dumps(datos, indent=2, ensure_ascii=False))
        return 0

    print("═" * 74)
    print(" 1 · ESCRITURAS A DISCO desde backend/app (sitios de llamada)")
    print("═" * 74)
    for destino, n in sorted(resumen.items(), key=lambda x: -x[1]):
        print(f"   {n:>4}  {destino}")
    print(f"   {len(escrituras):>4}  TOTAL")
    subidas = datos["1_escrituras_a_disco"]["objetos_minio_s3"]["sitios_de_subida_a_objetos"]
    print(f"\n   Subidas a almacenamiento de objetos (MinIO/S3): {len(subidas)}")
    for s in subidas[:10]:
        print(f"      {s}")

    print("\n" + "═" * 74)
    print(" 2 · CLAVES Ed25519")
    print("═" * 74)
    for f in datos["2_claves_ed25519"]:
        aborta = "sí" if f["el_arranque_aborta_si_falta"] else "NO"
        print(f"   {f['variable']:<34} {f['origen']:<16} aborta si falta: {aborta}")
        print(f"      para: {f['para']}")

    print("\n" + "═" * 74)
    print(" 3 · SESIONES")
    print("═" * 74)
    for k, v in datos["3_sesiones"].items():
        print(f"   {k}: {v}")

    print("\n" + "═" * 74)
    print(" 4 · ESTADO EN LA MEMORIA DEL PROCESO")
    print("═" * 74)
    print(f"   {len(datos['4_estado_en_proceso'])} estructuras mutables a nivel de módulo")
    for f in datos["4_estado_en_proceso"][:20]:
        print(f"      {f['fichero']}:{f['linea']}  {f['codigo']}")
    print("\n   La prueba que zanja el reparto entre réplicas:")
    print("      bash scripts/probar_dos_replicas.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
