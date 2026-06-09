"""NIS2 UE 2022/2555 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_REFS = {
    "security_txt_reachable": "NIS2 art. 21.2.b + RFC 9116",
    "nis2_vulnerability_inbox": "NIS2 art. 21.2.b (gestión de vulnerabilidades)",
    "ssl_cert_expiry": "NIS2 art. 21.2.h (criptografía y certificados)",
    "breach_workflow_ready": "NIS2 art. 23 (notificación de incidentes)",
}


class NIS2Module(NormaModule):
    norma_key = "NIS2_UE_2022_2555"
    norma_name = "NIS2 · Directiva (UE) 2022/2555 (ciberseguridad)"
    regulatory_basis_url = "https://eur-lex.europa.eu/eli/dir/2022/2555/oj"
    applies_to = ["FULKRO_PLATFORM_IF_ESSENTIAL_OR_IMPORTANT_ENTITY"]
    frequency = "weekly"
    priority = "critical"
    checks_owned = [
        "security_txt_reachable",
        "nis2_vulnerability_inbox",
        "ssl_cert_expiry",
        "breach_workflow_ready",
    ]
    check_weights = {
        "ssl_cert_expiry": 0.30,
        "breach_workflow_ready": 0.30,
        "nis2_vulnerability_inbox": 0.25,
        "security_txt_reachable": 0.15,
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
            "## Alineación NIS2 en FULKRO",
            "",
            (
                "FULKRO se alinea voluntariamente con los requisitos del Art. "
                "21 NIS2 aunque, por tamaño actual, todavía no encaja como "
                "*entidad esencial* o *importante*. La alineación adelanta el "
                "trabajo si en el futuro un cliente del sector financiero o "
                "energético nos exige NIS2."
            ),
            "",
            "## Detalle por control",
            "",
            "| Check | Referencia NIS2 | Estado | Mensaje |",
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
                "## Procedimientos NIS2 documentados",
                "",
                "- Cadena de notificación de incidentes 24h / 72h / 1 mes (Art. 23).",
                "- Política de divulgación de vulnerabilidades (security.txt + DPO email).",
                "- Política de seguridad de la cadena de suministro (sub-procesadores).",
                "",
                f"_Reporte generado automáticamente · norma_key={self.norma_key}_",
            ]
        )
        return "\n".join(lines)


NormaRegistry.register(NIS2Module())
