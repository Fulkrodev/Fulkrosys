# MCP Vulnerability Scanning - FULKRO

**Status:** real (containerizable - validado externo)
**Categoria aplicabilidad ENS:** B,M,A
**Tools count:** 4

## Descripcion

Deteccion de vulnerabilidades conocidas via scanners de la industria. Apoya M8 en BASICA (nuclei high/critical) y MEDIA+ (OpenVAS completo).

## Tools expuestos

| Tool | Funcion (breve) |
|---|---|
| `grype` | (ver `tools/grype_tool.py::TOOL` - descripcion en docstring) |
| `nuclei` | (ver `tools/nuclei_tool.py::TOOL` - descripcion en docstring) |
| `openvas` | (ver `tools/openvas_tool.py::TOOL` - descripcion en docstring) |
| `trivy` | (ver `tools/trivy_tool.py::TOOL` - descripcion en docstring) |

## Authorization

Ver `authorization.json` en este mismo directorio. Scope estandar fail-closed:

- `allowed_ips_cidr`: lista CIDR - vacia = ninguna IP permitida por defecto
- `allowed_domains`: lista FQDN - vacia = ningun dominio permitido por defecto
- `time_windows_cron`: ventanas cron - controlado por cliente al autorizar alcance
- `tools_whitelisted`: subset de los tools listados arriba (cliente elige)

Validacion en `scope_enforcer` antes de cada invocacion.

## Containerizacion

`Dockerfile` presente - imagen base con runtime + requirements.txt. Construir con:

    docker build -t fulkro-mcp-vulnscan backend/mcp_servers/vulnscan/

Servidor inicia en stdin/stdout MCP protocol via `server.py`.

## Spec FULKRO

- **Input contract**: definido por cada `*_tool.py::TOOL` (Pydantic schema)
- **Output contract**: normalizado via `shared.output_normalizer`
- **Idempotency**: depende de la herramienta subyacente (la mayoria SI - scans son query)
- **LLM usage**: ninguno (los MCPs ejecutan binarios - LLM enrichment en M8 Agente 8)

## Uso en pipeline ENS

Categoria aplicabilidad: **B,M,A**.

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
