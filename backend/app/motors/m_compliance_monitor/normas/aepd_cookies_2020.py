"""AEPD Guía de Cookies 2020 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_REFS = {
    "cookies_banner_functional": "Guía AEPD 2020 §4.2 (información y consentimiento)",
    "cookie_consent_renewal_24month": "Guía AEPD 2020 §4.4 (renovación 24 meses)",
}


class AEPDCookiesModule(NormaModule):
    norma_key = "AEPD_COOKIES_2020"
    norma_name = "AEPD · Guía sobre el uso de las cookies (julio 2020)"
    regulatory_basis_url = (
        "https://www.aepd.es/sites/default/files/2020-07/guia-cookies.pdf"
    )
    applies_to = ["FULKRO_PLATFORM"]
    frequency = "monthly"
    priority = "high"
    checks_owned = [
        "cookies_banner_functional",
        "cookie_consent_renewal_24month",
    ]
    check_weights = {
        "cookies_banner_functional": 0.60,
        "cookie_consent_renewal_24month": 0.40,
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
            "## Cumplimiento Guía AEPD 2020 en FULKRO",
            "",
            (
                "La Guía AEPD 2020 desarrolla el Art. 22.2 LSSI-CE en materia "
                "de cookies. FULKRO implementa el patrón de consent banner "
                "con tres botones de igual prominencia (Rechazar / Configurar "
                "/ Aceptar) y renovación cada 24 meses."
            ),
            "",
            "## Detalle por control",
            "",
            "| Check | Referencia AEPD | Estado | Mensaje |",
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
                "## Inventario de cookies",
                "",
                (
                    "Inventario actualizado en "
                    "`frontend/lib/cookies/inventory.ts` y publicado en `/cookies` "
                    "(Política de Cookies)."
                ),
                "",
                f"_Reporte generado automáticamente · norma_key={self.norma_key}_",
            ]
        )
        return "\n".join(lines)


NormaRegistry.register(AEPDCookiesModule())
