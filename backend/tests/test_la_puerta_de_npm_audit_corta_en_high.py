"""Guardia: la puerta de npm audit corta en CRITICAL **y** HIGH.

El defecto. ``npm_audit_gate.py:71`` decia:

    if not isinstance(via, dict) or via.get("severity") != "critical":
        continue

Solo `critical`. Y el dia que se subio el umbral aparecieron DOCE avisos
CRITICAL/HIGH que pasaban enteros por la puerta —diez de `next` (denegacion de
servicio en Server Components, SSRF en Server Actions y en rewrites, bypass de
middleware con i18n) y dos de `postcss`— ninguno de los cuales se veia en el
recuento, porque ese recuento agrupa por PAQUETE y `next` ya figuraba como
"critical".

Ademas el informe se genera con ``--production``, asi que las dependencias de
desarrollo no se miraban en absoluto. Ahora se cuentan e informan aparte, sin
tumbar el build: no viajan al contenedor, pero que no se vean no es lo mismo
que que no existan.

Estos tests no llaman a npm: ejercitan el gate con informes sinteticos.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest


_RAIZ = Path(__file__).resolve().parents[2]
_GATE = _RAIZ / ".github/scripts/npm_audit_gate.py"
_LISTA = _RAIZ / ".github/npm-audit-allowlist.json"


def _informe(*avisos: tuple[str, str, str]) -> dict:
    """(paquete, severidad, ghsa) -> informe con la forma de `npm audit --json`."""
    vulns: dict[str, dict] = {}
    for paquete, severidad, ghsa in avisos:
        vulns.setdefault(paquete, {"severity": severidad, "via": []})
        vulns[paquete]["via"].append({
            "severity": severidad,
            "url": f"https://github.com/advisories/{ghsa}",
            "title": f"aviso de prueba {ghsa}",
        })
    return {"vulnerabilities": vulns, "metadata": {"vulnerabilities": {}}}


def _correr(tmp_path: Path, informe: dict, lista: dict | None = None):
    inf = tmp_path / "audit.json"
    inf.write_text(json.dumps(informe), encoding="utf-8")
    lst = tmp_path / "lista.json"
    lst.write_text(
        json.dumps(lista) if lista is not None
        else _LISTA.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(_GATE), str(inf), str(lst)],
        capture_output=True, text=True, cwd=_RAIZ,
    )


def test_un_high_sin_acotar_tumba_el_build(tmp_path):
    """Este es EL defecto: antes pasaba en verde."""
    r = _correr(tmp_path, _informe(("paquete-x", "high", "GHSA-hhhh-hhhh-hhhh")))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "GHSA-hhhh-hhhh-hhhh" in r.stdout + r.stderr


def test_un_critical_sin_acotar_sigue_tumbando_el_build(tmp_path):
    r = _correr(tmp_path, _informe(("paquete-x", "critical", "GHSA-cccc-cccc-cccc")))
    assert r.returncode == 1, r.stdout + r.stderr


def test_moderate_y_low_avisan_y_pasan(tmp_path):
    """El umbral es high: por debajo no se corta, para no criar ruido rojo."""
    r = _correr(
        tmp_path,
        _informe(
            ("paquete-x", "moderate", "GHSA-mmmm-mmmm-mmmm"),
            ("paquete-y", "low", "GHSA-llll-llll-llll"),
        ),
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_un_high_acotado_con_fecha_vigente_avisa_y_pasa(tmp_path):
    lista = {
        "avisos_aceptados": [{
            "ghsa": "GHSA-hhhh-hhhh-hhhh",
            "paquete": "paquete-x",
            "severidad": "high",
            "titulo": "t",
            "version_instalada": "1.0.0",
            "arreglado_en": ">=2.0.0",
            "por_que_se_acepta": "motivo de prueba",
            "revisar_antes_de": str(date.today() + timedelta(days=30)),
        }]
    }
    r = _correr(tmp_path, _informe(("paquete-x", "high", "GHSA-hhhh-hhhh-hhhh")), lista)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "AVISO ACOTADO" in r.stdout
    assert "HIGH" in r.stdout, "el aviso tiene que decir su severidad"


def test_un_high_acotado_con_la_fecha_pasada_tumba_el_build(tmp_path):
    """Una entrada caducada es un fallo, no una nota al pie."""
    lista = {
        "avisos_aceptados": [{
            "ghsa": "GHSA-hhhh-hhhh-hhhh",
            "paquete": "paquete-x",
            "severidad": "high",
            "titulo": "t",
            "version_instalada": "1.0.0",
            "arreglado_en": ">=2.0.0",
            "por_que_se_acepta": "motivo de prueba",
            "revisar_antes_de": str(date.today() - timedelta(days=1)),
        }]
    }
    r = _correr(tmp_path, _informe(("paquete-x", "high", "GHSA-hhhh-hhhh-hhhh")), lista)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "CADUCADO" in r.stdout + r.stderr


def test_las_dependencias_de_desarrollo_se_informan_sin_tumbar(tmp_path):
    inf_prod = tmp_path / "prod.json"
    inf_prod.write_text(json.dumps(_informe()), encoding="utf-8")
    inf_dev = tmp_path / "dev.json"
    inf_dev.write_text(json.dumps({
        "vulnerabilities": {"eslint-config-next": {"severity": "high", "via": []}},
        "metadata": {"vulnerabilities": {"high": 1, "total": 1}},
    }), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_GATE), str(inf_prod), str(_LISTA),
         "--informe-dev", str(inf_dev)],
        capture_output=True, text=True, cwd=_RAIZ,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "eslint-config-next" in r.stdout
    assert "SOLO de desarrollo" in r.stdout


def test_el_informe_roto_sigue_bloqueando(tmp_path):
    """Un fallo de la herramienta NO puede pasar por exito."""
    roto = tmp_path / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_GATE), str(roto), str(_LISTA)],
        capture_output=True, text=True, cwd=_RAIZ,
    )
    assert r.returncode == 2, r.stdout + r.stderr


@pytest.mark.parametrize("campo", [
    "ghsa", "paquete", "severidad", "titulo", "version_instalada",
    "arreglado_en", "por_que_se_acepta", "revisar_antes_de",
])
def test_cada_entrada_acotada_lleva_sus_campos(campo):
    """Una excepcion sin motivo y sin fecha no es una excepcion."""
    lista = json.loads(_LISTA.read_text(encoding="utf-8"))
    for entrada in lista["avisos_aceptados"]:
        assert entrada.get(campo), f"{entrada.get('ghsa')} sin {campo}"
        if campo == "por_que_se_acepta":
            assert len(entrada[campo]) > 80, (
                f"{entrada['ghsa']}: el motivo tiene que explicarse, no citarse"
            )


def test_el_workflow_pasa_los_dos_informes_al_gate():
    yml = (_RAIZ / ".github/workflows/security-scan.yml").read_text(encoding="utf-8")
    assert "--informe-dev npm-audit-report-dev.json" in yml
    assert "npm audit --json > npm-audit-report-dev.json" in yml
