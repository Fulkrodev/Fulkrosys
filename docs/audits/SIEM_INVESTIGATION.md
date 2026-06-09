# SIEM Investigation · ¿Necesita FULKRO un SIEM para quedar "perfecto"?

> Investigación READ-ONLY · 2026-06-06 · arquitecto ciberseguridad/cumplimiento ENS
> Worktree `~/fulkro-portales` (rama `batch2-fase0-recorrido`) · sin cambios de código.
> Veredicto resumido: **(A) NO hace falta un SIEM dedicado pre-piloto MEDIA. (B) SÍ conviene una capa ligera de correlación/alerta de seguridad sobre lo existente para op.mon, y una postura de producto "verificar/documentar SIEM del cliente" en MEDIA, integrar para ALTA.**

---

## 1. ¿El ENS exige un SIEM? Mapeo RD 311/2022 Anexo II

El ENS **no nombra "SIEM" en ningún sitio**. Exige *capacidades* (registro, detección, métricas, vigilancia) que en la práctica suele cubrir un SIEM/SOC, pero admite implementaciones más ligeras según categoría. Niveles de aplicabilidad (ENS 2022, código de colores Anexo II: verde = desde BÁSICA, amarillo = desde MEDIA, rojo = sólo ALTA):

| Medida | Qué exige | ¿Desde qué categoría? | ¿Implica SIEM? |
|---|---|---|---|
| **op.exp.8** Registro de la actividad | Logs de actividad de usuarios, con **trazabilidad y correlación de eventos entre sistemas** | **BÁSICA+** (refuerza en MEDIA/ALTA: relojes sincronizados, correlación) | Parcial. La "correlación entre sistemas" en MEDIA/ALTA empuja hacia agregación centralizada de logs (capacidad-SIEM), no necesariamente un producto SIEM. |
| **op.exp.9** Registro de la gestión de incidentes | Registrar todas las actuaciones de gestión de incidentes | **BÁSICA+** (op.exp.9 pasó a aplicar desde nivel bajo en ENS 2022) | No. Es gestión de casos (ticketing/runbook), no correlación. |
| **op.exp.10** Protección de los registros de actividad | Integridad/retención/no alteración de logs | **MEDIA+** | No directamente, pero el almacén de logs debe ser inviolable (hash-chain, WORM). |
| **op.mon.1** Detección de intrusión | IDS/IPS, detección de actividad anómala | **MEDIA+** | **Sí, núcleo SIEM/IDS.** Primera medida que realmente empuja a capacidad de detección. |
| **op.mon.2** Sistema de métricas | Métricas de eficacia del sistema de seguridad (incidentes, cobertura, tiempos) | **ALTA** | Parcial. Cuadro de mando de métricas; un SIEM lo facilita pero no es obligatorio. |
| **op.mon.3** Vigilancia | Vigilancia continua / supervisión | **BÁSICA+** (NUEVA en ENS 2022, aplica desde bajo) | Parcial. Revisión periódica de logs + alertas; ligero en BÁSICA, continuo/SOC en ALTA. |

**Conclusión normativa:**
- **BÁSICA**: op.exp.8/9 + op.mon.3 → cubrible con logging + revisión periódica. **No requiere SIEM.**
- **MEDIA** (objetivo piloto): aparece **op.mon.1 (detección de intrusión)** y op.exp.10. Aquí es donde se necesita *alguna* capacidad de detección/correlación. **No exige un producto SIEM acreditado**, pero el auditor ENAC esperará evidencia de detección de intrusiones y revisión de logs. Un IDS/HIDS + alertas suele bastar; muchas pymes MEDIA lo resuelven con Wazuh/IDS gestionado.
- **ALTA**: op.mon.2 + vigilancia continua → **en la práctica un SIEM/SOC 24/7** (propio o gestionado). Aquí sí es de facto obligatorio.

**CCN-STIC y herramientas oficiales:**
- CCN-STIC **808** (verificación del cumplimiento) marca que BÁSICA puede autoevaluarse y **MEDIA/ALTA exigen auditoría por entidad/auditor acreditado** — el auditor pedirá evidencia op.mon.
- CCN-STIC **818** (Herramientas de seguridad en el ENS) lista herramientas; CCN-STIC **1215** documenta el empleo seguro de GLORIA.
- **GLORIA** (CCN-CERT): plataforma de gestión de incidentes/amenazas por **correlación compleja de eventos** (SIEM), gratis de licencia **pero distribuida a organismos públicos** (requiere certificación del organismo). **MÓNICA NGSIEM** (Grupo ICA/CCN): NGSIEM nacional **certificado y clasificado ENS Categoría ALTA**, usable en sistemas ENS de cualquier categoría. Ambas se integran con CARMEN/CLAUDIA/LUCÍA/PILAR.
- **Implicación para FULKRO**: los clientes de FULKRO son **empresas privadas** que licitan a la AAPP (AMEND-012: la AAPP es customer-of-customer). **No suelen poder usar GLORIA/MÓNICA** (reservadas a AAPP), por lo que el SIEM del cliente será comercial/open-source (Wazuh, Elastic, Sentinel…). CCN **no "acredita SIEMs" para terceros**; sí certifica funcionalidades (caso MÓNICA, producto nacional CPSTIC).

Fuentes: [BOE RD 311/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191) · [CCN-STIC 808](https://www.ccn-cert.cni.es/es/800-guia-esquema-nacional-de-seguridad/518-ccn-stic-808-verificacion-del-cumplimiento-de-las-medidas-en-el-ens/file.html) · [CCN-STIC 818 herramientas](https://www.ccn-cert.cni.es/es/series-ccn-stic/800-guia-esquema-nacional-de-seguridad/527-ccn-stic-818-herramientas-de-seguridad-en-el-ens/file?format=html) · [GLORIA](https://www.ccn-cert.cni.es/soluciones-seguridad/gloria.html) · [MÓNICA NGSIEM](https://www.grupoica.com/-/monica_ngsiem_ccn_ica_sistemas_y_seguridad) · [ENS 2022 cambios op.mon](https://ciberseguridad.blog/el-nuevo-ens-2022-y-sus-principales-cambios/)

---

## 2. ¿Qué tiene ya FULKRO? (inventario capacidad-SIEM empírico)

### Lo que SÍ existe (fuerte)

| Capacidad | Dónde | Qué hace | ¿SIEM-like? |
|---|---|---|---|
| **Audit log inmutable hash-chain** | `backend/migrations/versions/d4f8b2a90001_audit_log_hash_chain_trigger.py` | `audit_log` con `seq BIGSERIAL`, trigger `fn_audit_log_hash_chain()` (SHA-256 encadenado, `pg_advisory_xact_lock`), triggers `fn_audit_log_immutable()` que **rechazan UPDATE/DELETE** (append-only), `fn_audit_track()` auto-captura INSERT/UPDATE/DELETE en **13 tablas críticas** (evidence, documents, contracts, invoices, projects, clients, categorizations, dda_entries, obligations, magerit_analysis, audit_findings, pentest_findings, document_versions), `fn_audit_log_verify_chain()` para integridad. | **Sí, núcleo de op.exp.8/op.exp.10.** Es un log de auditoría de negocio/datos inviolable — pero NO ingiere logs de SO/red/auth de servidor. |
| **Monitor de cumplimiento auto (dogfooding)** | `backend/app/motors/m_compliance_monitor/` (`checks.py` 40 KB, `normas/ens_rd_311_2022.py`) | Checks deterministas programados (Celery `tasks.py`/`norma_tasks.py`). El módulo ENS auto-aplicado cubre `audit_logs_continuity` (op.exp.8), `backups_integrity` (op.exp.10), `rls_coverage_percentage` (op.acc.4), `ssl_cert_expiry` (mp.s.2), `admin_actions_audit_logged` (op.exp.8 art.24.1). `check_audit_logs_continuity` alerta si `audit_log` no recibe filas en 24-48h (detecta middleware roto). | Parcial: es **control de cumplimiento periódico**, no detección de amenazas en tiempo real. |
| **Verificación técnica / pentest / vuln-scan (M8)** | `backend/app/motors/m08_verification/` | Scheduler nocturno Celery (ventana 22:00-06:00, `scheduler.py`), orquestador MCP (`mcp_executor_service.py`), runners reales: OpenVAS, Prowler, ScoutSuite, nmap, ZAP, Lynis, testssl, nuclei (`tools/*_runner.py`). Mapeo CVE→ENS y CIS→ENS (`ens_mapper.py`, `*_ens_mapper.py`, `mitre_mapper.py`), `kill_switch.py`, `zfp_engine.py` (zero-false-positive). | **Detección de vulnerabilidades point-in-time**, NO correlación continua de eventos. Cubre op.exp.5 (gestión vulnerabilidades), no op.mon.1 en sentido IDS continuo. |
| **Gestión de incidentes (M19)** | `backend/app/motors/m19_risk/incident_workflow_service.py` + `ccn_cert_decision_tree.py` | Máquina de estados CCN-STIC 817 (created→triaged→investigated→mitigated→resolved→closed), árbol de decisión routing CCN-CERT (internal / LUCÍA federation / notificación manual), deadlines 24h/72h, reloj art.33/LUCÍA. | **Sí, cubre op.exp.9** (registro gestión incidentes). Es case-management manual, NO genera incidentes por detección automática. |
| **Alertas proactivas (M18)** | `backend/app/motors/m18_communication/alert_service.py` + `alert_schemas.py` | Cola `alert_queue` con severity info/warning/critical + categorías + dispatch SSE `alert_new`. | Categorías son **de negocio/cumplimiento** (payment_overdue, audit_due, rgpd_72h, evidence_stale, workflow_blocked…), **NO eventos de seguridad** (login fallido, escalada de privilegios, anomalía de tráfico). |
| **SSE dispatcher** | `backend/app/core/sse_dispatcher.py` | Bus de eventos en tiempo real con replay buffer (ring-buffer, Last-Event-ID, Pattern #21). | Infra reusable para *empujar* alertas de seguridad si se construyera la capa. |
| **Observabilidad LLM (m_observability)** | `backend/app/motors/m_observability/` (355 LOC) | Coste LLM, top consumers, **anomaly alerts deterministas** (spike / sustained high / cost-cap). Lee `llm_interaction_log`. | Es observabilidad de coste LLM, **no seguridad**. Patrón de detección de anomalías reusable, pero fuera de alcance SIEM. |
| **Cloud connectors (M16/m_cloud_connectors)** | `backend/app/motors/m_cloud_connectors/` | OAuth read-only (ADR-014) a M365/Google Workspace/AWS/Azure, `gap_rules.py`, `diagnostic_gap_engine.py`, `remediation_orchestrator.py`. | Postura de configuración (CSPM ligero), **no streaming de eventos** de seguridad continuo. |

### Lo que NO existe (gaps reales vs un SIEM)

Búsqueda empírica negativa: `grep -riE "syslog|filebeat|fluentd|logstash|wazuh|elastic|opensearch"` en `backend/app` → **0 resultados de log-shipping/SIEM**. Los matches de "correlat" son falsos positivos (billing, retainer).

1. **No hay ingestión de logs de infraestructura**: SSH/auth (`/var/log/auth.log`), kernel, firewall, nginx/Caddy access, syslog del SO, Docker, PostgreSQL pgAudit hacia un colector central. El `audit_log` es **de aplicación/datos**, no de plataforma.
2. **No hay correlación de eventos de seguridad en tiempo real** ni reglas de detección (p.ej. N logins fallidos → alerta, IP nueva geo-anómala, escalada de privilegios).
3. **No hay IDS/IPS** (op.mon.1) ni FIM (file integrity monitoring) sobre el host.
4. **No hay cuadro de métricas de seguridad** (op.mon.2): MTTD/MTTR, % cobertura logging, incidentes/periodo.
5. **No hay vigilancia continua 24/7** (op.mon.3 nivel ALTA) — sólo checks diarios de cumplimiento.
6. **El módulo ENS auto-aplicado NO incluye ningún check op.mon** (sólo op.exp.8/op.exp.10/op.acc.4/mp.s.2). Gap directo de dogfooding para op.mon.1/op.mon.3.

---

## 3. Doble ángulo

### (a) FULKRO sobre sí mismo (dogfooding R7, ENS MEDIA)

**Para op.exp.8/op.exp.9/op.exp.10: BASTA lo existente** (audit_log hash-chain + compliance_monitor + incident workflow M19). Es de hecho mejor que la media del mercado.

**Gap honesto para op.mon en su propia categoría MEDIA:**
- **op.mon.1 (detección de intrusión)** aplica desde MEDIA y **FULKRO no lo tiene** sobre su propia plataforma. Hoy depende de pentest nocturno (point-in-time), no de detección continua.
- **op.mon.3 (vigilancia)** aplica desde BÁSICA y sólo está cubierto parcialmente por checks diarios de cumplimiento.

Para una auditoría MEDIA de FULKRO sobre sí mismo, el auditor ENAC podría señalar op.mon.1 como **no conformidad menor** si no hay *ninguna* detección de intrusión. Mitigantes ligeros aceptables en MEDIA: fail2ban + alertas, HIDS básico (auditd/Wazuh-agent en el único host Hetzner), revisión periódica documentada de logs nginx/auth. **No necesita un SIEM completo para su propio MEDIA**, pero sí cerrar el gap op.mon con algo más que checks de negocio.

### (b) FULKRO como producto para clientes

Distinción clave de modelo de negocio: FULKRO **implanta y verifica** el ENS; **no es el operador de seguridad 24/7 del cliente**. La responsabilidad de op.mon recae en la **infraestructura del cliente** (su SIEM/IDS, propio o gestionado por su MSSP/cloud).

- **MEDIA (piloto)**: FULKRO debe **guiar, verificar y documentar** que el cliente tiene capacidad de detección de intrusión (op.mon.1) y registro/protección de logs (op.exp.8/10). FULKRO ya aporta el verificador técnico (M8: OpenVAS/Prowler/ScoutSuite) que evidencia configuración, y puede generar la evidencia documental. **No debería operar el SIEM del cliente** — eso lo vende como retainer (R_MEDIO incluye "vuln semanal", podría ampliarse).
- **ALTA**: op.mon.2 + vigilancia continua hacen el SIEM/SOC de facto obligatorio en el cliente. FULKRO **debe integrarse/leer** del SIEM del cliente (o recomendar Wazuh gestionado / MSSP) y verificar métricas, NO construir un SIEM multi-tenant propio (rompería ADR-014 read-only y el alcance "implantador, no operador").

**Recomendación de producto**: FULKRO = capa de *verificación y evidencia* del op.mon del cliente, no SIEM-as-a-service. El retainer R_ALTO ya describe "SOC + DR drills" como servicio gestionado — ahí encaja la operación, externalizada o vía partner.

---

## 4. Opciones de mercado

| Opción | Encaje ENS | Coste/operación (consultor autónomo) | Integración stack Python/FastAPI+PG+Docker/Hetzner | Self-host vs gestionado |
|---|---|---|---|---|
| **Wazuh** (open-source SIEM/XDR) | **El mejor encaje ENS de facto en pymes españolas.** Reglas/decoders mapean op.acc.5, op.exp (incl. incident mgmt), mp.info.3; FIM, detección de intrusión host, vuln-detection. Muchos integradores ENS lo despliegan. No trae un "módulo ENS oficial CCN" empaquetado, pero sí compliance templates (PCI/GDPR/HIPAA) reutilizables y reglas adaptables a op.mon. | Licencia **0€** (open-source). Coste real = **operación**: 1 nodo Wazuh (manager+indexer+dashboard) consume RAM/CPU notables (~4-8 GB para indexer Elasticsearch/OpenSearch). Para un autónomo, la operación 24/7 es el verdadero coste. | Alta afinidad Docker (imágenes oficiales `wazuh/wazuh-manager`, indexer, dashboard via docker-compose). Agente en el host Hetzner + agentes en hosts del cliente. API REST consumible desde FastAPI. | **Self-host** viable en Hetzner para FULKRO-sobre-sí-mismo; **gestionado/cloud** recomendable si se ofrece a clientes ALTA. |
| **Elastic SIEM** (Elastic Security) | Bueno; detección + reglas, pero ENS lo cubres tú con reglas a medida. | Free tier limitado; features SIEM avanzadas requieren licencia de pago. Indexer pesado. | Beats/Agent + Elasticsearch. Más pesado de operar que Wazuh; solapa con OpenSearch que ya usarías bajo Wazuh. | Self-host pesado o Elastic Cloud (coste). |
| **Graylog** | Aceptable para agregación + alerting de logs; menos "XDR/IDS" que Wazuh. | Open-source core gratis; enterprise de pago. | Ingesta syslog/GELF sencilla; MongoDB+OpenSearch backend (más piezas). | Self-host. |
| **Microsoft Sentinel** (cloud-native, Azure) | Muy potente; encaje natural si el cliente ya es M365/Azure (FULKRO ya tiene conector M365/Azure). | **Pago por ingesta (GB/día)** — puede dispararse; no apto como gasto fijo de un autónomo, sí como coste pasable al cliente Azure. | API/Logic Apps; FULKRO podría leer incidentes vía Graph/Sentinel API. No self-host. | **Gestionado** (Azure). Bueno para clientes cloud-Azure, malo para FULKRO-sobre-sí-mismo en Hetzner. |

**Lectura para FULKRO**: para dogfooding propio en Hetzner y para clientes pyme, **Wazuh** es la opción canónica (coste de licencia 0, encaje ENS probado, Docker-friendly). Sentinel sólo cuando el cliente ya vive en Azure (y paga él la ingesta). Elastic/Graylog no aportan ventaja sobre Wazuh para este caso.

Fuentes: [Wazuh regulatory compliance](https://documentation.wazuh.com/current/compliance/index.html) · [Wazuh ENS (AI Security)](https://aisecurity.es/wazuh) · [Microsoft Learn ENS](https://learn.microsoft.com/es-es/compliance/regulatory/offering-ens-spain)

---

## 5. Recomendación concreta priorizada

### Veredicto: **(A) + (B)** — NO SIEM dedicado pre-piloto MEDIA; SÍ una **capa ligera de correlación/alerta de seguridad** sobre la infra existente, y postura de producto "verificar/documentar". **(C) Wazuh sólo cuando llegue ALTA o lo pida el cliente.**

**Por qué NO un SIEM completo ahora:**
1. El ENS MEDIA no exige un *producto* SIEM; exige *capacidad* de detección (op.mon.1) y registro/protección (op.exp.8/10), que FULKRO ya cubre al 80% (audit_log hash-chain + M8 + M19 + compliance_monitor).
2. Para un consultor autónomo single-host, operar un SIEM 24/7 es un coste operativo desproporcionado pre-revenue. **Sería prematuro.**
3. GLORIA/MÓNICA no aplican (son para AAPP; los clientes de FULKRO son privados).

### Plan por fases (reusando infra; respetando RLS, R6 hash-chain, ADR-014 read-only)

**FASE 0 — Pre-piloto MEDIA (crítico, esfuerzo bajo ~6-10h) · cerrar el gap op.mon de dogfooding sin SIEM:**
- Añadir **checks op.mon al módulo ENS auto-aplicado** (`m_compliance_monitor/normas/ens_rd_311_2022.py`): `intrusion_detection_present` (op.mon.1), `log_review_cadence` (op.mon.3). Aunque sean checks "¿está fail2ban/auditd activo y hay revisión periódica?", cierran la trazabilidad de dogfooding.
- En el host Hetzner: **fail2ban + auditd/journald hardening + nginx/Caddy access logs retenidos** y revisados; documentar la revisión periódica (op.mon.3). Coste casi nulo, evidencia suficiente para MEDIA.
- Generar **evidencia documental op.mon** para la auditoría (procedimiento de revisión de logs, política de retención) — reusa `m06_document_factory`/`m07_evidence`.
- *No tocar* audit_log hash-chain ni RLS.

**FASE 1 — Producto, soporte al cliente MEDIA (crítico para el negocio, parte ya hecho):**
- Posicionar FULKRO como **verificador/documentador** de op.mon del cliente: M8 (OpenVAS/Prowler/ScoutSuite) evidencia configuración; generar el entregable que demuestra que el cliente tiene IDS/registro. **No operar** el SIEM del cliente.
- Si el cliente no tiene detección: **recomendar Wazuh** (open-source) o su MSSP, y dejarlo en el plan/gap (M4/M17), no asumirlo FULKRO.

**FASE 2 — Capa ligera de correlación de seguridad propia (post-piloto, opcional, ~15-25h):**
- Construir un **detector de eventos de seguridad** reusando lo existente, NO un SIEM nuevo:
  - Nueva **categoría de seguridad en M18 `alert_service`** (`_VALID_CATEGORIES` += `auth_bruteforce`, `priv_escalation`, `anomalous_access`, `integrity_breach`).
  - **Reglas deterministas** estilo `m_observability.get_anomaly_alerts` (spike/sustained) pero sobre eventos de auth/acceso (N logins fallidos, IP nueva, acceso fuera de horario).
  - Empujar vía **SSE dispatcher existente** (`alert_new`) al panel admin.
  - Verificación periódica de integridad del hash-chain (`fn_audit_log_verify_chain`) como alerta de manipulación (op.exp.10).
- Esto da op.mon.1/op.mon.3 "ligero" propio sin desplegar Wazuh, manteniendo R6/RLS/ADR-014.

**FASE 3 — ALTA (cuando haya cliente ALTA o revenue, ~30-60h + operación):**
- **Integrar Wazuh** (self-host Hetzner para FULKRO + recomendado/gestionado para cliente): agentes en hosts, FIM, IDS host, dashboards.
- **op.mon.2 métricas**: cuadro de mando (MTTD/MTTR, cobertura logging, incidentes/periodo) — puede vivir como vista derivada FULKRO leyendo de Wazuh API + audit_log (read-only).
- **Vigilancia continua / SOC**: externalizar a partner/MSSP o vender como retainer R_ALTO ("SOC + DR drills" ya descrito). FULKRO **no debe** convertirse en SOC multi-tenant operado por un autónomo.

### Pre-piloto crítico vs post-piloto/ALTA

| Item | Cuándo | Esfuerzo |
|---|---|---|
| Checks op.mon en módulo ENS dogfooding + fail2ban/auditd + evidencia docs | **Pre-piloto (crítico)** | ~6-10h |
| Posicionamiento producto "verificar/documentar SIEM cliente" (ya 80% con M8) | **Pre-piloto (crítico)** | ~2-4h (entregable) |
| Capa ligera de correlación de seguridad propia (M18+SSE+reglas) | Post-piloto (nice-to-have) | ~15-25h |
| Integrar Wazuh + métricas op.mon.2 + vigilancia continua | ALTA / demand-driven | ~30-60h + operación |

### Honestidad sobre el esfuerzo / prematuridad
- Desplegar Wazuh **ahora** sería **prematuro y sobre-dimensionado**: añade operación 24/7 que un autónomo single-host no puede sostener, sin beneficio para el piloto MEDIA.
- El riesgo real pre-piloto es **op.mon.1 vacío en el dogfooding de FULKRO** (no conformidad menor potencial). Se cierra con horas, no con un SIEM.
- La regla rectora: **FULKRO implanta y verifica el ENS; no opera la seguridad 24/7**. El SIEM, cuando llegue, es del cliente (o partner), y FULKRO lo integra en modo read-only para evidenciar/medir.

---

## Apéndice · file:line de referencia
- Audit log hash-chain: `backend/migrations/versions/d4f8b2a90001_audit_log_hash_chain_trigger.py:60-130` (`fn_audit_log_hash_chain`, `fn_audit_log_immutable`, `fn_audit_track`, 13 tablas tracked).
- Módulo ENS auto-aplicado (cubre op.exp.8/10, op.acc.4, mp.s.2 · **sin op.mon**): `backend/app/motors/m_compliance_monitor/normas/ens_rd_311_2022.py:13-52`.
- Check continuidad logs op.exp.8: `backend/app/motors/m_compliance_monitor/checks.py:278-293` + `:739-755` (admin actions) + `:900-906` (regulatory_basis ENS op.exp.8).
- Alertas de NEGOCIO (no seguridad): `backend/app/motors/m18_communication/alert_service.py:23-37` (`_VALID_CATEGORIES`).
- Verificación técnica/pentest (point-in-time, no continuo): `backend/app/motors/m08_verification/scheduler.py`, `tools/openvas_runner.py`, `tools/prowler_runner.py`, `tools/scoutsuite_runner.py`, `ens_mapper.py`.
- Incidentes op.exp.9 (case-management manual): `backend/app/motors/m19_risk/incident_workflow_service.py:1-45`, `ccn_cert_decision_tree.py`.
- SSE bus reusable: `backend/app/core/sse_dispatcher.py`.
- Anomaly detection determinista (patrón reusable): `backend/app/motors/m_observability/README.md`.
- Negativo (no SIEM): `grep -riE "syslog|filebeat|fluentd|logstash|wazuh|elastic|opensearch" backend/app` → 0 resultados de log-shipping.
