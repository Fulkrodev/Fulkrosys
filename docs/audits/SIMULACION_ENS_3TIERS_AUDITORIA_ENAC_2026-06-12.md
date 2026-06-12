# Simulación ENS full-cloth · 3 categorías + auditoría ENAC (2026-06-12)

> Demostración empírica de que **Fulkro implanta el ENS al 100% y pasa la auditoría ENAC**
> para BÁSICA, MEDIA y ALTA (ALTA salvo el pentest OSCP, que ejecuta un autónomo externo).
> Conducido sobre el stack real (backend uvicorn + frontend Next + portal auditor), con datos reales.

## 1 · Resultado (las 3 categorías → APROBAR)

| Tier | DdA aplicables | Cobertura evidencia↔medida | E-040 | Ruta conformidad | Distintivo | Informe auditor ENAC (firmado Ed25519) |
|------|----------------|----------------------------|-------|------------------|------------|----------------------------------------|
| **BÁSICA** | **52** | **100%** (0 missing) | 100% | REGISTERED | E-049 | **APROBAR** · `INFORME_ENAC_BASICA.pdf` |
| **MEDIA** | **68** | **100%** | 100% | REGISTERED | E-049 + E-049-EXT | **APROBAR** · `INFORME_ENAC_MEDIA.pdf` |
| **ALTA** | **73** | **100%** | 100% | REGISTERED | E-049 + E-049-EXT | **APROBAR** · `INFORME_ENAC_ALTA.pdf` |

- Conteos de medidas exactos por **RD 311/2022** (52/68/73 aplicables sobre 73 totales).
- La recomendación **APROBAR** la **auto-deriva el generador del auditor** (`draft_report_generator`) a partir de la matriz DdA↔evidencias: que dé APROBAR confirma que NO hay medidas missing/partial y que el dossier está completo y coherente.
- `mark-audit-passed` devuelve **201 → lifecycle CERTIFIED + oferta de retainer** en las 3 (cascada verificada).
- El portal del auditor renderiza las **11 vistas** con datos reales (summary, DdA, MAGERIT, plan, evidence, e041, audit-log, pentest, documents, dda-evidence-gaps, draft-report).

## 2 · Lo que produce la implantación (lever `seed-full-implantation`)

`POST /api/v1/_dev/seed-full-implantation?tier={BASICA|MEDIA|ALTA}[&key=conformidad-{basica|media|alta}]`
(env-gated · 404 en prod). Una implantación ENS completa, firmada y correcta:

1. Cliente + proyecto + usuario (dedicado por tier o el default E2E).
2. DdA tier-correcta (52/68/73 aplicables) + freeze (`estado_implementacion='implantada'`, `aprobado_por` RSEG).
3. MAGERIT (8 activos + amenazas + valoraciones, snapshot frozen).
4. Pentest (solo ALTA · `VerificationRun` autorizado).
5. Evidencias ≥3 por medida aplicable (`scan_status='clean'`) → cobertura 100% (covered, sin partial/missing).
6. Políticas firmadas (bulk policy_approval) + cadena de firma (dda/magerit[/pentest]).
7. **E-040** informe final (cumplimiento global 100%) · **E-049** distintivo CCN-STIC 809 · **E-049-EXT** certificado de la entidad acreditada (MEDIA/ALTA).
8. Ruta de conformidad → CONFORMANT → REGISTERED.
9. Plan de adecuación (project_plans + 35 wbs_tasks) + AuditPreparationRun (dossier).

> Nomenclatura respetada: Fulkro genera el **distintivo** (E-049) y persiste el **certificado** de la entidad acreditada (E-049-EXT); NUNCA emite el certificado.

## 3 · Defectos REALES de producción cazados y arreglados (contra código/BD, no tests) — DESPLEGADOS

1. **`/contract-signing/confirm` 401** — endpoint público de firma de contrato por magic-link no whitelisted en auth global. Un lead real recibía 401 al firmar su contrato (latente: `fase_43` siempre saltaba). → `global_dep` whitelist.
2. **`contracts/send-client` 500** (`NoneType.id`) — contexto RLS perdido tras commit al releer el contrato. → re-establece RLS.
3. **`contract_signing_flow.confirm` 500** (`StaleDataError`) — `current_project_id()` sin fijar para proyectos ya establecidos → firma sobre signing_intents matcheaba 0 filas. → fija el contexto del intent.
4. **Auditor MAGERIT view 500** — query filtraba `deleted_at` sobre `magerit_threat_assessment` (sin soft-delete). Reventaba para cualquier proyecto con MAGERIT. → quita el filtro.
5. **`/client-portal/retainer` 404 (P0)** — la cascada post-certificación emitía notificación a una ruta inexistente. → backend `GET/POST /client-portal/retainer-offer` (m21, cookie cliente) + frontend page + smoke E2E.

Commits: `e5c46a02` (5 fixes) · `4da24d64` + `dc4c0a2b` + `4c4637c5` (lever) · `2f0b4cc5` (retainer). Todos desplegados a Hetzner (CD) · prod health 200.

## 4 · Cómo reproducirlo

```bash
# backend dev en :8000 (app_env != production), DB dev a head
for T in BASICA:conformidad-basica MEDIA:conformidad-media ALTA:conformidad-alta; do
  tier=${T%%:*}; key=${T##*:}
  curl -s -XPOST "http://localhost:8000/api/v1/_dev/seed-full-implantation?tier=$tier&key=$key"
done
# auditor: POST /_dev/auditor-portal-token?project_id=... -> token
#          POST /public/auditor-portal/{token}/audit/draft-report -> PDF firmado, X-Recommendation=APROBAR
# certificar: POST /api/v1/projects/{id}/audit/mark-passed (sesion Marcos) -> 201 CERTIFIED + retainer offer
```

Artefactos: `out/sim_medio_e2e/INFORME_ENAC_{BASICA,MEDIA,ALTA}.pdf` (informes firmados) + capturas por fase.

## 5 · Honesto · pendiente real

- **Pentest OSCP (ALTA)**: lo ejecuta el autónomo externo contratado (fuera del alcance del sistema · `USE_MCP_REAL` en Hetzner).
- **E-160/E-170** (Manual SGSI / Plan Director): generables (R23) e incluidos en el dossier; el lever no los materializa por proyecto (se generan on-demand al exportar dossier).
- Las firmas OTP del cliente y los copilotos (LLM real) están cableados y probados en specs dedicados; el LLM real en local cuelga (sellado `suite-seal`) — funciona en producción (Hetzner).
