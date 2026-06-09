"""M8 v5.1 — Mapper OpenVAS NVT family + severity -> medidas ENS Anexo II.

OpenVAS reporta findings por NVT (Network Vulnerability Test). Cada NVT
pertenece a una familia (Web Servers, Databases, SSL and TLS, Windows,
etc.) y trae CVSS base + threat level (High/Medium/Low/Log).

Estrategia de mapeo en 3 capas (se consolidan uniendo medidas):
  1. Familia NVT      -> medidas ENS principales (13 familias mapeadas).
  2. NVT OID o nombre -> overrides especificos (para CVE criticos).
  3. Severity CVSS    -> medidas transversales (parches, logs, response).

La consolidacion es union (set). Un finding SSL/TLS high severity con CVE
critico mapea a mp.com.2 + mp.com.3 (familia) + op.exp.4 (mantenimiento
critico por CVSS >= 7.0) + op.exp.3 (gestion cambios/parches).
"""
from __future__ import annotations


# ══════════════════════════════════════════════════════════════════
# Mapping 1: familia NVT -> medidas ENS
# ══════════════════════════════════════════════════════════════════

FAMILY_TO_ENS: dict[str, list[str]] = {
    # Web / aplicacion
    "web servers": ["mp.sw.1", "mp.sw.2"],
    "web application abuses": ["mp.sw.2", "mp.s.2"],
    # BBDD
    "databases": ["mp.info.2", "mp.info.3"],
    # Windows
    "windows": ["op.exp.3", "op.exp.4"],
    "windows : microsoft bulletins": ["op.exp.3", "op.exp.4"],
    # General / multi-host
    "general": ["op.exp.2"],
    "service detection": ["op.exp.2"],
    # SSH y servicios de gestion
    "gain a shell remotely": ["op.acc.5", "op.acc.6"],
    "denial of service": ["mp.eq.3", "op.cont.2"],
    # Crypto
    "ssl and tls": ["mp.com.2", "mp.com.3"],
    "gnutls": ["mp.com.2", "mp.com.3"],
    # Servicios de autenticacion
    "default accounts": ["op.acc.2", "op.acc.4"],
    "credentials": ["op.acc.5"],
    # Archivos / FTP / SMB
    "smb": ["mp.com.1", "mp.info.3"],
    "ftp": ["mp.com.2"],
    # Firewall / perimetro
    "firewalls": ["mp.com.1"],
    "remote file access": ["mp.info.2", "op.acc.4"],
}


# ══════════════════════════════════════════════════════════════════
# Mapping 2: overrides NVT especificos (OID o substring del nombre)
# ══════════════════════════════════════════════════════════════════
#
# Util cuando la familia es generica pero el CVE afecta ENS concretas.
# Clave: substring (case-insensitive) que se busca en nvt.name o en
# refs.ref[type=cve].id. Valor: lista de medidas adicionales.

NAME_OVERRIDES: dict[str, list[str]] = {
    # RCE via path traversal clasico web
    "path traversal": ["op.exp.4", "op.acc.4"],
    # Auth bypass / sin password
    "auth bypass": ["op.acc.5"],
    "empty sa password": ["op.acc.2", "op.acc.5"],
    "sa login without password": ["op.acc.2", "op.acc.5"],
    # HSTS / headers seguridad
    "missing hsts": ["mp.com.2"],
    "hsts header": ["mp.com.2"],
    # SMB signing
    "smb signing not required": ["mp.com.3"],
    # End-of-Life / software obsoleto
    "end of life": ["op.exp.3", "op.exp.4"],
    "end-of-life": ["op.exp.3", "op.exp.4"],
    # Certificados
    "certificate expired": ["mp.com.2", "op.exp.3"],
    "self-signed certificate": ["mp.com.2"],
    # Cifrados debiles
    "rc4": ["mp.com.2"],
    "deprecated tlsv1": ["mp.com.2"],
}


# ══════════════════════════════════════════════════════════════════
# Mapping 3: bandas CVSS -> medidas transversales
# ══════════════════════════════════════════════════════════════════

def severity_to_ens(cvss: float) -> list[str]:
    """Medidas ENS asociadas a bandas CVSS (union con familia + overrides).

    Umbrales conforme al CVSS v3.1 oficial:
        >= 9.0   critical  -> parcheo urgente + gestion incidentes
        >= 7.0   high      -> mantenimiento critico
        >= 4.0   medium    -> revision en siguiente ciclo
        <  4.0   low/info  -> (vacio, no imputacion transversal)
    """
    if cvss is None:
        return []
    try:
        c = float(cvss)
    except (TypeError, ValueError):
        return []
    if c >= 9.0:
        return ["op.exp.4", "op.exp.7"]
    if c >= 7.0:
        return ["op.exp.4"]
    if c >= 4.0:
        return ["op.exp.3"]
    return []


# ══════════════════════════════════════════════════════════════════
# Etiquetas humanas
# ══════════════════════════════════════════════════════════════════

ENS_MEASURE_LABEL: dict[str, str] = {
    "op.acc.2": "Requisitos de acceso (passwords/MFA)",
    "op.acc.4": "Derechos de acceso (minimo privilegio)",
    "op.acc.5": "Mecanismo de autenticacion",
    "op.acc.6": "Acceso remoto",
    "op.exp.2": "Configuracion de seguridad",
    "op.exp.3": "Gestion de la configuracion (parches/cambios)",
    "op.exp.4": "Mantenimiento (parcheo critico)",
    "op.exp.7": "Gestion de incidentes",
    "op.cont.2": "Plan de continuidad",
    "mp.com.1": "Perimetro seguro",
    "mp.com.2": "Proteccion de la confidencialidad",
    "mp.com.3": "Proteccion de la integridad",
    "mp.eq.3": "Proteccion de equipos portatiles",
    "mp.info.2": "Calificacion de la informacion",
    "mp.info.3": "Cifrado",
    "mp.s.2": "Proteccion de servicios web",
    "mp.sw.1": "Desarrollo de aplicaciones",
    "mp.sw.2": "Aceptacion y puesta en servicio",
}


# ══════════════════════════════════════════════════════════════════
# API publica
# ══════════════════════════════════════════════════════════════════

def map_finding_to_ens(
    nvt_family: str | None,
    nvt_name: str | None,
    severity_cvss: float | None,
) -> list[str]:
    """Mapea un finding OpenVAS a medidas ENS aplicables (union).

    Returns lista ordenada sin duplicados.
    """
    measures: set[str] = set()
    if nvt_family:
        measures.update(FAMILY_TO_ENS.get(nvt_family.strip().lower(), []))
    if nvt_name:
        name_lower = nvt_name.lower()
        for substring, ens in NAME_OVERRIDES.items():
            if substring in name_lower:
                measures.update(ens)
    measures.update(severity_to_ens(severity_cvss))
    return sorted(measures)


def describe_ens_measure(measure: str) -> str:
    return ENS_MEASURE_LABEL.get(measure, measure)


def coverage_stats() -> dict[str, int]:
    """Stats para tests."""
    unique_measures: set[str] = set()
    for measures in FAMILY_TO_ENS.values():
        unique_measures.update(measures)
    for measures in NAME_OVERRIDES.values():
        unique_measures.update(measures)
    unique_measures.update(["op.exp.3", "op.exp.4", "op.exp.7"])  # severity bands
    return {
        "families_mapped": len(FAMILY_TO_ENS),
        "name_overrides": len(NAME_OVERRIDES),
        "unique_measures": len(unique_measures),
        "labels_defined": len(ENS_MEASURE_LABEL),
    }


# CVE / NVT families cubiertas por Nuclei (para consolidacion en orchestrator).
NUCLEI_COVERAGE_OVERLAP: frozenset[str] = frozenset({
    "web servers", "web application abuses", "ssl and tls",
})
