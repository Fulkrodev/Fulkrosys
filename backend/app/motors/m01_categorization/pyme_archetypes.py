"""6 arquetipos PYME formal classification (SAN-C MB-11.6).

Manual ENS define 6 arquetipos PYME con tratamiento workflow distinto +
genérico fallback. Classifier deterministic (sin LLM) por reglas CNAE +
infrastructure_type + workforce_type. Trazabilidad ENAC = valor primario,
determinismo prevalece (LECCIÓN-OPS lLM-vs-determinismo · S10.5).

Arquetipos
----------
- SAAS_ONLY · 100% SaaS sin infra propia (op.ext + op.nub dominantes)
- TELETRABAJO_TOTAL · equipo remoto (MFA + VPN + ZTNA mandatory)
- SECTOR_SALUD · datos art.9 RGPD (alta casi automática)
- SECTOR_EDUCACION · universidad/centro (PCE-Universidades aplicable)
- DESARROLLADOR_AAPP · SaaS para AAPP (mp.sw + CRA + SDLC seguro)
- PROVEEDOR_FINANCIERO · cliente banca (doble cumplimiento ENS+DORA)
- GENERICO · fallback (no encaja en arquetipos específicos)

Reglas deterministic (orden de prioridad)
-----------------------------------------
1. CNAE start "86" → SECTOR_SALUD (confianza 0.95)
2. CNAE start "85" → SECTOR_EDUCACION (confianza 0.95)
3. CNAE start "64" → PROVEEDOR_FINANCIERO (confianza 0.90)
4. infrastructure_type == "saas_only" → SAAS_ONLY (confianza 0.85)
5. workforce_type == "fully_remote" → TELETRABAJO_TOTAL (confianza 0.80)
6. is_aapp_developer flag → DESARROLLADOR_AAPP (confianza 0.85)
7. fallback → GENERICO (confianza 0.50)

Persistencia
------------
projects.archetype VARCHAR(50) + projects.archetype_confidence NUMERIC(3,2).
Clasificación recalculable on-demand (no cached) — confidence permite
revisión manual cuando rules ambiguas.

Referencias
-----------
- SAN-C.MB-11.6 · briefing 6 arquetipos PYME formal classification.
- LECCIÓN-OPS LLM-vs-determinismo (S10.5) · trazabilidad ENAC primary.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PymeArquetipo(str, Enum):
    """7 valores: 6 arquetipos formales + GENERICO fallback."""

    SAAS_ONLY = "saas_only"
    """100% SaaS sin infra propia · op.ext + op.nub dominantes."""

    TELETRABAJO_TOTAL = "teletrabajo_total"
    """Equipo remoto · MFA+VPN+ZTNA mandatory."""

    SECTOR_SALUD = "sector_salud"
    """Datos art.9 RGPD · Alta casi automática."""

    SECTOR_EDUCACION = "sector_educacion"
    """Universidad/centro · PCE-Universidades aplicable."""

    DESARROLLADOR_AAPP = "desarrollador_aapp"
    """SaaS para AAPP · mp.sw + CRA + SDLC seguro."""

    PROVEEDOR_FINANCIERO = "proveedor_financiero"
    """Cliente sector banca · doble cumplimiento ENS+DORA."""

    AUTONOMO_INDIVIDUAL = "autonomo_individual"
    """Autónomo/microempresa (≤5 personas · sin infra on-premise) · FRENTE L.

    Dimensión ORTOGONAL a la categoría ENS (NO categoría nueva · respeta 1=1).
    Soporta los 3 niveles (BÁSICA autodeclaración 808/809 · MEDIA/ALTA con su
    cierre ENAC). Marco documental ligero + acumulación de roles RSeg/RSis
    permitida con justificación (CCN-STIC 801 sec 5.1 · Art.11 RD 311/2022)."""

    GENERICO = "generico"
    """No encaja en arquetipos específicos · fallback."""


@dataclass(frozen=True)
class ArquetipoClassification:
    """Resultado de classify · arquetipo + confidence + path razonamiento."""

    arquetipo: PymeArquetipo
    confidence: Decimal
    reasoning_path: list[str]


def classify_archetype(client_data: dict) -> ArquetipoClassification:
    """Clasifica cliente en arquetipo PYME formal.

    Args:
        client_data: dict con keys flexibles:
            - ``cnae_code`` (str, opcional) · código CNAE 4 dígitos
            - ``sector`` (str, opcional) · nombre sector textual fallback
            - ``infrastructure_type`` (str, opcional) · "saas_only" | "on_prem" | "hybrid"
            - ``workforce_type`` (str, opcional) · "fully_remote" | "hybrid" | "on_site"
            - ``is_aapp_developer`` (bool, opcional) · flag dev AAPP

    Returns:
        ArquetipoClassification con arquetipo, confidence (0.0-1.0) y
        reasoning_path explicable per UI.
    """
    path: list[str] = []
    cnae = (client_data.get("cnae_code") or "").strip()
    sector = (client_data.get("sector") or "").lower()
    infra = (client_data.get("infrastructure_type") or "").lower()
    workforce = (client_data.get("workforce_type") or "").lower()
    is_aapp_dev = bool(client_data.get("is_aapp_developer"))

    # 1. CNAE sector salud (86 = Actividades sanitarias y servicios sociales)
    if cnae.startswith("86") or "salud" in sector or "sanidad" in sector:
        path.append(f"CNAE/sector salud detectado (cnae={cnae or '?'} · sector={sector or '?'})")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.SECTOR_SALUD,
            confidence=Decimal("0.95"),
            reasoning_path=path,
        )

    # 2. CNAE sector educación (85 = Educación)
    if cnae.startswith("85") or "educacion" in sector or "universidad" in sector:
        path.append(f"CNAE/sector educación detectado (cnae={cnae or '?'} · sector={sector or '?'})")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.SECTOR_EDUCACION,
            confidence=Decimal("0.95"),
            reasoning_path=path,
        )

    # 3. CNAE financiero (64 = Servicios financieros)
    if cnae.startswith("64") or "banca" in sector or "financ" in sector:
        path.append(f"CNAE/sector financiero detectado (cnae={cnae or '?'} · sector={sector or '?'})")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.PROVEEDOR_FINANCIERO,
            confidence=Decimal("0.90"),
            reasoning_path=path,
        )

    # 4. AAPP developer flag explícito
    if is_aapp_dev:
        path.append("Flag is_aapp_developer activado · SaaS para AAPP")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.DESARROLLADOR_AAPP,
            confidence=Decimal("0.85"),
            reasoning_path=path,
        )

    # 5. Infra SaaS-only
    if infra == "saas_only":
        path.append("infrastructure_type=saas_only · sin infra propia")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.SAAS_ONLY,
            confidence=Decimal("0.85"),
            reasoning_path=path,
        )

    # 6. Workforce fully remote
    if workforce == "fully_remote":
        path.append("workforce_type=fully_remote · equipo distribuido")
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.TELETRABAJO_TOTAL,
            confidence=Decimal("0.80"),
            reasoning_path=path,
        )

    # 6.5 (L-4 · FRENTE L) Autónomo / microempresa · ≤5 personas y SIN infra
    # on-premise. Ortogonal a sector (los específicos arriba tienen prioridad) ·
    # ANTES del fallback genérico. Acepta n_empleados (int) o tamano_empleados
    # ("micro"/"autonomo"/"individual").
    n_empleados = client_data.get("n_empleados")
    if n_empleados is None:
        n_empleados = client_data.get("num_empleados")
    tamano = (str(client_data.get("tamano_empleados") or "")).lower()
    es_micro = (
        (isinstance(n_empleados, (int, float)) and 0 < int(n_empleados) <= 5)
        or tamano in {"micro", "autonomo", "autónomo", "individual"}
    )
    if es_micro and infra != "on_prem":
        path.append(
            "Autónomo/microempresa (≤5 personas · sin infra on-premise) · "
            f"n_empleados={n_empleados} · tamano={tamano or '?'} · infra={infra or '?'}"
        )
        return ArquetipoClassification(
            arquetipo=PymeArquetipo.AUTONOMO_INDIVIDUAL,
            confidence=Decimal("0.80"),
            reasoning_path=path,
        )

    # 7. Fallback genérico
    path.append("Sin reglas específicas activadas · fallback genérico")
    return ArquetipoClassification(
        arquetipo=PymeArquetipo.GENERICO,
        confidence=Decimal("0.50"),
        reasoning_path=path,
    )


def archetype_workflow_adjustments(arquetipo: PymeArquetipo) -> dict:
    """Ajustes workflow recomendados per arquetipo (no aplicación automática).

    Returns dict consumible per frontend para mostrar badges + sugerencias
    en project info / workflow page.
    """
    adjustments: dict[PymeArquetipo, dict] = {
        PymeArquetipo.SAAS_ONLY: {
            "skip_marcos": ["mp.if"],  # Instalaciones físicas no aplican
            "highlight_marcos": ["op.ext", "op.nub"],
            "notes": "Foco op.ext (servicios externos) + op.nub (cloud).",
        },
        PymeArquetipo.TELETRABAJO_TOTAL: {
            "skip_marcos": [],
            "highlight_marcos": ["op.acc", "mp.com"],
            "notes": "MFA + VPN + ZTNA refuerzo mandatory.",
        },
        PymeArquetipo.SECTOR_SALUD: {
            "skip_marcos": [],
            "highlight_marcos": ["mp.info", "mp.s"],
            "notes": "Datos art.9 RGPD · pre-categorización Alta casi automática.",
        },
        PymeArquetipo.SECTOR_EDUCACION: {
            "skip_marcos": [],
            "highlight_marcos": ["mp.info"],
            "notes": "PCE-Universidades aplicable · entornos heterogéneos.",
        },
        PymeArquetipo.DESARROLLADOR_AAPP: {
            "skip_marcos": [],
            "highlight_marcos": ["mp.sw"],
            "notes": "mp.sw reforzado · CRA preparation · SDLC seguro.",
        },
        PymeArquetipo.PROVEEDOR_FINANCIERO: {
            "skip_marcos": [],
            "highlight_marcos": ["op.ext", "op.cont"],
            "notes": "Doble cumplimiento ENS+DORA · TPRM riguroso.",
        },
        PymeArquetipo.GENERICO: {
            "skip_marcos": [],
            "highlight_marcos": [],
            "notes": "Sin ajustes específicos · workflow estándar.",
        },
    }
    return adjustments.get(arquetipo, adjustments[PymeArquetipo.GENERICO])
