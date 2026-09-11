"""Tabla autoritativa del Anexo II del RD 311/2022 (ENS) — fuente única de verdad.

Transcrita LITERALMENTE de la tabla oficial del BOE-A-2022-7191 (Núm. 106,
miércoles 4 de mayo de 2022, págs. 61742-61745), columnas "Categoría de
seguridad del sistema: BÁSICA / MEDIA / ALTA".

Convención de aplicabilidad: una medida "aplica" en un nivel si su celda en la
tabla del BOE NO es "n.a." (esto incluye las celdas "+ [R...]", que aplican la
medida con refuerzo). Los refuerzos concretos (R1, R2, ...) se modelan aparte en
``ens_reinforcements``; aquí sólo se captura el booleano aplica/no-aplica por nivel.

Totales oficiales: 73 medidas (org 4 · op 33 · mp 36).
Por nivel (aplica = celda ≠ n.a.): BÁSICA 52 · MEDIA 68 · ALTA 73.

Usado como (1) referencia de verificación/guardia en tests y (2) corrección de
``ens_measures`` cuando el catálogo derivó a numeración/aplicabilidad RD 3/2010.
NO citar de memoria: verificado contra el BOE el 2026-06-07.
"""
from __future__ import annotations

# codigo -> (nombre_oficial_RD311_2022, aplica_basica, aplica_media, aplica_alta)
ANEXO_II_RD311: dict[str, tuple[str, bool, bool, bool]] = {
    # --- Marco organizativo [org] (4) ---
    "org.1": ("Política de seguridad", True, True, True),
    "org.2": ("Normativa de seguridad", True, True, True),
    "org.3": ("Procedimientos de seguridad", True, True, True),
    "org.4": ("Proceso de autorización", True, True, True),
    # --- Marco operacional [op] (33) ---
    # op.pl Planificación (5)
    "op.pl.1": ("Análisis de riesgos", True, True, True),
    "op.pl.2": ("Arquitectura de Seguridad", True, True, True),
    "op.pl.3": ("Adquisición de nuevos componentes", True, True, True),
    "op.pl.4": ("Dimensionamiento/gestión de la capacidad", True, True, True),
    "op.pl.5": ("Componentes certificados", False, True, True),
    # op.acc Control de acceso (6)
    "op.acc.1": ("Identificación", True, True, True),
    "op.acc.2": ("Requisitos de acceso", True, True, True),
    "op.acc.3": ("Segregación de funciones y tareas", False, True, True),
    "op.acc.4": ("Proceso de gestión de derechos de acceso", True, True, True),
    "op.acc.5": ("Mecanismo de autenticación (usuarios externos)", True, True, True),
    "op.acc.6": ("Mecanismo de autenticación (usuarios de la organización)", True, True, True),
    # op.exp Explotación (10)
    "op.exp.1": ("Inventario de activos", True, True, True),
    "op.exp.2": ("Configuración de seguridad", True, True, True),
    "op.exp.3": ("Gestión de la configuración de seguridad", True, True, True),
    "op.exp.4": ("Mantenimiento y actualizaciones de seguridad", True, True, True),
    "op.exp.5": ("Gestión de cambios", False, True, True),
    "op.exp.6": ("Protección frente a código dañino", True, True, True),
    "op.exp.7": ("Gestión de incidentes", True, True, True),
    "op.exp.8": ("Registro de la actividad", True, True, True),
    "op.exp.9": ("Registro de la gestión de incidentes", True, True, True),
    "op.exp.10": ("Protección de claves criptográficas", True, True, True),
    # op.ext Recursos externos (4)
    "op.ext.1": ("Contratación y acuerdos de nivel de servicio", False, True, True),
    "op.ext.2": ("Gestión diaria", False, True, True),
    "op.ext.3": ("Protección de la cadena de suministro", False, False, True),
    "op.ext.4": ("Interconexión de sistemas", False, True, True),
    # op.nub Servicios en la nube (1)
    "op.nub.1": ("Protección de servicios en la nube", True, True, True),
    # op.cont Continuidad del servicio (4)
    "op.cont.1": ("Análisis de impacto", False, True, True),
    "op.cont.2": ("Plan de continuidad", False, False, True),
    "op.cont.3": ("Pruebas periódicas", False, False, True),
    "op.cont.4": ("Medios alternativos", False, False, True),
    # op.mon Monitorización del sistema (3)
    "op.mon.1": ("Detección de intrusión", True, True, True),
    "op.mon.2": ("Sistema de métricas", True, True, True),
    "op.mon.3": ("Vigilancia", True, True, True),
    # --- Medidas de protección [mp] (36) ---
    # mp.if Protección de las instalaciones e infraestructuras (7)
    "mp.if.1": ("Áreas separadas y con control de acceso", True, True, True),
    "mp.if.2": ("Identificación de las personas", True, True, True),
    "mp.if.3": ("Acondicionamiento de los locales", True, True, True),
    "mp.if.4": ("Energía eléctrica", True, True, True),
    "mp.if.5": ("Protección frente a incendios", True, True, True),
    "mp.if.6": ("Protección frente a inundaciones", False, True, True),
    "mp.if.7": ("Registro de entrada y salida de equipamiento", True, True, True),
    # mp.per Gestión del personal (4)
    "mp.per.1": ("Caracterización del puesto de trabajo", False, True, True),
    "mp.per.2": ("Deberes y obligaciones", True, True, True),
    "mp.per.3": ("Concienciación", True, True, True),
    "mp.per.4": ("Formación", True, True, True),
    # mp.eq Protección de los equipos (4)
    "mp.eq.1": ("Puesto de trabajo despejado", True, True, True),
    "mp.eq.2": ("Bloqueo de puesto de trabajo", False, True, True),
    "mp.eq.3": ("Protección de dispositivos portátiles", True, True, True),
    "mp.eq.4": ("Otros dispositivos conectados a la red", True, True, True),
    # mp.com Protección de las comunicaciones (4)
    "mp.com.1": ("Perímetro seguro", True, True, True),
    "mp.com.2": ("Protección de la confidencialidad", True, True, True),
    "mp.com.3": ("Protección de la integridad y de la autenticidad", True, True, True),
    "mp.com.4": ("Separación de flujos de información en la red", False, True, True),
    # mp.si Protección de los soportes de información (5)
    "mp.si.1": ("Marcado de soportes", False, True, True),
    "mp.si.2": ("Criptografía", False, True, True),
    "mp.si.3": ("Custodia", True, True, True),
    "mp.si.4": ("Transporte", True, True, True),
    "mp.si.5": ("Borrado y destrucción", True, True, True),
    # mp.sw Protección de las aplicaciones informáticas (2)
    "mp.sw.1": ("Desarrollo de aplicaciones", False, True, True),
    "mp.sw.2": ("Aceptación y puesta en servicio", True, True, True),
    # mp.info Protección de la información (6)
    "mp.info.1": ("Datos personales", True, True, True),
    "mp.info.2": ("Calificación de la información", False, True, True),
    "mp.info.3": ("Firma electrónica", True, True, True),
    "mp.info.4": ("Sellos de tiempo", False, False, True),
    "mp.info.5": ("Limpieza de documentos", True, True, True),
    "mp.info.6": ("Copias de seguridad", True, True, True),
    # mp.s Protección de los servicios (4)
    "mp.s.1": ("Protección del correo electrónico", True, True, True),
    "mp.s.2": ("Protección de servicios y aplicaciones web", True, True, True),
    "mp.s.3": ("Protección de la navegación web", True, True, True),
    "mp.s.4": ("Protección frente a denegación de servicio", False, True, True),
}

# Totales oficiales (invariantes de guardia)
TOTAL_MEDIDAS = 73
APLICA_BASICA = 52
APLICA_MEDIA = 68
APLICA_ALTA = 73


def applicability_counts() -> tuple[int, int, int]:
    """(básica, media, alta) según la tabla autoritativa."""
    b = sum(1 for _, ab, _, _ in ANEXO_II_RD311.values() if ab)
    m = sum(1 for _, _, am, _ in ANEXO_II_RD311.values() if am)
    a = sum(1 for _, _, _, aa in ANEXO_II_RD311.values() if aa)
    return b, m, a


def _norm(s: str) -> str:
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def resolve_entries(yaml_measures: list[dict]) -> dict[str, dict]:
    """Construye las 73 entradas canónicas RD 311/2022 corrigiendo deriva RD 3/2010.

    Nombre y aplicabilidad por nivel salen de la tabla autoritativa (BOE). La
    descripción se toma de ``yaml_measures`` casando por NOMBRE (no por código),
    lo que resuelve automáticamente el desfase de numeración de mp.info y la
    medida op.exp.10 "Protección de claves criptográficas" (que el catálogo
    RD 3/2010 numeraba como op.exp.11).

    Devuelve ``{codigo: {nombre, descripcion, aplica_basica, aplica_media,
    aplica_alta}}`` para las 73 medidas. La descripción cae a "" si no hay
    coincidencia por nombre (no debería ocurrir con el catálogo actual).
    """
    by_name: dict[str, dict] = {}
    by_code: dict[str, dict] = {}
    for m in yaml_measures:
        by_code[m.get("codigo", "")] = m
        by_name.setdefault(_norm(m.get("nombre", "")), m)

    out: dict[str, dict] = {}
    for codigo, (nombre, ab, am, aa) in ANEXO_II_RD311.items():
        src = by_name.get(_norm(nombre)) or by_code.get(codigo) or {}
        out[codigo] = {
            "nombre": nombre,
            "descripcion": src.get("descripcion", "") or "",
            "aplica_basica": ab,
            "aplica_media": am,
            "aplica_alta": aa,
        }
    return out


# ── Eje de aplicabilidad (3ª columna de la tabla del Anexo II) ────────────
# codigo -> (eje, iniciales de dimension)
#   eje "categoria"  -> la medida se exige por la CATEGORIA del sistema.
#   eje "dimension"  -> se exige por el NIVEL de las dimensiones que se listan.
#
# Generado desde backend/tests/fixtures/anexo2_boe_verificado.json, que sale del
# PDF del BOE (ver backend/scripts/extraer_anexo2_boe.py y N0). NO se escribe a
# mano: test_no_afectada_y_aplicabilidad.py lo vuelve a contrastar contra el
# fixture, asi que cualquier edicion manual que se desvie falla.
#
# Esta pieza FALTABA. El catalogo traia aplica/no-aplica por nivel pero no el
# eje, que es justo lo que hace falta para no adscribir una dimension no
# afectada a ningun nivel (Anexo I, punto 3).
EJE_Y_DIMENSIONES: dict[str, tuple[str, str]] = {
    "org.1": ("categoria", ""),
    "org.2": ("categoria", ""),
    "org.3": ("categoria", ""),
    "org.4": ("categoria", ""),
    "op.pl.1": ("categoria", ""),
    "op.pl.2": ("categoria", ""),
    "op.pl.3": ("categoria", ""),
    "op.pl.4": ("dimension", "D"),
    "op.pl.5": ("categoria", ""),
    "op.acc.1": ("dimension", "TA"),
    "op.acc.2": ("dimension", "CITA"),
    "op.acc.3": ("dimension", "CITA"),
    "op.acc.4": ("dimension", "CITA"),
    "op.acc.5": ("dimension", "CITA"),
    "op.acc.6": ("dimension", "CITA"),
    "op.exp.1": ("categoria", ""),
    "op.exp.2": ("categoria", ""),
    "op.exp.3": ("categoria", ""),
    "op.exp.4": ("categoria", ""),
    "op.exp.5": ("categoria", ""),
    "op.exp.6": ("categoria", ""),
    "op.exp.7": ("categoria", ""),
    "op.exp.8": ("dimension", "T"),
    "op.exp.9": ("categoria", ""),
    "op.exp.10": ("categoria", ""),
    "op.ext.1": ("categoria", ""),
    "op.ext.2": ("categoria", ""),
    "op.ext.3": ("categoria", ""),
    "op.ext.4": ("categoria", ""),
    "op.nub.1": ("categoria", ""),
    "op.cont.1": ("dimension", "D"),
    "op.cont.2": ("dimension", "D"),
    "op.cont.3": ("dimension", "D"),
    "op.cont.4": ("dimension", "D"),
    "op.mon.1": ("categoria", ""),
    "op.mon.2": ("categoria", ""),
    "op.mon.3": ("categoria", ""),
    "mp.if.1": ("categoria", ""),
    "mp.if.2": ("categoria", ""),
    "mp.if.3": ("categoria", ""),
    "mp.if.4": ("dimension", "D"),
    "mp.if.5": ("dimension", "D"),
    "mp.if.6": ("dimension", "D"),
    "mp.if.7": ("categoria", ""),
    "mp.per.1": ("categoria", ""),
    "mp.per.2": ("categoria", ""),
    "mp.per.3": ("categoria", ""),
    "mp.per.4": ("categoria", ""),
    "mp.eq.1": ("categoria", ""),
    "mp.eq.2": ("dimension", "A"),
    "mp.eq.3": ("categoria", ""),
    "mp.eq.4": ("dimension", "C"),
    "mp.com.1": ("categoria", ""),
    "mp.com.2": ("dimension", "C"),
    "mp.com.3": ("dimension", "IA"),
    "mp.com.4": ("categoria", ""),
    "mp.si.1": ("dimension", "C"),
    "mp.si.2": ("dimension", "CI"),
    "mp.si.3": ("categoria", ""),
    "mp.si.4": ("categoria", ""),
    "mp.si.5": ("dimension", "C"),
    "mp.sw.1": ("categoria", ""),
    "mp.sw.2": ("categoria", ""),
    "mp.info.1": ("categoria", ""),
    "mp.info.2": ("dimension", "C"),
    "mp.info.3": ("dimension", "IA"),
    "mp.info.4": ("dimension", "T"),
    "mp.info.5": ("dimension", "C"),
    "mp.info.6": ("dimension", "D"),
    "mp.s.1": ("categoria", ""),
    "mp.s.2": ("categoria", ""),
    "mp.s.3": ("categoria", ""),
    "mp.s.4": ("dimension", "D"),
}

# Las 28 que el Anexo II indexa por dimension, y las 45 por categoria.
MEDIDAS_POR_DIMENSION = tuple(
    c for c, (eje, _) in EJE_Y_DIMENSIONES.items() if eje == "dimension"
)
MEDIDAS_POR_CATEGORIA = tuple(
    c for c, (eje, _) in EJE_Y_DIMENSIONES.items() if eje == "categoria"
)
