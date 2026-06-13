"""m_remediation · Motor de auto-remediación (ADR-055).

Aplica arreglos a hallazgos (cloud misconfig + host on-prem) acotado por una
POLÍTICA DE RIESGO DETERMINISTA (R1 · ningún LLM decide riesgo):

  - SAFE_AUTO : reversible · sin impacto acceso/disponibilidad → automático
  - GUARDED   : puede afectar acceso → autorización previa + snapshot + rollback
  - BLOCKED   : destructivo/irreversible → nunca auto · solo plan (humano externo)

Carve-out CONTROLADO de ADR-014: read-only sigue siendo el DEFAULT; la escritura
es opt-in por conector + kill-switch en 3 capas (env global · flag conector ·
política proyecto). Default OFF en todas → comportamiento idéntico al de hoy.

Submódulos:
  - catalog.py   : catálogo de acciones (código · determinista · versionado)
  - policy.py    : clasificador de riesgo + resolución de política por conector
  - models.py    : RemediationJob · RemediationSnapshot (+ agente Fase 3)
  - writers.py   : interfaz RemediationWriter por proveedor (escritura opt-in)
  - service.py   : orquestación preflight→snapshot→apply→verify→rollback→audit
"""
