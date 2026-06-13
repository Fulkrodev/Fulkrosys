# Despliegue del Agente de Remediación on-prem (ADR-055 Fase 3)

Guía de despliegue **seguro** del agente que aplica remediaciones en servidores
on-prem del cliente (CVEs, hardening, firewall) que FULKRO no puede tocar por API
cloud.

## Modelo de seguridad (por qué es blindado)

| Amenaza | Mitigación |
|---------|-----------|
| Que el agente abra superficie de ataque | **Sin puertos entrantes**: el agente hace *pull* (sale él hacia FULKRO). Nada escucha. |
| Que alguien le mande ejecutar código arbitrario | **Allowlist horneada** de playbooks (`playbooks.REGISTRY`). Un `playbook_id` fuera de la lista → rechazo. **Nunca** shell arbitrario ni `eval`. |
| Que se falsifique/manipule un comando | **Firma Ed25519 del servidor** sobre el payload canónico. El agente fija la clave pública del servidor en el *enrollment* y verifica cada comando. Manipulación → rechazo. |
| Que se falsifique un resultado | El agente **firma** cada report con su clave; el servidor lo verifica con la pública fijada en el *enrollment*. |
| Que un cambio rompa producción | Cada playbook es **idempotente**, hace **snapshot** previo y **revierte** solo si la verificación falla. **DRY-RUN por defecto** (no toca nada sin `--apply`). |
| Que un agente comprometido siga operando | **Kill-switch**: el admin revoca el agente (`/revoke`) → su token deja de autenticar al instante. |
| Tier de riesgo | SAFE_AUTO se aplica solo; **GUARDED requiere autorización previa** (cliente/admin) antes de que el servidor encole el comando. Destructivo = BLOCKED (nunca llega al agente). |

## Requisitos del servidor (FULKRO)

Define la clave de firma **estable** del servidor (si no, los agentes no podrán
verificar comandos tras un reinicio):

```bash
# 32 bytes hex · guárdala como secreto (.env.prod)
python3 -c "import secrets;print(secrets.token_hex(32))"
# → FULKRO_REMEDIATION_SIGNING_KEY=<hex>
```

Y el kill-switch global (default OFF · nada se ejecuta sin esto):

```bash
FULKRO_REMEDIATION_ENABLED=true
```

## Despliegue en el host del cliente

Requisitos: Python 3.10+ y `cryptography` (`pip install cryptography`). Copia
`agent/fulkro_remediation_agent.py` + `agent/playbooks.py` al host.

```bash
# 1. Marcos emite un token de enrollment desde el panel admin:
#    POST /api/v1/admin/projects/{pid}/remediation/agents  {hostname}
#    → devuelve enrollment_token (se muestra UNA vez)

# 2. Enrolar (canjea el token · genera el par de claves del agente):
sudo FULKRO_AGENT_STATE=/var/lib/fulkro-agent \
  python3 fulkro_remediation_agent.py enroll \
  --server https://fulkro.es --token <ENROLLMENT_TOKEN>

# 3. Probar en seco (NO aplica nada · recomendado primero):
python3 fulkro_remediation_agent.py run --server https://fulkro.es --once

# 4. Ejecutar de verdad (como servicio · requiere root para sshd/ufw/apt):
sudo python3 fulkro_remediation_agent.py run --server https://fulkro.es --apply
```

El estado (clave privada del agente + token) vive en
`/var/lib/fulkro-agent/agent_state.json` con permisos `0600`. Trátalo como secreto.

### Como servicio systemd (recomendado)

```ini
# /etc/systemd/system/fulkro-agent.service
[Unit]
Description=FULKRO Remediation Agent
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /opt/fulkro-agent/fulkro_remediation_agent.py run \
  --server https://fulkro.es --apply --interval 60
Environment=FULKRO_AGENT_STATE=/var/lib/fulkro-agent
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
```

## Playbooks incluidos (reference)

| playbook_id | Tier | Qué hace | Reversible |
|-------------|------|----------|-----------|
| `harden_sshd_root_login` | SAFE_AUTO | `PermitRootLogin no` + valida (`sshd -t`) + recarga | sí (restaura config) |
| `enable_host_firewall_rule` | SAFE_AUTO | `ufw deny <port>` | sí (`ufw delete`) |
| `apply_package_security_update` | GUARDED | `apt-get install --only-upgrade <pkg>` | best-effort (reinstala versión previa) |

Añadir un playbook nuevo = implementarlo en `playbooks.REGISTRY` (host) **y**
catalogarlo en `backend/app/motors/m_remediation/catalog.py` con `provider="host"`.
La allowlist del agente y el catálogo del servidor deben coincidir (lo verifica el
test `test_allowlist_matches_host_catalog`).

## Auditoría (ENAC)

Cada enrollment, comando emitido y report queda en `audit_log` (cadena hash R6 ·
`remediation.agent.*`). El report firmado por el agente prueba la integridad del
resultado de cada acción aplicada en el sistema del cliente.
