"""LSSI-CE 34/2002 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_ARTICLE_REFS = {
    "privacy_policy_freshness": "Art. 10 LSSI-CE (información general)",
    "security_txt_reachable": "Art. 16 LSSI-CE (responsabilidad de prestadores)",
}


class LSSICEModule(NormaModule):
    norma_key = "LSSI_CE_34_2002"
    norma_name = "LSSI-CE · Ley 34/2002 de Servicios de la Sociedad de la Información"
    regulatory_basis_url = "https://www.boe.es/eli/es/l/2002/07/11/34/con"
    applies_to = ["FULKRO_PLATFORM"]
    frequency = "quarterly"
    priority = "medium"
    checks_owned = [
        "privacy_policy_freshness",
        "security_txt_reachable",
    ]
    check_weights = {
        "privacy_policy_freshness": 0.70,
        "security_txt_reachable": 0.30,
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
            "## Obligaciones LSSI-CE en FULKRO",
            "",
            (
                "FULKRO presta servicios de la sociedad de la información a "
                "través de fulkro.es. La LSSI-CE exige información general "
                "accesible (Art. 10 · Aviso Legal) y mecanismos de contacto "
                "para usuarios y autoridades (Art. 16)."
            ),
            "",
            "## Detalle por control",
            "",
            "| Check | Artículo LSSI-CE | Estado | Mensaje |",
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
        lines.append(
            "## Páginas legales requeridas"
        )
        lines.append("")
        lines.append("- `/privacy` (Política de Privacidad · Art. 10.1.c)")
        lines.append("- `/cookies` (Política de Cookies · RD-Ley 13/2012)")
        lines.append("- `/terms` (Términos del servicio)")
        lines.append("- `/imprint` (Aviso Legal · Art. 10.1.a-b)")
        lines.append("")
        lines.append(f"_Reporte generado automáticamente · norma_key={self.norma_key}_")
        return "\n".join(lines)


NormaRegistry.register(LSSICEModule())
