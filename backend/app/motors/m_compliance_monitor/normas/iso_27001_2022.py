"""ISO 27001:2022 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_REFS = {
    "ssl_cert_expiry": "ISO 27001:2022 A.8.24 (uso de criptografía)",
    "backups_integrity": "ISO 27001:2022 A.8.13 (copias de seguridad)",
    "audit_logs_continuity": "ISO 27001:2022 A.8.15 (logging)",
    "rls_coverage_percentage": "ISO 27001:2022 A.5.18 (derechos de acceso)",
    "isms_docs_review_due": "ISO 27001:2022 §7.5 (información documentada)",
}


class ISO27001Module(NormaModule):
    norma_key = "ISO_27001_2022"
    norma_name = "ISO/IEC 27001:2022 · Sistema de Gestión de Seguridad de la Información"
    regulatory_basis_url = "https://www.iso.org/standard/27001"
    applies_to = ["FULKRO_PLATFORM"]
    frequency = "quarterly"
    priority = "high"
    checks_owned = [
        "ssl_cert_expiry",
        "backups_integrity",
        "audit_logs_continuity",
        "rls_coverage_percentage",
        "isms_docs_review_due",
    ]
    check_weights = {
        "backups_integrity": 0.25,
        "audit_logs_continuity": 0.20,
        "isms_docs_review_due": 0.20,
        "rls_coverage_percentage": 0.20,
        "ssl_cert_expiry": 0.15,
    }

    def generate_report_md(
        self,
        outcomes: list[CheckOutcome],
        period_start: datetime,
        period_end: datetime,
    ) -> str:
        score = self.calculate_score(outcomes)
        status = self.score_to_status(score).upper()
        by_name = {o.check_name: o for o in outcomes}
        lines = [
            f"# Reporte de Cumplimiento · {self.norma_name}",
            "",
            f"**Periodo**: {period_start.date().isoformat()} → "
            f"{period_end.date().isoformat()}",
            f"**Score**: **{score:.1f} %** · _{status}_",
            f"**Marco**: <{self.regulatory_basis_url}>",
            "",
            "## Estado del SGSI FULKRO",
            "",
            (
                "Este reporte corresponde a la fase de **preparación de "
                "certificación**: FULKRO opera el SGSI bajo los Anexos A "
                "(controles) y §4-§10 (cláusulas) pero la auditoría externa "
                "todavía no se ha realizado. La certificación formal está "
                "prevista para Q4 2027."
            ),
            "",
            "## Detalle por control (Anexo A)",
            "",
            "| Check | Anexo / Cláusula | Estado | Mensaje |",
            "|---|---|---|---|",
        ]
        for name in self.checks_owned:
            ref = _REFS.get(name, "—")
            outcome = by_name.get(name)
            if outcome is None:
                lines.append(f"| `{name}` | {ref} | ⚪ unknown | sin datos |")
                continue
            emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴", "unknown": "⚪"}.get(
                outcome.status, "⚪"
            )
            lines.append(
                f"| `{name}` | {ref} | {emoji} {outcome.status} | {outcome.message} |"
            )
        lines.extend(
            [
                "",
                "## Documentación del SGSI",
                "",
                "- Information Security Policy",
                "- Risk Assessment + Risk Treatment Plan",
                "- Asset Register",
                "- Access Control Policy",
                "- Incident Response Plan + BCP",
                "",
                "Las 5 políticas viven bajo `docs/compliance/04-ISMS_ISO27001/` "
                "y se revisan cada 12-18 meses (`check_isms_docs_review_due`).",
                "",
                f"_Reporte generado automáticamente · norma_key={self.norma_key}_",
            ]
        )
        return "\n".join(lines)


NormaRegistry.register(ISO27001Module())
