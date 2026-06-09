"""Motor SIEM (FRENTE N) · capa ligera de correlación de eventos de seguridad.

Agrega eventos de las fuentes EXISTENTES (ADR-025 · sin tablas nuevas · ON-QUERY)
y aplica reglas de correlación DETERMINISTAS (R1 · sin LLM en la decisión):
- M8 verification_findings (pentest/vuln-scan · foco principal)
- M19 incidents (incidentes de seguridad · CCN-STIC 817)
- M18 escalation_events (escalados)
- m_compliance_monitor compliance_alerts (alertas de cumplimiento)

Mapea ENS op.mon.1 (detección de intrusión) + op.mon.2 (métricas · ALTA).
Read-only (ADR-014). NO sustituye un SOC 24/7 ni un SIEM acreditado para ALTA
(Wazuh/externo) · es la correlación interna + métricas (ver SIEM_INVESTIGATION.md).
"""
