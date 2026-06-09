"""RGPD UE 2016/679 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_ARTICLE_REFS: dict[str, str] = {
    "rgpd_endpoints_responding": "Art. 15 / 17 / 20 RGPD (derechos del interesado)",
    "breach_workflow_ready": "Art. 33 RGPD (notificación de violaciones)",
    "privacy_policy_freshness": "Art. 13-14 RGPD (información al interesado)",
    "dpa_template_version": "Art. 28 RGPD (encargado del tratamiento)",
    "sub_processor_dpa_expirations": "Art. 28 RGPD (sub-encargados)",
    "sub_processors_list_freshness": "Art. 28.2 RGPD (transparencia sub-encargados)",
    "ropa_review_due": "Art. 30 RGPD (Registro de Actividades de Tratamiento)",
    "dpo_email_working": "Art. 37 / 38 RGPD (Delegado de Protección de Datos)",
}


class RGPDModule(NormaModule):
    norma_key = "RGPD_UE_2016_679"
    norma_name = "RGPD · Reglamento General de Protección de Datos (UE 2016/679)"
    regulatory_basis_url = "https://eur-lex.europa.eu/eli/reg/2016/679/oj"
    applies_to = ["FULKRO_PLATFORM", "DATA_CONTROLLER", "DATA_PROCESSOR"]
    frequency = "monthly"
    priority = "critical"
    checks_owned = [
        "rgpd_endpoints_responding",
        "breach_workflow_ready",
        "privacy_policy_freshness",
        "dpa_template_version",
        "sub_processor_dpa_expirations",
        "sub_processors_list_freshness",
        "ropa_review_due",
        "dpo_email_working",
    ]
    check_weights = {
        "rgpd_endpoints_responding": 0.20,
        "breach_workflow_ready": 0.18,
        "dpa_template_version": 0.12,
        "privacy_policy_freshness": 0.12,
        "ropa_review_due": 0.12,
        "sub_processor_dpa_expirations": 0.10,
        "sub_processors_list_freshness": 0.08,
        "dpo_email_working": 0.08,
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
            "## Resumen ejecutivo",
            "",
            (
                "FULKRO opera como responsable y, según el contrato, como "
                "encargado del tratamiento para las cuentas cliente que se "
                "gestionan en la plataforma. Este informe agrega el estado "
                "de los controles automáticos que respaldan el cumplimiento "
                "del RGPD en el periodo indicado."
            ),
            "",
            "## Detalle por control (Art. RGPD)",
            "",
            "| Check | Artículo | Estado | Mensaje |",
            "|---|---|---|---|",
        ]
        for name in self.checks_owned:
            ref = _ARTICLE_REFS.get(name, "—")
            outcome = by_name.get(name)
            if outcome is None:
                lines.append(f"| `{name}` | {ref} | ⚪ unknown | sin datos en el periodo |")
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
                "## Observaciones",
                "",
                (
                    "- Los checks con estado **rojo** se notifican al DPO de "
                    "forma inmediata (canal email)."
                ),
                (
                    "- Las brechas detectadas se notifican a la AEPD en el "
                    "plazo de 72 horas (Art. 33.1 RGPD)."
                ),
                (
                    "- El RoPA se mantiene en `fulkro_ropa_treatments` y se "
                    "exporta a formato AEPD bajo demanda."
                ),
                "",
                f"_Reporte generado automáticamente · norma_key={self.norma_key}_",
            ]
        )
        return "\n".join(lines)


NormaRegistry.register(RGPDModule())
