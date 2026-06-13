# Activación en producción · Auto-remediación (ADR-055)

Por defecto, en prod NO se aplica nada (read-only · igual que hoy). Activación en 3 pasos:

## 1. Secretos en `.env.prod` (Hetzner · una vez)

```bash
# Clave de firma del servidor para el agente on-prem (32 bytes hex · ESTABLE).
# Sin esto, los agentes no pueden verificar comandos tras un reinicio del servidor.
python3 -c "import secrets;print('FULKRO_REMEDIATION_SIGNING_KEY='+secrets.token_hex(32))"

# Interruptor maestro global (kill-switch capa 1 · default false).
FULKRO_REMEDIATION_ENABLED=true
```

Añadir ambas líneas a `.env.prod` y recrear el backend (`docker compose -f
docker-compose.prod.yml --env-file .env.prod up -d backend`). La clave de firma es
secreto: guardarla en el gestor de secretos, NO en git.

## 2. Activación por conector (UI · botones · por cliente)

En `/admin/projects/{id}/remediation` → sección **Conectores cloud**:
- **Activar / Desactivar** la remediación del conector (capa 2 del kill-switch).
- **Política**: `Sin auto` · `Solo seguro automático` (SAFE_AUTO se aplica solo) ·
  `Seguro auto + riesgo autorizado` (FULL · GUARDED pide autorización previa).
- **Activar escritura**: registra el consentimiento + muestra los permisos que el
  cliente debe conceder en su plataforma.

## 3. Conceder escritura en la plataforma del cliente (una vez · lo hace el cliente)

OAuth/IAM obliga a que el admin del cliente apruebe; FULKRO no puede auto-aprobarlo.

| Proveedor | Qué concede el cliente |
|-----------|------------------------|
| **AWS** | Adjuntar al rol que asume FULKRO una IAM policy con los permisos de escritura (S3/IAM/CloudTrail) listados en el grant-write. |
| **Microsoft 365** | El Global Admin concede *admin consent* a la app de FULKRO para los permisos Graph (Policy.ReadWrite.ConditionalAccess) en la pantalla oficial de Microsoft. |
| **Azure** | Asignar al Service Principal de FULKRO el rol RBAC con escritura sobre los recursos (p.ej. Storage Account Contributor). |
| **Google Workspace** | Añadir a la cuenta de servicio de FULKRO la delegación de dominio para el scope de Drive. |

## Verificación

- AWS está probado de verdad (moto · `test_cloud_writers_aws.py`): el motor aplica
  cifrado/bloqueo-público/versionado/política-contraseñas y verifica el estado real.
- M365/Azure/Google: lógica verificada por mock de alta fidelidad; la **primera
  aplicación contra el tenant vivo** se valida en el alta del primer cliente (con un
  `dry_run` primero desde la UI).

## Seguridad permanente

Cada acción es reversible (snapshot + auto-rollback si la verificación falla) y queda
en `audit_log` (cadena hash R6). El agente on-prem solo ejecuta playbooks de su
allowlist firmada (ver `REMEDIATION_AGENT_DEPLOYMENT.md`). Los destructivos están
BLOCKED (nunca automáticos).
