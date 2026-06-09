# Shared MCP infrastructure - MCP infrastructure (NOT a server)

**Tipo:** infraestructura compartida (sin tools ofensivos propios)

## Descripcion

Libreria comun a todos los MCPs: MCPProtocol class, MCPTool base, scope_check, output_normalizer, utils. NO tiene tools propios - NO containerizable independientemente.

## Estado

Componente fundacional - NO se containeriza independientemente. Importado por
todos los servidores MCP ofensivos en `backend/mcp_servers/*/server.py`.
