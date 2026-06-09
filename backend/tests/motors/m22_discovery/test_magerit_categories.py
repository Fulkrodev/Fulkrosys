"""Tests MageritCategory enum (SAN-C MB-11.1).

Cobertura:
- Enum tiene 9 categorías canónicas MAGERIT v3 Libro II.
- ``from_resource_type`` clasifica connectors directos (M365/AWS/Azure/GitHub/GWS).
- Heurística substring fallback para tipos no mapeados directos.
- Wrapper backward-compat ``classify_magerit_type`` retorna mismo string.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m22_discovery.asset_discovery import classify_magerit_type
from backend.app.motors.m22_discovery.magerit_categories import MageritCategory


def test_enum_has_9_canonical_categories():
    """MAGERIT v3 Libro II define 9 categorías de activos."""
    assert len(MageritCategory) == 9


def test_enum_codes_match_legacy_strings():
    """Codes string preservan compatibilidad BD/PKG/tests previos."""
    assert MageritCategory.INFORMACION.value == "D"  # legacy "D" Datos
    assert MageritCategory.SERVICIOS.value == "S"
    assert MageritCategory.SOFTWARE.value == "SW"
    assert MageritCategory.HARDWARE.value == "HW"
    assert MageritCategory.COMUNICACIONES.value == "COM"
    assert MageritCategory.SOPORTES.value == "SI"
    assert MageritCategory.AUXILIAR.value == "AUX"
    assert MageritCategory.INSTALACIONES.value == "L"
    assert MageritCategory.PERSONAL.value == "P"


@pytest.mark.parametrize(
    "rt, expected",
    [
        ("m365_user", MageritCategory.PERSONAL),
        ("m365_mailbox", MageritCategory.INFORMACION),
        ("m365_team", MageritCategory.SERVICIOS),
        ("aws_ec2_instance", MageritCategory.HARDWARE),
        ("aws_s3_bucket", MageritCategory.INFORMACION),
        ("aws_lambda", MageritCategory.SOFTWARE),
        ("aws_vpc", MageritCategory.COMUNICACIONES),
        ("aws_iam_role", MageritCategory.PERSONAL),
        ("azure_storage_account", MageritCategory.INFORMACION),
        ("github_repo", MageritCategory.SOFTWARE),
        ("gws_drive", MageritCategory.INFORMACION),
    ],
)
def test_from_resource_type_direct_lookup(rt, expected):
    assert MageritCategory.from_resource_type(rt) == expected


@pytest.mark.parametrize(
    "rt, expected",
    [
        ("custom_vpc_x", MageritCategory.COMUNICACIONES),
        ("xyz_storage", MageritCategory.INFORMACION),
        ("custom_vm_pool", MageritCategory.HARDWARE),
        ("tenant_user_record", MageritCategory.PERSONAL),
        ("application_x", MageritCategory.SOFTWARE),
        ("unknown_thing", MageritCategory.SOFTWARE),  # default fallback
    ],
)
def test_from_resource_type_heuristic_fallback(rt, expected):
    assert MageritCategory.from_resource_type(rt) == expected


def test_classify_magerit_type_backward_compat_returns_string():
    """Wrapper legacy retorna string code, no enum."""
    result = classify_magerit_type("aws_s3_bucket")
    assert isinstance(result, str)
    assert result == "D"


def test_all_codes_canonical_count():
    codes = MageritCategory.all_codes()
    assert len(codes) == 9
    assert set(codes) == {"D", "S", "SW", "HW", "COM", "SI", "AUX", "L", "P"}
