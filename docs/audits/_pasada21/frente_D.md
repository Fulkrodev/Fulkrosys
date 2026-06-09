# FRENTE D · Auditoría del portal de compliance propio de Fulkro (dogfooding)

**Modo**: READ-ONLY · clasificación justificada leyendo el cuerpo real de cada fichero (no nombres/firmas).
**Alcance**: `m_compliance_monitor` (motor dogfooding) entero + `m_compliance` (motor de derechos RGPD del interesado) en lo relevante + API admin/cliente + frontend + scheduling Celery + presign MinIO.

**Leyenda de clase**:
- **1** = evalúa estado real del sistema (consulta BD / inspecciona config / cuenta algo / hace I/O real) y persiste/actúa.
- **2** = parcialmente real pero con dependencia ausente / degradación a placeholder / proxy débil / no cableado del todo.
- **3** = stub / constante hardcodeada / siempre devuelve "verde" sin evaluar nada.

**Leyenda sub-preguntas**: a=genera artefacto/reporte real · b=evidencia · c=audit_log R6 · d=¿refleja estado real? · e=frontend accionable.

---

## TL;DR verdicto

El dogfooding **es real, no un shell**. Los 19 checks (la doc los llama "17" + 2 de atom 10.1) tienen lógica genuina: hacen HTTP real, `to_regclass`/`information_schema`, `pg_class.relrowsecurity`, `socket+ssl` real al cert, `stat().st_mtime` de ficheros reales, lectura de `audit_log`/`backup_jobs`/`client_users`, e inspección de `os.environ`. **Ninguno devuelve un "green" hardcodeado**. Las 7 normas agregan outcomes reales desde la tabla `compliance_checks` con pesos que suman 1.0 y generan Markdown a partir del estado real. Los reportes se persisten en BD y se firman con `presigned_get_object` del SDK MinIO **real** (no string falso). Semáforo, alertas, auto-resolve, emails y scheduling Celery están todos cableados y registrados en el beat schedule. Frontend `tanstack-query` plenamente accionable.

**Dos huecos reales (de producto, no normativos)**:
1. **audit_log R6 (sub-item c) NO se emite** para las acciones administrativas del propio monitor (run check / resolve alert / sync registry / mark-reviewed / generate-report). No hay middleware global de audit. El monitor *lee* `audit_log` pero no *escribe* su propia traza. Es el gap más sustantivo.
2. **Varios checks degradan a `yellow`/`green` "informational"** cuando la infraestructura subyacente aún no está desplegada (tablas `fulkro_ropa_treatments`, `email_log`, columnas `consent_renewal_due`, ficheros MD de políticas). Es honestidad de estado (devuelven `unknown`/`yellow` con mensaje "atom X pendiente"), NO un falso verde — pero significa que hoy parte del score es "no sabemos" más que "cumplimos".

Distinción clave: **no hay hueco normativo** (la cobertura RGPD/LOPDGDD/LSSI-CE/NIS2/ISO/ENS/cookies está mapeada a artículos reales con pesos). El gap es **de producto/madurez**: (i) la auto-traza del monitor no entra en la cadena de hash R6, y (ii) algunos controles dependen de tablas/ficheros que se crean en atoms posteriores y mientras tanto puntúan como `unknown`.

---

## Tabla 1 · Los 19 checks (cuerpo real)

| # | Check | Clase | file:line del cuerpo | Qué evalúa de verdad | a | b | c | d | e | Qué falta |
|---|-------|-------|----------------------|----------------------|---|---|---|---|---|-----------|
| 1 | `cookies_banner_functional` | 1 | `checks.py:139-155` | HTTP real GET a `/legal/cookies` vía `_http_get` (`checks.py:127-133`), evalúa código 200 | sí (reporte) | n/a | no | sí | sí | — |
| 2 | `rgpd_endpoints_responding` | 1 | `checks.py:161-185` | HTTP real a 3 rutas portal RGPD; 404/0→red, 401/403→green | sí | n/a | no | sí | sí | proxy (existencia de ruta, no funcionalidad) |
| 3 | `ssl_cert_expiry` | 1 | `checks.py:191-231` | `socket.create_connection`+`ssl.wrap_socket`, parsea `notAfter` real, días restantes | sí | n/a | no | sí | sí | skip green en http/localhost (dev) |
| 4 | `backups_integrity` | 1 | `checks.py:237-272` | `SELECT MAX(completed_at) FROM backup_jobs WHERE status='completed'`, umbral 48h/7d | sí | sí (M26) | no | sí | sí | `unknown` si tabla M26 no desplegada |
| 5 | `audit_logs_continuity` | 1 | `checks.py:278-296` | `SELECT MAX(created_at) FROM audit_log`, gap 24h/2d | sí | sí | no (lee, no escribe) | sí | sí | — |
| 6 | `dpo_email_working` | 2 | `checks.py:302-341` | Verifica formato de alias + cuenta `email_log` 90d **si la tabla existe**; si no, green "configured" | sí | parcial | no | parcial | sí | tabla `email_log` ausente → green optimista sin tráfico verificado |
| 7 | `security_txt_reachable` | 1 | `checks.py:347-360` | HTTP real `/.well-known/security.txt`, exige `Contact:` | sí | n/a | no | sí | sí | — |
| 8 | `privacy_policy_freshness` | 2 | `checks.py:366-401` | `Path.exists()` + `st_mtime` de MD real; usa **mtime de fichero** como proxy de "revisión" | sí | sí (fichero) | no | parcial | sí | si MD no existe → yellow "atom 9.bis.4 pendiente"; mtime ≠ revisión real (un `git checkout` lo resetea) |
| 9 | `breach_workflow_ready` | 2 | `checks.py:407-413` | Solo `to_regclass('fulkro_breach_notifications')`; green = "tabla presente" | sí | parcial | no | parcial | sí | comprueba existencia de tabla, NO que el workflow 72h funcione |
| 10 | `sub_processor_dpa_expirations` | 1/2 | `checks.py:419-447` | Si tabla `fulkro_ropa_treatments`+col `dpa_expires_at`: `SELECT ... < NOW()+60d` real; si no, yellow | sí | sí (cond.) | no | sí (cond.) | sí | tabla aún no desplegada → yellow "atom 9.bis.3 pendiente" |
| 11 | `nis2_vulnerability_inbox` | 2 | `checks.py:453-475` | HTTP a security.txt + extrae línea `Contact:`; green si declara email | sí | parcial | no | parcial | sí | proxy débil: green por *declarar* email, sin verificar que el buzón se monitoriza |
| 12 | `rls_coverage_percentage` | 1 | `checks.py:481-531` | `information_schema.columns` (project_id/client_id) ∩ `pg_class.relrowsecurity=true`; % real | sí | sí | no | sí | sí | — (uno de los más fuertes) |
| 13 | `dpa_template_version` | 2 | `checks.py:537-564` | `Path.exists()`+`st_mtime` del DOCX, umbral 24m | sí | sí (cond.) | no | parcial | sí | si DOCX no existe → yellow; mtime como proxy de "revisión" |
| 14 | `sub_processors_list_freshness` | 2 | `checks.py:570-592` | `Path.exists()`+`st_mtime` del MD, umbral 120d | sí | sí (cond.) | no | parcial | sí | mismo proxy mtime; yellow si ausente |
| 15 | `ropa_review_due` | 1/2 | `checks.py:598-629` | `SELECT MAX(last_reviewed_at) FROM fulkro_ropa_treatments` real si existe; umbral anual | sí | sí (cond.) | no | sí (cond.) | sí | tabla aún no desplegada → yellow |
| 16 | `isms_docs_review_due` | 2 | `checks.py:635-677` | Itera 5 MD ISMS, `exists()`+`st_mtime`, missing/aging/overdue | sí | sí (cond.) | no | parcial | sí | mtime proxy; red si faltan ficheros |
| 17 | `cookie_consent_renewal_24month` | 1/2 | `checks.py:683-726` | `SELECT SUM(consent_renewal_due<NOW())...FROM client_users` real si col existe; si no, yellow | sí | sí (cond.) | no | sí (cond.) | sí | columna aún no desplegada → yellow "atom 9.bis.1 pendiente" |
| 18 | `admin_actions_audit_logged` | 1 | `checks.py:739-799` | `SELECT COUNT(*) FROM audit_log WHERE usuario=ANY(:emails) AND timestamp>cutoff` 24h/7d real | sí | sí | no (lee) | sí | sí | lista admin hardcodeada a `marcos@fulkro.es` (`checks.py:734-736`) — correcto para single-admin pero frágil |
| 19 | `marketing_analytics_opt_in_only` | 1 | `checks.py:821-854` | Inspecciona `os.environ` de 8 claves de analítica (`checks.py:809-818`); green si ninguna set | sí | n/a | no | sí | sí | binario env-presence; green legítimo dado privacy-by-design (sin analítica) |

**Conclusión Tabla 1**: 0 checks clase 3. ~9 son clase 1 sólida (HTTP/SQL/SSL/env reales). ~10 son clase 2 por *dependencia ausente* (tabla/columna/fichero que se crea en atoms posteriores) o por *proxy mtime* (usar `st_mtime` de un fichero como prueba de "revisión documental"). **Ninguno devuelve un verde constante fabricado**: cuando no pueden evaluar, devuelven `yellow`/`unknown` con mensaje honesto ("atom X pendiente"), que el scoring trata como 0.5 (precaución), no como pase. El registry (`checks.py:860-1036`) mapea los 19 con categoría, cadencia, severidad y base regulatoria explícita; el runner (`checks.py:1049-1057`) captura excepciones → `unknown` (no green silencioso).

---

## Tabla 2 · Las 7 normas (cuerpo real)

Todas heredan de `NormaModule` (`normas/base.py:56`). El scoring real está en `base.py:87-108` (green=1.0, yellow=0.5, unknown=0.5, red=0.0, ponderado). Los outcomes **se agregan desde la tabla `compliance_checks` real** en `norma_reports_service.py:157-193` (si falta la fila → `unknown`, no green).

| Norma | Clase | file:line del cuerpo | checks_owned (reales) | pesos suman 1.0 | a | b | c | d | e |
|-------|-------|----------------------|------------------------|------|---|---|---|---|---|
| RGPD UE 2016/679 | 1 | `rgpd_ue_2016_679.py:25-118` | 8 checks (endpoints, breach, privacy, dpa, sub-proc x2, ropa, dpo) | sí (`:42-51`) | sí | sí | no | sí | sí |
| LOPDGDD 3/2018 | 1 | `lopdgdd_3_2018.py:20-83` | 3 (dpo_email, breach, privacy) | sí (`:32-36`) | sí | sí | no | sí | sí |
| LSSI-CE 34/2002 | 1 | `lssi_ce_34_2002.py:19-89` | 2 (privacy, security_txt) | sí (`:30-33`) | sí | sí | no | sí | sí |
| NIS2 UE 2022/2555 | 1 | `nis2_ue_2022_2555.py:21-97` | 4 (security_txt, vuln_inbox, ssl, breach) | sí (`:34-39`) | sí | sí | no | sí | sí |
| ISO 27001:2022 | 1 | `iso_27001_2022.py:22-105` | 5 (ssl, backups, audit, rls, isms_docs) | sí (`:36-42`) | sí | sí | no | sí | sí |
| ENS RD 311/2022 | 1 | `ens_rd_311_2022.py:21-107` | 4 (audit, backups, rls, ssl) | sí (`:42-47`) | sí | sí | no | sí | sí |
| AEPD Cookies 2020 | 1 | `aepd_cookies_2020.py:19-97` | 2 (banner, consent_renewal_24m) | sí (`:32-35`) | sí | sí | no | sí | sí |

**Conclusión Tabla 2**: las 7 normas son clase 1. Cada `generate_report_md` produce Markdown real a partir de los outcomes (no plantilla con datos fijos): emoji por estado, mensaje del check, referencia al artículo concreto. El registry valida que los pesos sumen 1.0 al registrar (`base.py:205-211`, `registry.py:27`). Checks transversales (p.ej. `ssl_cert_expiry` lo poseen NIS2+ISO+ENS) están soportados (`registry.py:39-46`). La calidad del *score* de cada norma es exactamente tan buena como los checks subyacentes — es decir, las normas que dependen mucho de checks clase-2 (RGPD: breach/dpa/ropa/sub-proc dependen de tablas aún no desplegadas) hoy puntúan con mucho `unknown`=0.5, reflejando madurez parcial honesta.

---

## Tabla 3 · Semáforo / alertas / sync / reportes / presign

| Componente | Clase | file:line del cuerpo | Veredicto |
|-----------|-------|----------------------|-----------|
| Semáforo global (`overall`) | 1 | `api.py:64-110` | Agrega `COUNT` real por status desde `compliance_checks`; red>0→red, yellow/unknown>0→yellow. Estado **real**, no estático. |
| `run_check` (persist + estado) | 1 | `service.py:125-190` | Persiste `last_result`, `status`, `last_run_at`, `next_run_at`, `consecutive_failures`. Real. |
| Alertas (crear/auto-resolve) | 1 | `service.py:147-190`, `:406-427` | Crea `ComplianceAlert` en yellow/red o unknown×3; auto-resuelve al volver green. Lifecycle real. |
| Email alertas (HIGH inmediato / digest) | 1 | `service.py:208-316` | Render MJML real + `get_email_sender().send`, marca `email_sent_at`. Degradación graceful en except. |
| Sync registry | 1 | `service.py:88-121` | Upsert filas desde `CHECK_REGISTRY`. Real. |
| Scheduling Celery (checks) | 1 | `tasks.py:30-89` + `celery_app.py:283-286` | 4 tareas registradas en beat (daily/weekly/monthly/quarterly). Real. |
| Scheduling Celery (norma reports) | 1 | `norma_tasks.py:61-62` + `celery_app.py:248-252` | `build_beat_entries()` auto-registra una entrada por norma desde el registry. Real. |
| Reporte semanal status | 1 | `service.py:341-383` + `:430-475` | Genera Markdown real desde filas + persiste `ComplianceReport`. |
| Reporte por norma | 1 | `norma_reports_service.py:67-124` | Agrega outcomes reales, score, MD+JSON, persiste `FulkroComplianceNormaReport`, ship a storage, alerta si <85 o critical. |
| **Signed URL (presign MinIO)** | 1 | `reports_service.py:120-157` → `minio_client.py:53-62`,`:148-151` | `client.presigned_get_object(bucket, key, expires=7d)` del SDK **real** `minio.Minio`. **NO es string falso.** En dev escribe a carpeta Desktop; en prod sube a MinIO + presign. Degradación a `inline` si MinIO no disponible (honesto). |
| Frontend monitor | 1 | `frontend/app/(admin)/admin/compliance/monitor/page.tsx:97-333` | `useQuery`/`useMutation` reales contra la API; trigger check, resolve alert, sync, descarga `signed_url`. Polling 60s. Plenamente accionable. |
| Frontend norma-reports | 1 | `frontend/app/(admin)/admin/compliance/norma-reports/page.tsx` (existe) | Página dedicada presente. |

---

## audit_log R6 (sub-item c) — análisis transversal

- **Los checks LEEN audit_log** de verdad: `check_audit_logs_continuity` (`checks.py:287`) y `check_admin_actions_audit_logged` (`checks.py:763-779`) consultan `audit_log` (R6, cadena de hash) para verificar continuidad y traza de acciones admin. Eso es dogfooding correcto del propio R6.
- **El monitor NO ESCRIBE audit_log** para sus propias acciones administrativas. Las rutas `POST /checks/{name}/run` (`api.py:139-162`), `POST /alerts/{id}/resolve` (`api.py:184-201`), `POST /sync-registry` (`api.py:225-230`), `POST /norma-reports/{key}/run` (`norma_reports_api.py:157-172`) y `POST /reviewed/{id}` (`norma_reports_api.py:176-195`) hacen `db.commit()` pero **no emiten ninguna fila en `audit_log`**. No existe middleware global de audit (`backend/app/middleware/` solo contiene `csp.py` y `marcos_timesheet_middleware.py`; `main.py` no añade audit middleware). Por tanto, **c = NO** para todo el motor de monitorización.
- Matiz: el motor *hermano* `m_compliance` (derechos del interesado) sí lee/preserva `audit_log` en exports DSAR y erasure (`rgpd_services.py:283-318`, `:564` `audit_log_preserved=TRUE`), lo cual es la cara cliente del RGPD, no el dogfooding.

---

## Hueco normativo-real vs hueco-de-producto

**NO hay hueco normativo de cobertura**: las 7 normas mapean a artículos concretos (RGPD 15/17/20/28/30/33/37-38, LOPDGDD 11/34.5/74, LSSI-CE 10/16, NIS2 21.2.b/.h/23, ISO A.8.13/.15/.24/A.5.18/§7.5, ENS op.exp.8/.10/op.acc.4/mp.s.2, AEPD Cookies §4.2/§4.4) con pesos normalizados. El conjunto de 19 controles cubre las obligaciones operativas verificables automáticamente.

**Huecos de PRODUCTO (madurez), no de norma**:
1. **Auto-traza R6 ausente** (el más importante): las acciones del monitor no entran en la cadena de hash inmutable. Un auditor ENAC que mire "¿quién disparó este check / resolvió esta alerta?" no encuentra traza R6. Dado que la plataforma *vende* trazabilidad ENAC R6, que su propio órgano de compliance no se auto-registre es una incoherencia de dogfooding.
2. **Dependencias de infraestructura aún no desplegadas** degradan ~10 checks a `unknown`/`yellow` informational (`fulkro_ropa_treatments`, `email_log`, `consent_renewal_due`, MD de políticas, DOCX DPA). El score actual mezcla "cumplimos" con "aún no podemos medirlo". Honesto (no falso verde) pero el % de hoy no es interpretable como cumplimiento neto.
3. **Proxies débiles**: `st_mtime` de ficheros como prueba de "revisión documental" (checks 8/13/14/16) — un `git clone`/`checkout` resetea mtime y falsea la frescura; `nis2_vulnerability_inbox`/`dpo_email_working` aceptan green por *declarar* un contacto sin verificar que el buzón se monitoriza realmente.

---

## VEREDICTO FINAL

**El dogfooding es REAL, no un demo shell.** Hay lógica de evaluación genuina en los 19 checks (HTTP, SQL contra `audit_log`/`backup_jobs`/`client_users`/`pg_class`/`information_schema`, SSL socket real, `os.environ`, `st_mtime`), 7 normas que agregan outcomes reales con pesos verificados, persistencia en 3 tablas (`compliance_checks`, `compliance_alerts`/`reports`, `fulkro_compliance_norma_reports`), presign MinIO auténtico del SDK, scheduling Celery registrado en el beat, emails MJML reales y un frontend plenamente accionable. **Cero checks clase 3 (placeholder green).**

Las reservas son de **madurez/producto**, no de fachada: (1) el monitor no se auto-registra en R6 — gap de coherencia dogfooding que un auditor notaría; (2) parte del estado es `unknown` porque las tablas/ficheros subyacentes se crean en atoms posteriores; (3) algún proxy (mtime, declaración-de-contacto) es más débil que la obligación normativa que pretende cubrir. Todo ello documentado honestamente en los propios mensajes de los checks ("atom X pendiente"), sin falsos verdes.

**Clasificación global del frente: clase 1 con dos asteriscos** (auto-traza R6 + dependencias de infra pendientes).
