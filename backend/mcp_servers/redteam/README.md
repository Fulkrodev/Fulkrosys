# MCP Red Team Operations - FULKRO

**Status:** estructural (containerizable - tools registered)
**Categoria aplicabilidad ENS:** A
**Tools count:** 6

## Descripcion

Caldera + Sliver + simulacion ATT&CK - obligatorio ALTA cada 2 anos. Output E-704 Red Team formal.

## Tools expuestos

| Tool | Funcion (breve) |
|---|---|
| `atomic_red_team` | (ver `tools/atomic_red_team_tool.py::TOOL` - descripcion en docstring) |
| `caldera_create_operation` | (ver `tools/caldera_create_operation_tool.py::TOOL` - descripcion en docstring) |
| `caldera_get_results` | (ver `tools/caldera_get_results_tool.py::TOOL` - descripcion en docstring) |
| `infection_monkey` | (ver `tools/infection_monkey_tool.py::TOOL` - descripcion en docstring) |
| `purplesharp` | (ver `tools/purplesharp_tool.py::TOOL` - descripcion en docstring) |
| `sliver_implant` | (ver `tools/sliver_implant_tool.py::TOOL` - descripcion en docstring) |

## Authorization

Ver `authorization.json` en este mismo directorio. Scope estandar fail-closed:

- `allowed_ips_cidr`: lista CIDR - vacia = ninguna IP permitida por defecto
- `allowed_domains`: lista FQDN - vacia = ningun dominio permitido por defecto
- `time_windows_cron`: ventanas cron - controlado por cliente al autorizar alcance
- `tools_whitelisted`: subset de los tools listados arriba (cliente elige)

Validacion en `scope_enforcer` antes de cada invocacion.

## Containerizacion

`Dockerfile` presente - imagen base con runtime + requirements.txt. Construir con:

    docker build -t fulkro-mcp-redteam backend/mcp_servers/redteam/

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
