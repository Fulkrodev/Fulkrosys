# ADR-055 · Auto-Remediación (cloud safe-tier AUTO + risky-tier autorizado) + Agente on-prem blindado

**Estado**: ACEPTADO (2026-06-13) · supersede CONTROLADO de ADR-014.
**Decisión Marcos**: postura híbrida (lo que no supone riesgo → AUTO · lo que supone riesgo → implantación perfecta + autorización previa) · alcance cloud + agente on-prem totalmente blindado · backend + frontend + BD.

## Contexto

Hasta hoy FULKRO **detecta** gaps cloud (`m_cloud_connectors/gap_rules.py`), **prioriza**, **genera plan** y **re-verifica** (`m08_verification/remediation/retest_runner.py`), pero **aplicar** el arreglo lo hace una persona a mano (ADR-014: OAuth read-only · `remediation_orchestrator.py` solo trackea estado). El cliente MEDIA no debería necesitar un humano por cada misconfig trivial; el cliente ALTA sí mantiene al pentester para hallazgos de host.

## Decisión

Introducir un **motor de remediación** (`m_remediation`) que **aplica** arreglos, acotado por una **política de riesgo determinista** (R1: ninguna decisión de riesgo la toma un LLM):

### Niveles de riesgo (clasificación estática por `action_type`)

| Tier | Definición | Ejecución | Ejemplos |
|------|-----------|-----------|----------|
| **SAFE_AUTO** | Reversible · sin impacto en disponibilidad/acceso | Automática (si cliente habilitó auto-remediación) | cifrar bucket, bloquear acceso público, activar logs/auditoría, versionado, forzar MFA condicional, política de contraseñas, hardening sshd, regla firewall |
| **GUARDED** | Puede afectar acceso/disponibilidad | **Autorización previa** (reusa `CloudGap` approval) + snapshot obligatorio + verify + auto-rollback si falla | rotar clave, cambiar política IAM no-destructiva, desactivar protocolo legacy |
| **BLOCKED** | Destructivo/irreversible | **Nunca auto** · solo plan; lo aplica un humano externo | borrar recurso, cambios de red/routing, eliminar principal IAM |

### Carve-out controlado de ADR-014
- `read-only` sigue siendo el **DEFAULT**. La escritura es **opt-in por conector** (`cloud_connectors.remediation_enabled` + `auto_remediation_policy` + `granted_write_scopes`) y requiere consentimiento explícito de scopes de escritura por el cliente.
- **Kill-switch en 3 capas** (fail-closed): env global `FULKRO_REMEDIATION_ENABLED` (default `false`) · flag por conector · política por proyecto. Si cualquiera está en off → NO se aplica nada.

### Ciclo de ejecución seguro (idéntico cloud y host)
1. **preflight** — releer estado actual; si ya cumple → no-op `SUCCEEDED` (idempotente).
2. **snapshot** — persistir estado previo en `remediation_snapshots` (rollback).
3. **apply** — ejecutar acción (idempotente · blast-radius guard: rechaza si afecta > N recursos sin confirmación).
4. **verify** — releer estado; afirmar propiedad deseada.
5. **rollback** — si verify falla → restaurar desde snapshot → `ROLLED_BACK`.
6. **audit** — cada paso a `audit_log` (R6 hash chain) + `remediation_jobs`.

### Agente on-prem blindado (`m_remediation_agent` dentro de `m_remediation`)
Para CVEs/hardening de servidores propios del cliente (FULKRO no tiene acceso de escritura a su red). Defensa en profundidad:
- **Sin puertos entrantes en el cliente**: el agente **hace pull** de comandos (cero superficie de ataque inbound).
- **Enrollment Ed25519**: token de un solo uso → el agente genera su par de claves; el servidor guarda la pública. Auth mutua.
- **Comandos firmados Ed25519 por el servidor** + **allowlist de playbooks** horneada en el agente: el agente **RECHAZA** cualquier comando que no esté en su catálogo de playbooks firmados (dato ≠ instrucción · espejo de la doctrina anti-injection M8). **Nada de shell arbitrario.**
- **Mínimo privilegio**: playbooks específicos, idempotentes, con pre-snapshot + rollback + verify.
- **Tiering idéntico**: playbooks SAFE_AUTO corren solos; GUARDED requieren autorización; destructivos BLOCKED.
- **Heartbeat + revocación**: el servidor revoca un agente; el agente se auto-desactiva si no valida firma/heartbeat.
- **Audit R6**: cada comando + resultado se reporta, hash-chained, append-only → evidencia al dossier ENAC.

## Consecuencias
- ENAC-defendible: toda auto-acción es reversible, acotada por política y trazada (R6).
- Default seguro: sin habilitar nada explícito, el comportamiento es idéntico al de hoy (read-only).
- Deuda gestionada: los ejecutores de escritura por proveedor y los playbooks de host crecen incrementalmente detrás de la interfaz `RemediationWriter`/playbook; el núcleo (clasificar/snapshot/apply/verify/rollback/audit/kill-switch) es el que debe ser perfecto.

## Tablas nuevas
- `remediation_jobs` — unidad de trabajo (origen: cloud gap_id o host finding_id) · action_type · tier · status · snapshot_ref · result · RLS project_id.
- `remediation_snapshots` — estado previo para rollback · RLS project_id.
- `remediation_agents` — enrollment de agente host · pubkey · status · heartbeat · capabilities · RLS.
- `remediation_agent_commands` — bundles de comando firmados que el agente hace pull · RLS.
- `cloud_connectors` (extend) — `remediation_enabled` · `auto_remediation_policy` · `granted_write_scopes`.

## Doctrinas honradas
R1 (riesgo determinista · no LLM) · R6 (hash chain) · R29 (cliente friendly) · R30 (admin tutor) · ADR-013 (doble pool) · ADR-025 (reusa `CloudGap` approval para GUARDED) · OPS-026 (DRY) · Sub-atom 5.A (audit_log 3-way OR).
