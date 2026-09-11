# Índice de decisiones de arquitectura (ADR)

**Esta página es la puerta de entrada. Si buscas un ADR, empieza aquí.**

Antes del 2026-09-11 no había puerta de entrada, y quien abría el repo se
encontraba con esto: un `docs/adr/ADR-001` y un `docs/architecture/ADR-046`,
sin nada que explicara dónde estaban del 003 al 045 — ni que **ADR-003
significaba dos decisiones distintas según en qué carpeta miraras**.

## Las tres casas, y por qué son tres

| dónde | qué hay | por qué |
|---|---|---|
| `docs/spec/DECISIONS.md` | ADR-004 … ADR-052, en un solo fichero | La primera época. Formato monolítico de las sesiones 1-11. |
| `docs/architecture/ADR-XXX_*.md` | ADR-046 … ADR-055, ficha por decisión | El monolito creció y los diffs se volvieron ilegibles. Desde ADR-046 cada decisión tiene su fichero. |
| `docs/adr/ADR-XXX-*.md` | ADR-056 … ADR-061, ficha por decisión | Los de esta campaña. Misma convención que la anterior, otro directorio. |

Que sean tres no es una decisión: es sedimento. Unificarlo movería ficheros que
están enlazados desde commits, migraciones y comentarios de código, y ese trabajo
no compra nada que no compre esta tabla. Lo que sí era un defecto —y está
arreglado— era la **numeración duplicada**.

## Lo que estaba mal y se arregló el 2026-09-11

**Había dos ADR-001, dos ADR-002 … hasta dos ADR-005.** La serie nueva de
`docs/adr/` empezó en 001 sin mirar que la vieja ya usaba esos números. No era
teórico, ya confundía al propio repo:

| número | qué decía la serie vieja | qué decía la serie nueva |
|---|---|---|
| ADR-003 | el fallback de sesión de desarrollo por `APP_ENV` (citado en `CLAUDE.md` R4 y en el runbook de Hetzner) | «¿es escalable en horizontal?» |
| ADR-004 | no hacer videollamada propia (citado en `m_meetings`, `m20_workspace`, dos migraciones) | «una llamada al modelo que falla no es un éxito» |
| ADR-005 | el motor de mensajería con el cliente (citado en `m29_client_messaging`) | «el modelo en el proceso limita los workers» |

**Arreglo**: la serie nueva se renumeró a **ADR-056 … ADR-060** (y sigue: ADR-061), continuando la
secuencia global. Las referencias por ruta y las que apuntaban a la serie nueva
se actualizaron; las que apuntan a la vieja se dejaron intactas, que es lo que
debían decir desde el principio.

## Tres anomalías que este índice destapa y NO se han arreglado

**1. ADR-001, ADR-002 y ADR-003 (los históricos) no existen.** Están citados
—`CLAUDE.md:57` manda «ver ADR-003» para la regla R4, y
`docs/deploy/HETZNER_DEPLOY_RUNBOOK.md` lo repite— pero no hay ningún fichero ni
ninguna sección que los defina, ni en `DECISIONS.md` ni en ninguna otra parte:

```
$ grep -rn "ADR-003" docs/ | grep -v adr/ADR-058
docs/deploy/HETZNER_DEPLOY_RUNBOOK.md:94: ... el fallback de sesión dev de ADR-003
```

Una referencia a una decisión que nadie escribió es peor que ninguna referencia:
tiene forma de justificación. No se inventa aquí lo que decían, porque no consta.
Quien sepa qué decidieron esos tres, que los escriba.

**2. ADR-046 a ADR-052 están DUPLICADOS**, en `DECISIONS.md` y además como ficha
propia en `docs/architecture/`. El README de ese directorio dice que desde el 046
las decisiones viven en fichero separado, pero el monolito conserva su copia. En
la tabla de abajo se marcan; la ficha propia manda, porque es la que se edita.
Consolidarlas es trabajo de otro día, y hasta entonces conviene saberlo.

**3. Dos números que `CLAUDE.md` y `DECISIONS.md` no cuentan igual.** Salió al
verificar las referencias de [`ARCHITECTURE.md`](../../ARCHITECTURE.md):

| número | según `CLAUDE.md` | según `docs/spec/DECISIONS.md` |
|---|---|---|
| ADR-014 | «OAuth de sólo lectura siempre · nada destructivo automático» | «Portal ENS Radar admin-only» — de un subsistema **retirado** el 2026-06-07 |
| ADR-025 | «no crear tabla nueva si una existente ya cubre el caso» | «DB drift resolution: alinear modelo a realidad» |

Las dos doctrinas que describe `CLAUDE.md` son reales y se aplican; lo que no
cuadra es a qué número pertenecen. No se corrige aquí porque no consta cuál de
las dos versiones es la original, y adivinarlo sería inventar historia. Quien lo
sepa, que lo cierre.

## Convención para el siguiente

- El próximo es **ADR-062**, ficha propia en `docs/adr/`.
- Un número es de una sola decisión, para siempre. Antes de coger uno, mírese
  esta tabla.
- El título del fichero y el `# ADR-XXX` de la primera línea dicen el mismo
  número. Si no, este índice miente.

## Los sesenta

| # | decisión | dónde vive |
|---|---|---|
| ~~ADR-001~~ | *citado en el código, pero **no está escrito en ninguna parte*** | — |
| ~~ADR-002~~ | *citado en el código, pero **no está escrito en ninguna parte*** | — |
| ~~ADR-003~~ | *citado en el código, pero **no está escrito en ninguna parte*** | — |
| ADR-004 | Reuniones externas, panel A18 admin-only | `docs/spec/DECISIONS.md` |
| ADR-005 | M29 Client Messaging motor nuevo | `docs/spec/DECISIONS.md` |
| ADR-006 | Panel Settings + Email forward + Magic Link config | `docs/spec/DECISIONS.md` |
| ADR-007 | Orquestación guiada D17 Opción A | `docs/spec/DECISIONS.md` |
| ADR-008 | Brand identity completo | `docs/spec/DECISIONS.md` |
| ADR-009 | FULKRO NO implementa firma cualificada eIDAS/TSA | `docs/spec/DECISIONS.md` |
| ADR-010 | Cláusula firma C-001 + página "Cómo funciona la firma" portal cliente | `docs/spec/DECISIONS.md` |
| ADR-011 | Magic Links auditoría + ampliación + email destinatario configurable | `docs/spec/DECISIONS.md` |
| ADR-012 | Motor M30 Client Contacts (lista contactos por empresa) | `docs/spec/DECISIONS.md` |
| ADR-013 | Separación arquitectónica de portales · admin / radar / client | `docs/spec/DECISIONS.md` |
| ADR-014 | Portal ENS Radar admin-only · pipeline v2 + UI completa + tracking runs | `docs/spec/DECISIONS.md` |
| ADR-015 | role en BD (identidad invariante) vs capabilities en Settings (toggles operacionales) | `docs/spec/DECISIONS.md` |
| ADR-016 | Drift modelo SQLAlchemy ↔ BD real pendiente de auditoría | `docs/spec/DECISIONS.md` |
| ADR-017 | Coexistencia dual auth flow (admin cookie httpOnly · cliente Bearer localStorage) | `docs/spec/DECISIONS.md` |
| ADR-018 | Aceleración auth unificado (Mini-Fase 3.5 S11) tras bug regresión middleware | `docs/spec/DECISIONS.md` |
| ADR-019 | CSRF triple binding cliente | `docs/spec/DECISIONS.md` |
| ADR-020 | Tablas auth_sessions vs client_sessions separadas (cookie común) | `docs/spec/DECISIONS.md` |
| ADR-021 | Motors Auth Landing via FastAPI Global Dependency | `docs/spec/DECISIONS.md` |
| ADR-022 | Panel Admin Clientes /admin/clients | `docs/spec/DECISIONS.md` |
| ADR-023 | Dominio compartido m27 Conformity ↔ m28 Change Governance | `docs/spec/DECISIONS.md` |
| ADR-024 | Reuniones externas (NO videocall propio FULKRO) | `docs/spec/DECISIONS.md` |
| ADR-025 | DB drift resolution: alinear modelo a realidad cuando BD tiene semantic correcto | `docs/spec/DECISIONS.md` |
| ADR-026 | Workflow phase derivation · 8 fases lifecycle persisted + CASCADE fallback | `docs/spec/DECISIONS.md` |
| ADR-027 | OPCION D hibrido C1-preserve + documento-adopt para FASE 8.5 | `docs/spec/DECISIONS.md` |
| ADR-028 | Magic Links emails: Python inline renderer (supersede parcial ADR-011) | `docs/spec/DECISIONS.md` |
| ADR-029 | Cleanup CCN-STIC 804 v2017 legacy + reseed canónico diferido | `docs/spec/DECISIONS.md` |
| ADR-030 | Criterio WHITELIST_EXACT/PREFIX endpoints sin auth | `docs/spec/DECISIONS.md` |
| ADR-031 | MAGERIT hybrid mode no implementado · decisión arquitectónica | `docs/spec/DECISIONS.md` |
| ADR-032 | M20 chat encryption at-rest · Fernet local master key | `docs/spec/DECISIONS.md` |
| ADR-033 | Content-Security-Policy + hardening headers pre-deploy | `docs/spec/DECISIONS.md` |
| ADR-034 | Frontend wire-up obligatorio per atom | `docs/spec/DECISIONS.md` |
| ADR-035 | Sistema vivo guiado cronológico (post-SAN-D MB-13) | `docs/spec/DECISIONS.md` |
| ADR-036 | UI condicional per categoría B/M/A + arquetipo PYME (SAN-D MB-17) | `docs/spec/DECISIONS.md` |
| ADR-037 | AI Auditor pro contextualizado + threat profundo Magerit Libro II (SAN-D MB-15) | `docs/spec/DECISIONS.md` |
| ADR-038 | Portal cliente workspace continuo (SAN-D MB-14) | `docs/spec/DECISIONS.md` |
| ADR-039 | Notification Orchestrator simplificado modelo Marcos (SAN-D MB-16) | `docs/spec/DECISIONS.md` |
| ADR-040 | Auto-billing milestone + transferencia bancaria manual (SAN-D MB-18) | `docs/spec/DECISIONS.md` |
| ADR-041 | CRM workflow comercial lead→cliente · m13_commercial extension (SAN-D MB-19.A) | `docs/spec/DECISIONS.md` |
| ADR-042 | Magic-link policy híbrida final (post-SAN-D MB-19.B) | `docs/spec/DECISIONS.md` |
| ADR-043 | SAN-D learnings + iterative pattern (cierre SAN-D MB-19.C) | `docs/spec/DECISIONS.md` |
| ADR-044 | Commercial readiness checklist (cierre SAN-D MB-19.C) | `docs/spec/DECISIONS.md` |
| ADR-045 | Deploy handoff procedure Sesión 12 (cierre SAN-D MB-19.C) | `docs/spec/DECISIONS.md` |
| [ADR-046](../architecture/ADR-046_capability_vs_feature_flag_clarification.md) | Capability vs Feature Flag clarification + Q5.3 cement explicit | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-047](../architecture/ADR-047_intelligence_cross_motor_distributed_pattern.md) | Intelligence Cross-Motor · Distributed Pattern (NO new motor) | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-048](../architecture/ADR-048_backup_encryption_strategy.md) | Backup Encryption Strategy + Offsite Replication | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-049](../architecture/ADR-049_copilot_3_surfaces_architectural_intent.md) | Copilot Agent 14 · 3 surfaces architectural intent · NO duplicate | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-050](../architecture/ADR-050_copilot_admin_guided_mode_vision_defer_mb14.md) | Copilot ADMIN guided mode end-to-end ENS lifecycle · VISIÓN cement · DEFER MB-14 polish  | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-051](../architecture/ADR-051_firma_firmas_hub_distinct_architectural_intent.md) | `firma/` vs `firmas-hub/` · 2 surfaces architectural intent · NO duplicate | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-052](../architecture/ADR-052_copilot_sse_streaming_distinct_intent.md) | Copilot SSE streaming wire-up · distinct intent vs generic `/agents/{id}/invoke` | ficha propia · `docs/architecture/` · **también en el monolito** |
| [ADR-053](../architecture/ADR-053_cloud_first_architecture.md) | Cloud-First Architecture · Unified `m_cloud_connectors` layer sobre M16 OAuth | ficha propia · `docs/architecture/` |
| [ADR-054](../architecture/ADR-054_project_scoped_admin_ux.md) | Project-Scoped Admin UX · Active Project Context Pattern | ficha propia · `docs/architecture/` |
| [ADR-055](../architecture/ADR-055-auto-remediation.md) | Auto-Remediación (cloud safe-tier AUTO + risky-tier autorizado) + Agente on-prem blindad | ficha propia · `docs/architecture/` |
| **[ADR-056](ADR-056-postgres-demo-sin-age.md)** | El perfil demo usa la imagen oficial de PostgreSQL, sin Apache AGE ni pgAudit | ficha propia · `docs/adr/` |
| **[ADR-057](ADR-057-imagen-backend-sin-instrumental-pentest.md)** | La imagen del backend se parte en dos: aplicación y instrumental de pentest | ficha propia · `docs/adr/` |
| **[ADR-058](ADR-058-escalabilidad-horizontal.md)** | ¿Es escalable en horizontal? Medido con dos réplicas | ficha propia · `docs/adr/` |
| **[ADR-059](ADR-059-llamada-llm-fallida-no-es-exito.md)** | Una llamada al modelo que falla no puede quedar registrada como éxito | ficha propia · `docs/adr/` |
| **[ADR-060](ADR-060-el-modelo-en-el-proceso-limita-los-workers.md)** | El número de workers no lo limita la CPU: lo limita la memoria del modelo | ficha propia · `docs/adr/` |
| **[ADR-061](ADR-061-el-eje-de-dimensiones-y-la-dimension-no-afectada.md)** | El eje de dimensiones: una dimensión no afectada no se adscribe a ningún nivel | ficha propia · `docs/adr/` |