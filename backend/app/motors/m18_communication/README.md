# Motor 18 · Communication & Reporting

Generación automática de reportes desde datos reales del proyecto (M17 Planning + M19 Risk + M05 Obligations + M07 Evidence + M08 Verification + M10 Audit Sim) + plan de comunicación + triggers de escalado + actas de reuniones DOCX + AEPD decision tree (notificación brecha datos personales). Anti-alucinación pura: TODO determinista, NO LLM.

## Funcionalidades

- **Report generator** (`report_generator.py`) `REPORT_TEMPLATES` con templates per tipo de informe (estado mensual · incidente · auditoría · etc.).
- **Alerts service** (`alert_service.py` + `alerts_api.py` + `alert_schemas.py`) gestión alertas con priorización + canal (email · WhatsApp · in-app).
- **Escalation service** (`escalation_service.py`) `TRIGGERS` de escalado automático (SLA breach · incidente crítico · auditoría próxima).
- **Minutes service** (`minutes_service.py` + `minutes_docx.py`) actas de reuniones DOCX generadas + estados (draft → reviewed → signed) + firma vía M05_signing.
- **Plan service** (`plan_service.py`) plan de comunicación cliente con cadencias + canales.
- **AEPD API** (`aepd_api.py` + `aepd_connector.py` + `aepd_decision_tree.py`) decision tree para notificación brecha datos personales art. 33 RGPD + connector AEPD plataforma.
- **Email signature** (`email_signature.py`) firma email outbound (BIMI + DKIM + DMARC trust).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.002 |
| Files | 14 |
| Status | production-grade |
| Tests | `backend/tests/motors/m18_communication/` |
| API prefix | `/api/v1/communication/*` (+ alerts + aepd sub-routers) |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP communication core
- `alerts_api.py` · endpoints alerts
- `aepd_api.py` · endpoints AEPD notificación brecha
- `report_generator.py` · `REPORT_TEMPLATES` + `ReportError`
- `alert_service.py` + `alert_schemas.py` · alerts core
- `escalation_service.py` · `TRIGGERS` + `EscalationError`
- `minutes_service.py` + `minutes_docx.py` · actas reuniones
- `plan_service.py` · `CommunicationPlanService`
- `aepd_connector.py` · connector plataforma AEPD
- `aepd_decision_tree.py` · decision tree brecha art. 33 RGPD
- `email_signature.py` · firma email BIMI/DKIM/DMARC

⚠️ NO existe `service.py` único · scope split por responsabilidad (report · alert · escalation · minutes · plan · aepd).

## DB tables

N/A motor-specific declarado en api.py · usa modelos compartidos:
- `Alert` + `EscalationLog` (compartidos)
- `Minutes` (actas DOCX)
- `CommunicationPlan` + `AepdNotification`

RLS por `alerts` + `minutes`.

## Cross-motor integration

- **Inbound** (motores que consumen M18):
  - M08 Verification (alertas vuln crítica)
  - M19 Risk (alerta incidente · escalation)
  - M23 Retainer (informe mensual retainer)
  - M27 Conformity (informe conformidad cliente)
  - M_meetings (minutes wire-up)
- **Outbound**:
  - M06 Document Factory (templates DOCX/PDF para reports)
  - M12 Magic Link (notificación cliente vía link)
  - M17 Planning (data plan para reports)
  - M20 Workspace (post mensaje workspace cliente)
  - M30 Client Contacts (destinatarios)
- **LLM agents**: ninguno (motor determinístico estricto · cement anti-alucinación)

## Limitaciones conocidas

### Anti-alucinación estricta en reports

Decisión cement: TODO report content extraído de BD real · NUNCA LLM-generated. Si data missing → reporte explicita "no disponible" · NO inventa.

**Cement institutional**: feedback Marcos S10.5 + ADR-034.

## ADRs referenced

- ADR-034 · cement determinismo (referenced en código motor)
- ADR-035 · referenced en código

## Cement OPS

Hub crítico consumidor (5 motores inbound) + productor reports cliente. AEPD decision tree es legal-critical (art. 33 RGPD 72h notification window · breach → AEPD obligatorio). NO LLM en reports es invariante institutional.
