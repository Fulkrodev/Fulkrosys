# MCP Infrastructure (AD + Network) - FULKRO

**Status:** estructural (containerizable - tools registered)
**Categoria aplicabilidad ENS:** A
**Tools count:** 14

## Descripcion

Active Directory + lateral movement + post-exploitation. Apoya M8 ALTA (Red Team formal con BloodHound + Metasploit + Impacket suite).

## Tools expuestos

| Tool | Funcion (breve) |
|---|---|
| `bloodhound_analyze` | (ver `tools/bloodhound_analyze_tool.py::TOOL` - descripcion en docstring) |
| `bloodhound_collect` | (ver `tools/bloodhound_collect_tool.py::TOOL` - descripcion en docstring) |
| `certipy` | (ver `tools/certipy_tool.py::TOOL` - descripcion en docstring) |
| `coercer` | (ver `tools/coercer_tool.py::TOOL` - descripcion en docstring) |
| `impacket` | (ver `tools/impacket_tool.py::TOOL` - descripcion en docstring) |
| `kerbrute` | (ver `tools/kerbrute_tool.py::TOOL` - descripcion en docstring) |
| `lynis` | (ver `tools/lynis_tool.py::TOOL` - descripcion en docstring) |
| `metasploit_check` | (ver `tools/metasploit_check_tool.py::TOOL` - descripcion en docstring) |
| `metasploit_exploit` | (ver `tools/metasploit_exploit_tool.py::TOOL` - descripcion en docstring) |
| `metasploit_info` | (ver `tools/metasploit_info_tool.py::TOOL` - descripcion en docstring) |
| `metasploit_post` | (ver `tools/metasploit_post_tool.py::TOOL` - descripcion en docstring) |
| `metasploit_search` | (ver `tools/metasploit_search_tool.py::TOOL` - descripcion en docstring) |
| `netexec` | (ver `tools/netexec_tool.py::TOOL` - descripcion en docstring) |
| `responder` | (ver `tools/responder_tool.py::TOOL` - descripcion en docstring) |

## Authorization

Ver `authorization.json` en este mismo directorio. Scope estandar fail-closed:

- `allowed_ips_cidr`: lista CIDR - vacia = ninguna IP permitida por defecto
- `allowed_domains`: lista FQDN - vacia = ningun dominio permitido por defecto
- `time_windows_cron`: ventanas cron - controlado por cliente al autorizar alcance
- `tools_whitelisted`: subset de los tools listados arriba (cliente elige)

Validacion en `scope_enforcer` antes de cada invocacion.

## Containerizacion

`Dockerfile` presente - imagen base con runtime + requirements.txt. Construir con:

    docker build -t fulkro-mcp-infra backend/mcp_servers/infra/

Servidor inicia en stdin/stdout MCP protocol via `server.py`.

## Spec FULKRO

- **Input contract**: definido por cada `*_tool.py::TOOL` (Pydantic schema)
- **Output contract**: normalizado via `shared.output_normalizer`
- **Idempotency**: depende de la herramienta subyacente (la mayoria SI - scans son query)
- **LLM usage**: ninguno (los MCPs ejecutan binarios - LLM enrichment en M8 Agente 8)

## Uso en pipeline ENS

Categoria aplicabilidad: **A**.

Invocado desde:
- Motor M8 Verificacion (orquestador)
- Agente 8 ReAct loop (MEDIA+)
- Cliente autoriza alcance mediante `/api/v1/projects/<id>/verification/scope`

## Estado

✓ Containerizable - Dockerfile + requirements presentes - tools/*_tool.py registered en server.py

## TODO future

- Anadir tests de integracion contra targets de laboratorio
- Validar tool count contra spec FULKRO (plan v2 sec D.3 dice 14 MCPs - 70 tools)
- Anadir ejemplos `authorization.json` per categoria B/M/A
