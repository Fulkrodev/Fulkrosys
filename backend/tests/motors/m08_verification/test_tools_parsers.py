"""M8 v5.1 — Tests unit de parsers de tools (sin binarios).

Cada test usa fixture con output real (XML/JSON/text) capturado
de una ejecucion previa de la tool y verifica que parse_output()
extrae los FindingCandidate correctamente.
"""
from __future__ import annotations

import json

import pytest

from backend.app.motors.m08_verification.tools.lynis_runner import LynisRunner
from backend.app.motors.m08_verification.tools.nmap_runner import NmapRunner
from backend.app.motors.m08_verification.tools.nuclei_runner import NucleiRunner
from backend.app.motors.m08_verification.tools.testssl_runner import TestsslRunner
from backend.app.motors.m08_verification.tools.zap_runner import ZapRunner


# ════════════════════════════════════════════════════════════════════
# Nmap parser
# ════════════════════════════════════════════════════════════════════

NMAP_XML_SAMPLE = b"""<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="10.0.1.15" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="6.6.1"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="nginx" version="1.18.0"/>
        <script id="ssl-heartbleed" output="VULNERABLE"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed"/>
        <service name="http"/>
      </port>
    </ports>
  </host>
</nmaprun>"""


def test_nmap_parser_extracts_open_ports():
    findings = NmapRunner.parse_output(NMAP_XML_SAMPLE)
    titles = [f["title"] for f in findings]
    # Solo abiertos: 22 + 443 + script ssl-heartbleed
    assert any("22" in t for t in titles)
    assert any("443" in t for t in titles)
    assert not any("80" in t and "Puerto abierto" in t for t in titles)


def test_nmap_parser_obsolete_ssh_severity_medium():
    findings = NmapRunner.parse_output(NMAP_XML_SAMPLE)
    ssh_findings = [f for f in findings if f.get("affected_port") == 22]
    assert ssh_findings
    # OpenSSH 6.6.1 esta en OBSOLETE_SERVICE_KEYWORDS
    assert ssh_findings[0]["severity"] == "medium"


def test_nmap_parser_nse_heartbleed_critical():
    findings = NmapRunner.parse_output(NMAP_XML_SAMPLE)
    heartbleed = [
        f for f in findings if "ssl-heartbleed" in f.get("title", "")
    ]
    assert heartbleed
    assert heartbleed[0]["severity"] == "critical"
    assert heartbleed[0]["affected_port"] == 443


def test_nmap_parser_empty_input():
    assert NmapRunner.parse_output(b"") == []
    assert NmapRunner.parse_output(b"<?xml?>not valid xml") == []


# ════════════════════════════════════════════════════════════════════
# Nuclei parser
# ════════════════════════════════════════════════════════════════════

NUCLEI_NDJSON_SAMPLE = b"""{"template-id":"CVE-2021-44228","host":"https://web.dataforma.es","matched-at":"https://web.dataforma.es/api/login","info":{"name":"Apache Log4j RCE","severity":"critical","tags":["cve","rce","log4j"],"classification":{"cve-id":["CVE-2021-44228"],"cwe-id":["CWE-502"],"cvss-score":10.0,"cvss-metrics":"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"}}}
{"template-id":"http-missing-security-headers","host":"https://web.dataforma.es","matched-at":"https://web.dataforma.es/","info":{"name":"X-Frame-Options Header Missing","severity":"info","tags":["headers"]}}
not-json-line
{"template-id":"tech-detect","host":"https://web.dataforma.es","info":{"name":"WordPress detected","severity":"info"}}
"""


def test_nuclei_parser_extracts_critical_log4shell():
    findings = NucleiRunner.parse_output(NUCLEI_NDJSON_SAMPLE)
    log4 = [f for f in findings if f.get("cve_id") == "CVE-2021-44228"]
    assert log4
    f = log4[0]
    assert f["severity"] == "critical"
    assert f["cvss_score"] == 10.0
    assert f["cwe_id"] == "CWE-502"
    assert f["affected_url"] == "https://web.dataforma.es/api/login"
    assert f["affected_port"] == 443
    assert f["tool_metadata"]["template_id"] == "CVE-2021-44228"


def test_nuclei_parser_skips_invalid_json_lines():
    findings = NucleiRunner.parse_output(NUCLEI_NDJSON_SAMPLE)
    # Esperado: 3 findings (log4 + headers + tech), no 4
    assert len(findings) == 3


def test_nuclei_parser_handles_missing_classification():
    sample = b'{"template-id":"x","host":"h","info":{"name":"X","severity":"info"}}'
    findings = NucleiRunner.parse_output(sample)
    assert len(findings) == 1
    assert findings[0]["cve_id"] is None
    assert findings[0]["cvss_score"] is None


# ════════════════════════════════════════════════════════════════════
# testssl parser
# ════════════════════════════════════════════════════════════════════

TESTSSL_JSON_SAMPLE = b"""[
  {"id": "TLS1", "severity": "MEDIUM", "finding": "TLS 1.0 offered (deprecated)", "host": "web.example.es", "port": "443"},
  {"id": "TLS1_3", "severity": "OK", "finding": "TLS 1.3 offered (OK)", "host": "web.example.es", "port": "443"},
  {"id": "RC4", "severity": "HIGH", "finding": "RC4 ciphers offered", "host": "web.example.es", "port": "443"},
  {"id": "cert_expiration", "severity": "INFO", "finding": "Certificate expires in 45 days", "host": "web.example.es", "port": "443"}
]
"""


def test_testssl_parser_excludes_ok_findings():
    findings = TestsslRunner.parse_output(TESTSSL_JSON_SAMPLE, default_host="web.example.es")
    titles = [f["title"] for f in findings]
    assert any("TLS1" in t for t in titles)
    assert any("RC4" in t for t in titles)
    # OK no debe aparecer
    assert not any("TLS 1.3" in (f.get("description") or "") for f in findings)


def test_testssl_parser_severity_normalized():
    findings = TestsslRunner.parse_output(TESTSSL_JSON_SAMPLE, default_host="web.example.es")
    rc4 = [f for f in findings if "RC4" in f["title"]]
    assert rc4 and rc4[0]["severity"] == "high"
    tls1 = [f for f in findings if "TLS1" in f["title"]]
    assert tls1 and tls1[0]["severity"] == "medium"


def test_testssl_parser_empty():
    assert TestsslRunner.parse_output(b"") == []
    assert TestsslRunner.parse_output(b"   ") == []


# ════════════════════════════════════════════════════════════════════
# Lynis parser
# ════════════════════════════════════════════════════════════════════

LYNIS_REPORT_SAMPLE = b"""# Lynis report
warning[]=AUTH-9286|No password complexity requirements set|/etc/login.defs|enable PAM_PASSWDQC
warning[]=FILE-7524|Found one or more world writable files|/var/log/test.log|chmod 644
suggestion[]=AUTH-9282|PASS_MIN_LEN<14|/etc/login.defs|set to 14
suggestion[]=NETW-3032|Determine if protocol DCCP is used|sysctl|disable
report_version_major=3
"""


def test_lynis_parser_separates_warnings_suggestions():
    findings = LynisRunner.parse_output(LYNIS_REPORT_SAMPLE, host="srv01")
    warnings = [f for f in findings if f["tool_metadata"]["kind"] == "warning"]
    suggestions = [f for f in findings if f["tool_metadata"]["kind"] == "suggestion"]
    assert len(warnings) == 2
    assert len(suggestions) == 2
    assert all(f["severity"] == "high" for f in warnings)
    assert all(f["severity"] == "medium" for f in suggestions)


def test_lynis_parser_extracts_test_id():
    findings = LynisRunner.parse_output(LYNIS_REPORT_SAMPLE, host="srv01")
    ids = {f["tool_metadata"]["lynis_test_id"] for f in findings}
    assert ids == {"AUTH-9286", "FILE-7524", "AUTH-9282", "NETW-3032"}


# ════════════════════════════════════════════════════════════════════
# ZAP parser
# ════════════════════════════════════════════════════════════════════

ZAP_RAW_SAMPLE = json.dumps({
    "alerts": [
        {
            "id": "1", "name": "SQL Injection",
            "risk": "High", "confidence": "Medium",
            "url": "https://web.dataforma.es/api/users?id=1",
            "param": "id", "evidence": "syntax error",
            "description": "SQL injection vulnerability in id param.",
            "solution": "Use parameterized queries.",
            "cweid": "89", "pluginId": "40018",
        },
        {
            "id": "2", "name": "X-Frame-Options Header Missing",
            "risk": "Medium", "url": "https://web.dataforma.es/",
            "evidence": "", "description": "Missing header",
            "cweid": "1021", "pluginId": "10020",
        },
    ],
}).encode("utf-8")


def test_zap_parser_extracts_severity_and_cwe():
    findings = ZapRunner.parse_output(ZAP_RAW_SAMPLE)
    assert len(findings) == 2
    sqli = [f for f in findings if "SQL" in f["title"]][0]
    assert sqli["severity"] == "high"
    assert sqli["cwe_id"] == "89"
    assert sqli["affected_url"] == "https://web.dataforma.es/api/users?id=1"
    assert sqli["affected_port"] == 443


def test_zap_parser_empty():
    assert ZapRunner.parse_output(b"") == []
    assert ZapRunner.parse_output(b'{"alerts":[]}') == []
