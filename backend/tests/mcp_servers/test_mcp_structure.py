"""Structure and logic tests for the FULKRO MCP servers (no Docker required)."""
import json
import sys
from pathlib import Path

import pytest
import yaml


MCP_BASE = Path("backend/mcp_servers")

SERVERS = [
    "recon", "vulnscan", "webpentest", "infra", "redteam",
    "cloud", "config", "phishing", "sast", "cracking",
    "apisec", "mobile", "wireless", "scope_enforcer",
]

TOOL_SERVERS = [s for s in SERVERS if s != "scope_enforcer"]

EXPECTED_TOOL_COUNTS = {
    "recon": 10, "vulnscan": 4, "webpentest": 6, "infra": 13,
    "redteam": 6, "cloud": 4, "config": 4, "phishing": 1,
    "sast": 5, "cracking": 3, "apisec": 4, "mobile": 2, "wireless": 3,
}


def _ensure_sys_path():
    path = str(MCP_BASE)
    if path not in sys.path:
        sys.path.insert(0, path)


class TestFileStructure:
    def test_compose_exists(self):
        """Post SAN-B.MB-7.2: docker-compose.pentest.yml mergeado en root
        docker-compose.yml con profiles:[pentest]. Verifica root file existe."""
        repo_root = MCP_BASE.parent.parent  # backend/mcp_servers/.. = repo root
        assert (repo_root / "docker-compose.yml").exists()

    def test_compose_is_valid_yaml(self):
        """Verifica root docker-compose.yml tiene los servicios pentest
        post-merge (SAN-B.MB-7.2). 14 pentest services + core services."""
        repo_root = MCP_BASE.parent.parent
        with open(repo_root / "docker-compose.yml") as fh:
            data = yaml.safe_load(fh)
        assert "services" in data
        # Pentest services merged (todos con profiles: [pentest]):
        pentest_services = {
            "scope-enforcer", "recon", "vulnscan", "webpentest", "infra-mcp",
            "redteam", "cloud-mcp", "config-mcp", "phishing", "sast",
            "cracking", "apisec", "mobile", "wireless", "openvas",
        }
        assert pentest_services.issubset(set(data["services"].keys())), (
            f"Servicios pentest faltantes: {pentest_services - set(data['services'].keys())}"
        )
        # Networks pentest-net + pentest-external presentes:
        assert "pentest-net" in data.get("networks", {})
        assert "pentest-external" in data.get("networks", {})

    def test_shared_files_exist(self):
        for fname in ("mcp_protocol.py", "scope_check.py", "output_normalizer.py", "utils.py"):
            assert (MCP_BASE / "shared" / fname).exists(), f"shared/{fname} missing"

    @pytest.mark.parametrize("server", SERVERS)
    def test_server_dir_exists(self, server):
        assert (MCP_BASE / server).is_dir()

    @pytest.mark.parametrize("server", SERVERS)
    def test_dockerfile_exists(self, server):
        assert (MCP_BASE / server / "Dockerfile").exists()

    @pytest.mark.parametrize("server", TOOL_SERVERS)
    def test_server_py_exists(self, server):
        assert (MCP_BASE / server / "server.py").exists()

    @pytest.mark.parametrize("server", TOOL_SERVERS)
    def test_tools_dir_exists(self, server):
        tools = MCP_BASE / server / "tools"
        assert tools.is_dir()
        py_files = [f for f in tools.glob("*.py") if f.name != "__init__.py"]
        expected = EXPECTED_TOOL_COUNTS.get(server, 1)
        assert len(py_files) >= expected, (
            f"{server}: expected {expected} tools, "
            f"found {len(py_files)}: {[f.name for f in py_files]}"
        )


class TestMCPProtocol:
    def test_mcp_server_base_importable(self):
        _ensure_sys_path()
        from shared.mcp_protocol import MCPServer, MCPTool  # noqa: F401
        assert hasattr(MCPServer, "run")
        assert hasattr(MCPServer, "register_tool")

    def test_tool_creation(self):
        _ensure_sys_path()
        from shared.mcp_protocol import MCPTool

        tool = MCPTool(
            name="test",
            description="test tool",
            input_schema={"properties": {"target": {"type": "string"}}},
            risk_level="low",
            timeout_seconds=60,
        )
        assert tool.name == "test"
        assert tool.risk_level == "low"
        assert tool.input_schema["type"] == "object"

    def test_server_registration(self):
        _ensure_sys_path()
        from shared.mcp_protocol import MCPServer, MCPTool

        class TestServer(MCPServer):
            SERVER_NAME = "test"

            def _register_tools(self):
                self.register_tool(
                    MCPTool("t1", "desc", {"properties": {}}),
                    lambda: {"ok": True},
                )

        s = TestServer()
        assert "t1" in s.tools
        assert len(s.tools) == 1


class TestScopeCheck:
    def setup_method(self):
        _ensure_sys_path()
        import os

        os.environ["PENTEST_AUTHORIZATION"] = json.dumps({
            "targets": ["10.0.0.0/24", "192.168.1.0/24", "ejemplo.com", "*.ejemplo.com"],
            "excluded_targets": ["10.0.0.1"],
            "allowed_test_types": ["scan", "enumerate", "config_audit"],
            "window_start": "2020-01-01T00:00:00+00:00",
            "window_end": "2030-12-31T23:59:59+00:00",
        })
        import shared.scope_check as sc
        sc._AUTHORIZATION = None

    def test_allow_ip_in_range(self):
        from shared.scope_check import check_scope
        assert check_scope("10.0.0.50", "scan")["allowed"] is True

    def test_deny_ip_out_of_range(self):
        from shared.scope_check import check_scope
        assert check_scope("172.16.0.1", "scan")["allowed"] is False

    def test_deny_excluded_ip(self):
        from shared.scope_check import check_scope
        assert check_scope("10.0.0.1", "scan")["allowed"] is False

    def test_deny_forbidden_test_type(self):
        from shared.scope_check import check_scope
        assert check_scope("10.0.0.50", "exploit")["allowed"] is False

    def test_allow_exact_domain(self):
        from shared.scope_check import check_scope
        assert check_scope("ejemplo.com", "scan")["allowed"] is True

    def test_allow_wildcard_subdomain(self):
        from shared.scope_check import check_scope
        assert check_scope("sub.ejemplo.com", "scan")["allowed"] is True

    def test_deny_unrelated_domain(self):
        from shared.scope_check import check_scope
        assert check_scope("evil.com", "scan")["allowed"] is False

    def test_fail_closed(self):
        import os
        os.environ["PENTEST_AUTHORIZATION"] = "INVALID JSON"
        import shared.scope_check as sc
        sc._AUTHORIZATION = None
        from shared.scope_check import check_scope
        assert check_scope("10.0.0.50", "scan")["allowed"] is False


class TestOutputNormalizer:
    def setup_method(self):
        _ensure_sys_path()

    def test_normalize_nuclei_finding(self):
        from shared.output_normalizer import normalize_finding

        raw = {
            "info": {
                "name": "TLS 1.0 Detected",
                "severity": "medium",
                "description": "TLS 1.0 is deprecated and insecure",
            },
            "host": "10.0.0.5",
            "port": "443",
            "matched-at": "https://10.0.0.5:443",
        }
        f = normalize_finding(raw, "nuclei", "10.0.0.5")
        assert f["severity"] == "medium"
        assert f["tool"] == "nuclei"
        assert f["host"] == "10.0.0.5"
        assert len(f["raw_output_hash"]) == 64

    def test_normalize_nmap_finding(self):
        from shared.output_normalizer import normalize_finding
        raw = {"title": "Open SSH", "severity": "info", "host": "10.0.0.5", "port": 22}
        f = normalize_finding(raw, "nmap", "10.0.0.5")
        assert f["title"] == "Open SSH"
        assert f["port"] == 22

    def test_extract_cves(self):
        _ensure_sys_path()
        from shared.utils import extract_cves

        cves = extract_cves("Found CVE-2021-44228 (Log4Shell) and CVE-2020-1472 (ZeroLogon)")
        assert "CVE-2021-44228" in cves
        assert "CVE-2020-1472" in cves

    def test_normalize_severity_variants(self):
        _ensure_sys_path()
        from shared.utils import normalize_severity

        assert normalize_severity("CRITICAL") == "critical"
        assert normalize_severity("high") == "high"
        assert normalize_severity("Medium") == "medium"
        assert normalize_severity("bajo") == "low"
        assert normalize_severity("informational") == "info"
        assert normalize_severity("unknown") == "info"


class TestUtils:
    def setup_method(self):
        _ensure_sys_path()

    def test_parse_jsonl(self):
        from shared.utils import parse_jsonl

        raw = '{"a":1}\n{"b":2}\nsome warning\n{"c":3}'
        result = parse_jsonl(raw)
        assert len(result) == 3
        assert result[0]["a"] == 1

    def test_parse_nmap_xml_basic(self):
        from shared.utils import parse_nmap_xml

        xml = """<?xml version="1.0"?>
        <nmaprun>
          <host>
            <status state="up"/>
            <address addr="10.0.0.5" addrtype="ipv4"/>
            <ports>
              <port protocol="tcp" portid="22">
                <state state="open"/>
                <service name="ssh" product="OpenSSH" version="8.9"/>
              </port>
            </ports>
          </host>
        </nmaprun>"""
        result = parse_nmap_xml(xml)
        assert len(result["hosts"]) == 1
        assert result["hosts"][0]["ip"] == "10.0.0.5"
        assert result["hosts"][0]["ports"][0]["port"] == 22
        assert result["hosts"][0]["ports"][0]["service"] == "ssh"

    def test_hash_output(self):
        from shared.utils import hash_output

        h = hash_output("test data")
        assert len(h) == 64
