"""ENS RD 311/2022 norma plugin (mini-atom 3)."""
from __future__ import annotations

from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


_REFS = {
    "audit_logs_continuity": "ENS [op.exp.8] Registro de la actividad de los usuarios",
    "backups_integrity": "ENS [op.exp.10] Protección de los registros de la actividad",
    "rls_coverage_percentage": "ENS [op.acc.4] Segregación de funciones",
    "ssl_cert_expiry": "ENS [mp.s.2] Protección de servicios web (cifrado)",
    "admin_actions_audit_logged": "ENS [op.exp.8] Registro de acciones de administración (Art. 24.1)",
    "intrusion_detection_present": "ENS [op.mon.1] Detección de intrusión + [op.mon.3] Vigilancia",
    "mfa_enforcement": "ENS [op.acc.5] Mecanismo de autenticación (2FA · R4) + [op.acc.6]",
}


class ENSModule(NormaModule):
    """FULKRO se autoaplica el ENS RD 311/2022.

    Aunque FULKRO no es una entidad del sector público, asume el ENS
    como marco de referencia voluntario porque (i) los clientes a los
    que asiste sí lo aplican y (ii) la consistencia entre lo que
    predicamos y lo que practicamos es operacionalmente útil.
    """

    norma_key = "ENS_RD_311_2022"
    norma_name = "ENS · Real Decreto 311/2022 (Esquema Nacional de Seguridad)"
    regulatory_basis_url = "https://www.boe.es/eli/es/rd/2022/05/03/311/con"
    applies_to = ["FULKRO_PLATFORM_VOLUNTARY"]
    frequency = "monthly"
    priority = "high"
    checks_owned = [
        "audit_logs_continuity",
        "backups_integrity",
        "rls_coverage_percentage",
        "ssl_cert_expiry",
        # J-1 · check 18 ENS art.24.1 (registro de acciones de administración).
        # Faltaba pese a ser nuclear para op.exp.8 en dogfooding MEDIA.
        "admin_actions_audit_logged",
        # SIEM_INVESTIGATION.md · op.mon.1 (detección de intrusión · aplica
        # desde MEDIA, el nivel que FULKRO declara sobre sí mismo). El plugin
        # NO tenía ningún check op.mon → posible no conformidad menor cerrada.
        "intrusion_detection_present",
        # J#4/5 dogfooding · op.acc.5 (2FA · R4 WebAuthn/TOTP para admin). El
        # plugin no verificaba el segundo factor pese a ser nuclear en MEDIA.
        "mfa_enforcement",
    ]
    check_weights = {
        "audit_logs_continuity": 0.20,
        "backups_integrity": 0.18,
        "rls_coverage_percentage": 0.15,
        "ssl_cert_expiry": 0.12,
        "admin_actions_audit_logged": 0.15,
        "intrusion_detection_present": 0.10,
        "mfa_enforcement": 0.10,
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
            "## Aplicabilidad voluntaria a FULKRO",
            "",
            (
                "FULKRO no es entidad del sector público, pero asume el ENS "
                "como marco interno porque sus clientes sí lo aplican. La "
                "categoría asumida es **MEDIA** (Anexo I), coherente con que "
                "la plataforma gestiona datos de varios clientes con categoría "
                "MEDIA y se autoaplica el ENS sobre sí misma (dogfooding · R7)."
            ),
            "",
            "## Detalle por control",
            "",
            "| Check | Medida ENS | Estado | Mensaje |",
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
                "## Conservación de evidencias (Art. 24.1)",
                "",
                (
                    "Las evidencias se conservan 7 años (anonimizadas tras "
                    "supresión solicitada por el interesado · ver "
                    "`fulkro_erasure_requests` · `tombstone_data`)."
                ),
                "",
                f"_Reporte generado automáticamente · norma_key={self.norma_key}_",
            ]
        )
        return "\n".join(lines)


NormaRegistry.register(ENSModule())
