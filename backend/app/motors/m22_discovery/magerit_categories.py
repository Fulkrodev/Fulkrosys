"""MAGERIT v3 Libro II · 9 categorías canónicas activos (SAN-C MB-11.1).

Enum formal sustituye dict ``MAGERIT_TYPE_MAP`` previo (SAN-C MB-11.1).
Los valores string del enum coinciden con los códigos históricos del
proyecto FULKRO en BD (`discovered_assets.tipo_magerit`,
`magerit_assets.tipo`, `pkg_nodes.properties.tipo_magerit`) para
preservar compatibilidad sin migration data.

Mapping canonical MAGERIT v3 Libro II → código FULKRO:

    [I]  Información            → "D"  (legacy "Datos" del proyecto)
    [S]  Servicios              → "S"
    [SW] Aplicaciones           → "SW"
    [HW] Equipamiento           → "HW"
    [COM] Comunicaciones        → "COM"
    [SI] Soportes información   → "SI"
    [AUX] Equipamiento auxiliar → "AUX"
    [L]  Instalaciones          → "L"
    [P]  Personal               → "P"

NOTA · diferencia "I" canonical vs "D" legacy: decisión histórica
proyecto previa al ADR canonical. Spirit MAGERIT preservado (categoría
"Información/Datos" identificada como activo intangible). Migration
"D"→"I" canonical pendiente sesión futura si se decide; impacta 30+
sitios código + DB. Documentado aquí para trazabilidad.

Referencias
-----------
- MAGERIT v3 Libro II "Catálogo de Elementos" CCN · sección 1
  "Tipos de activos" · 9 categorías canónicas.
- SAN-C.MB-11.1 · briefing audit 9 categorías + workflow 10 fases.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


class MageritCategory(str, Enum):
    """9 categorías canónicas MAGERIT v3 Libro II.

    Valores string preservan codes legacy proyecto FULKRO en BD/PKG/tests.
    """

    INFORMACION = "D"      # [I] Información (legacy "D" Datos en código)
    SERVICIOS = "S"        # [S] Servicios
    SOFTWARE = "SW"        # [SW] Aplicaciones / software
    HARDWARE = "HW"        # [HW] Equipamiento físico
    COMUNICACIONES = "COM"  # [COM] Comunicaciones (red, conectividad)
    SOPORTES = "SI"        # [SI] Soportes información
    AUXILIAR = "AUX"       # [AUX] Equipamiento auxiliar
    INSTALACIONES = "L"    # [L] Instalaciones físicas
    PERSONAL = "P"         # [P] Personal

    @classmethod
    def all_codes(cls) -> list[str]:
        """Lista 9 codes string en orden enum."""
        return [c.value for c in cls]

    @classmethod
    def from_resource_type(
        cls,
        resource_type: str,
        metadata: Optional[dict] = None,
    ) -> "MageritCategory":
        """Clasifica resource_type discovery → categoría MAGERIT.

        Lookup directo prefijo conector + heurística por substring fallback.
        Replica lógica histórica ``classify_magerit_type`` previa pero
        retorna enum canonical en vez de string.
        """
        rt = (resource_type or "").lower()

        # Lookup directo (M365, AWS, Azure, GitHub, GWS, genéricos)
        if rt in _RESOURCE_TYPE_MAP:
            return _RESOURCE_TYPE_MAP[rt]

        # Heurística substring fallback
        if any(k in rt for k in ("vpc", "vnet", "subnet", "network", "elb", "gateway")):
            return cls.COMUNICACIONES
        if any(k in rt for k in ("bucket", "storage", "data", "drive", "mailbox", "sharepoint")):
            return cls.INFORMACION
        if any(k in rt for k in ("repo", "lambda", "function", "app_service", "application")):
            return cls.SOFTWARE
        if any(k in rt for k in ("vm", "ec2", "instance", "server", "device")):
            return cls.HARDWARE
        if any(k in rt for k in ("user", "role", "account", "identity")):
            return cls.PERSONAL
        if any(k in rt for k in ("team", "group", "service")):
            return cls.SERVICIOS
        return cls.SOFTWARE


_RESOURCE_TYPE_MAP: dict[str, MageritCategory] = {
    # M365
    "m365_user": MageritCategory.PERSONAL,
    "m365_device": MageritCategory.HARDWARE,
    "m365_application": MageritCategory.SOFTWARE,
    "m365_mailbox": MageritCategory.INFORMACION,
    "m365_sharepoint_site": MageritCategory.INFORMACION,
    "m365_team": MageritCategory.SERVICIOS,
    # AWS
    "aws_ec2_instance": MageritCategory.HARDWARE,
    "aws_s3_bucket": MageritCategory.INFORMACION,
    "aws_rds_instance": MageritCategory.SOFTWARE,
    "aws_lambda": MageritCategory.SOFTWARE,
    "aws_vpc": MageritCategory.COMUNICACIONES,
    "aws_iam_role": MageritCategory.PERSONAL,
    "aws_elb": MageritCategory.COMUNICACIONES,
    # Azure
    "azure_vm": MageritCategory.HARDWARE,
    "azure_storage_account": MageritCategory.INFORMACION,
    "azure_sql_db": MageritCategory.SOFTWARE,
    "azure_vnet": MageritCategory.COMUNICACIONES,
    "azure_app_service": MageritCategory.SOFTWARE,
    # GitHub
    "github_repo": MageritCategory.SOFTWARE,
    "github_action": MageritCategory.SOFTWARE,
    # Google Workspace
    "gws_user": MageritCategory.PERSONAL,
    "gws_drive": MageritCategory.INFORMACION,
    "gws_group": MageritCategory.SERVICIOS,
    # Genéricos
    "server": MageritCategory.HARDWARE,
    "network_device": MageritCategory.COMUNICACIONES,
    "database": MageritCategory.INFORMACION,
    "application": MageritCategory.SOFTWARE,
    "service": MageritCategory.SERVICIOS,
    "bucket": MageritCategory.INFORMACION,
    "vpc": MageritCategory.COMUNICACIONES,
    "subnet": MageritCategory.COMUNICACIONES,
    "repo": MageritCategory.SOFTWARE,
    "storage": MageritCategory.INFORMACION,
    "vm": MageritCategory.HARDWARE,
}
