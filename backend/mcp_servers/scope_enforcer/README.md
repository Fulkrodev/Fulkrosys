# Scope Enforcer (fail-closed) - MCP infrastructure (NOT a server)

**Tipo:** infraestructura compartida (sin tools ofensivos propios)

## Descripcion

Gateway fail-closed que valida cada invocacion contra authorization.json del MCP destino (IPs CIDR, dominios FQDN, ventanas tiempo, tools whitelist). Bloquea por defecto si no hay match explicito. CRITICO para compliance ENS.

## Estado

Componente fundacional - NO se containeriza independientemente. Importado por
todos los servidores MCP ofensivos en `backend/mcp_servers/*/server.py`.
