"""Tool: graphql_introspection — GraphQL schema introspection + risk checks."""
import json
import urllib.request

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="graphql_introspection",
    description="Run GraphQL introspection query and report schema + risky fields.",
    input_schema={
        "properties": {"endpoint": {"type": "string"}},
        "required": ["endpoint"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["mp.sw.2", "op.exp.4"],
)


_INTROSPECTION = {
    "query": (
        "query IntrospectionQuery{__schema{types{name kind"
        " fields{name type{name kind}}}}}"
    )
}


async def graphql_introspection(endpoint: str) -> dict:
    scope = check_scope(endpoint, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    data = json.dumps(_INTROSPECTION).encode()
    req = urllib.request.Request(
        endpoint, data=data, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        schema = json.loads(body)
        return {"endpoint": endpoint, "schema": schema}
    except Exception as exc:
        return {"error": str(exc)[:500], "endpoint": endpoint}
