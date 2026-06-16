"""Render sample per-norma reports to Desktop folder (mini-atom 3).

Uses dummy "all green" check outcomes so the reports are visually
informative without requiring a populated database. Output:

    /mnt/c/Users/Usuario/Desktop/Fulkro compliance/08-Self_Monitoring_Reports/per_norma/
      RGPD_UE_2016_679_sample.md
      LOPDGDD_3_2018_sample.md
      ...

Run with::

    PYTHONPATH=/home/usuario/fulkro python scripts/render_norma_reports_samples.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.motors.m_compliance_monitor.normas import (
    CheckOutcome,
    NormaRegistry,
)


# W9-2: destino configurable vía FULKRO_SAMPLES_DIR (antes hardcodeado al Desktop
# de Windows /mnt/c/...). Default portable = <repo-root>/out/compliance_samples.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SAMPLES_BASE = Path(
    os.environ.get("FULKRO_SAMPLES_DIR", str(_REPO_ROOT / "out" / "compliance_samples"))
)
OUTPUT_DIR = _SAMPLES_BASE / "08-Self_Monitoring_Reports" / "per_norma"


_GREEN_MESSAGES = {
    "rgpd_endpoints_responding": "Endpoints /portal/rgpd/access · /erasure · /portability disponibles",
    "breach_workflow_ready": "Tabla fulkro_breach_notifications presente · workflow Art. 33 listo",
    "privacy_policy_freshness": "Política de privacidad publicada en /privacy · revisada hace 35 días",
    "dpa_template_version": "DPA template v1.0 publicado · 12 secciones + 3 anexos",
    "sub_processor_dpa_expirations": "5 sub-encargados con DPA vigente · ninguno expira en 60 días",
    "sub_processors_list_freshness": "/sub-processors actualizado · todos los proveedores listados",
    "ropa_review_due": "RoPA con 10 tratamientos · última revisión hoy",
    "dpo_email_working": "dpo@fulkro.es responde · email_log con tráfico en 90 días",
    "cookies_banner_functional": "Banner cookies funcional · 3 botones equal prominence (Guía AEPD 2020)",
    "cookie_consent_renewal_24month": "Todos los consents en ventana 24m · sin expirados",
    "security_txt_reachable": "/.well-known/security.txt sirve correctamente",
    "nis2_vulnerability_inbox": "security@fulkro.es responde · vulnerability inbox declarada",
    "ssl_cert_expiry": "Certificado SSL vigente · 245 días restantes",
    "backups_integrity": "Última copia completed hace 6h · restore test pasó este mes",
    "audit_logs_continuity": "audit_log con eventos en últimas 24h · hash chain íntegro",
    "rls_coverage_percentage": "RLS coverage 100% · todas las tablas tenant-sensitive cubiertas",
    "isms_docs_review_due": "5 ISMS docs presentes · todos dentro de ventana 18m",
}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)
    rendered = 0
    for module in NormaRegistry.get_all():
        period_end = now
        period_start = period_end - timedelta(days={
            "weekly": 7,
            "monthly": 30,
            "quarterly": 92,
        }[module.frequency])
        outcomes = [
            CheckOutcome(
                check_name=name,
                status="green",
                message=_GREEN_MESSAGES.get(name, "control nominal"),
                last_run_at=now,
                regulatory_basis=None,
            )
            for name in module.checks_owned
        ]
        md = module.generate_report_md(outcomes, period_start, period_end)
        path = OUTPUT_DIR / f"{module.norma_key}_sample.md"
        path.write_text(md, encoding="utf-8")
        print(f"  wrote {path.name} ({len(md):,} chars · score {module.calculate_score(outcomes):.1f}%)")
        rendered += 1
    print(f"\n✓ {rendered} norma sample reports rendered to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
