"""LOPDGDD 3/2018 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_ARTICLE_REFS = {
    "dpo_email_working": "Art. 34.5 LOPDGDD (canal de contacto del DPO)",
    "breach_workflow_ready": "Art. 74 LOPDGDD (deber de notificación)",
    "privacy_policy_freshness": "Art. 11 LOPDGDD (información al afectado)",
}


class LOPDGDDModule(NormaModule):
    norma_key = "LOPDGDD_3_2018"
    norma_name = "LOPDGDD · Ley Orgánica 3/2018 de Protección de Datos"
    regulatory_basis_url = "https://www.boe.es/eli/es/lo/2018/12/05/3/con"
    applies_to = ["FULKRO_PLATFORM", "DATA_CONTROLLER"]
    frequency = "monthly"
    priority = "critical"
    checks_owned = [
        "dpo_email_working",
        "breach_workflow_ready",
        "privacy_policy_freshness",
    ]
    check_weights = {
        "breach_workflow_ready": 0.40,
        "dpo_email_working": 0.30,
        "privacy_policy_freshness": 0.30,
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
            f"**Marco regulatorio**: <{self.regulatory_basis_url}>",
            "",
            "## Aplicabilidad a FULKRO",
            "",
            (
                "La LOPDGDD complementa el RGPD en el ámbito español. Este "
                "informe verifica las obligaciones específicas del título III "
                "(derechos digitales) y del título VIII (potestades de la AEPD) "
                "que afectan a FULKRO como responsable establecido en España."
            ),
            "",
            "## Detalle por control",
            "",
            "| Check | Artículo LOPDGDD | Estado | Mensaje |",
            "|---|---|---|---|",
        ]
        for name in self.checks_owned:
            ref = _ARTICLE_REFS.get(name, "—")
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
        lines.append("")
        lines.append(f"_Reporte generado automáticamente · norma_key={self.norma_key}_")
        return "\n".join(lines)


NormaRegistry.register(LOPDGDDModule())
