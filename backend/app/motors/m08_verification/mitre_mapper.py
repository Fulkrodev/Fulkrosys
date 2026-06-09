"""M8 v5.1 — MITRE ATT&CK mapper.

Capa 1 (rule): CVE → tecnicas ATT&CK (catalogo curado, ~50 mapeos)
Capa 2 (pattern): keywords del titulo/desc → tecnicas
Capa 3 (LLM Haiku 4.5): fallback structured output · confidence >= 0.5

Output:
    [{"technique_id": "T1190", "tactic": "Initial Access",
      "technique_name": "Exploit Public-Facing Application",
      "source": "rule" | "pattern" | "llm_capa3"}]

SAN-B.MB-3.ter.3 cierra Capa 3 LLM stub (`enable_llm=True` default).
"""
from __future__ import annotations

from typing import Any

from backend.app.motors.m08_verification.zfp_engine import ZfpFinding


# ════════════════════════════════════════════════════════════════════
# CAPA 1 — CVE → MITRE ATT&CK
# ════════════════════════════════════════════════════════════════════

CVE_TO_MITRE: dict[str, list[dict[str, str]]] = {
    # OpenSSH regreSSHion
    "CVE-2024-6387": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1059", "tactic": "Execution",
         "technique_name": "Command and Scripting Interpreter"},
    ],
    # Log4Shell + variants
    "CVE-2021-44228": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1059.007", "tactic": "Execution",
         "technique_name": "Command and Scripting Interpreter: JavaScript"},
    ],
    "CVE-2021-45046": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # Spring4Shell
    "CVE-2022-22965": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # ProxyShell Exchange
    "CVE-2021-34473": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1505.003", "tactic": "Persistence",
         "technique_name": "Web Shell"},
    ],
    # EternalBlue
    "CVE-2017-0144": [
        {"technique_id": "T1210", "tactic": "Lateral Movement",
         "technique_name": "Exploitation of Remote Services"},
    ],
    # BlueKeep
    "CVE-2019-0708": [
        {"technique_id": "T1210", "tactic": "Lateral Movement",
         "technique_name": "Exploitation of Remote Services"},
    ],
    # Heartbleed
    "CVE-2014-0160": [
        {"technique_id": "T1040", "tactic": "Credential Access",
         "technique_name": "Network Sniffing"},
    ],
    # ShellShock
    "CVE-2014-6271": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1059.004", "tactic": "Execution",
         "technique_name": "Unix Shell"},
    ],
    # Apache Struts
    "CVE-2017-5638": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    "CVE-2018-11776": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # Drupalgeddon
    "CVE-2018-7600": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # PrintNightmare
    "CVE-2021-1675": [
        {"technique_id": "T1068", "tactic": "Privilege Escalation",
         "technique_name": "Exploitation for Privilege Escalation"},
    ],
    "CVE-2021-34527": [
        {"technique_id": "T1068", "tactic": "Privilege Escalation",
         "technique_name": "Exploitation for Privilege Escalation"},
    ],
    # Citrix ADC
    "CVE-2019-19781": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1133", "tactic": "Initial Access",
         "technique_name": "External Remote Services"},
    ],
    # F5 BIG-IP
    "CVE-2020-5902": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # PHP CGI
    "CVE-2024-4577": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # Atlassian
    "CVE-2022-26134": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    "CVE-2023-22515": [
        {"technique_id": "T1078.004", "tactic": "Initial Access",
         "technique_name": "Valid Accounts: Cloud Accounts"},
    ],
    # MOVEit
    "CVE-2023-34362": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
        {"technique_id": "T1505.003", "tactic": "Persistence",
         "technique_name": "Web Shell"},
    ],
    # VMware ESXi
    "CVE-2021-21974": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # pwnkit
    "CVE-2021-4034": [
        {"technique_id": "T1068", "tactic": "Privilege Escalation",
         "technique_name": "Exploitation for Privilege Escalation"},
    ],
    # Fortinet
    "CVE-2022-40684": [
        {"technique_id": "T1078", "tactic": "Initial Access",
         "technique_name": "Valid Accounts"},
    ],
    "CVE-2024-21762": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    # ConnectWise ScreenConnect
    "CVE-2024-1709": [
        {"technique_id": "T1078", "tactic": "Initial Access",
         "technique_name": "Valid Accounts"},
        {"technique_id": "T1219", "tactic": "Command and Control",
         "technique_name": "Remote Access Software"},
    ],
    # XZ Utils backdoor
    "CVE-2024-3094": [
        {"technique_id": "T1195.001", "tactic": "Initial Access",
         "technique_name": "Supply Chain Compromise: Compromise Software Dependencies"},
        {"technique_id": "T1554", "tactic": "Persistence",
         "technique_name": "Compromise Client Software Binary"},
    ],

    # ── Categorias generales sin CVE: pueden compartir tecnica ──
    # Web app exploits comunes
    "CVE-2023-46604": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
    "CVE-2023-3519": [
        {"technique_id": "T1190", "tactic": "Initial Access",
         "technique_name": "Exploit Public-Facing Application"},
    ],
}


# ════════════════════════════════════════════════════════════════════
# CAPA 2 — Pattern → MITRE
# ════════════════════════════════════════════════════════════════════

PATTERN_TO_MITRE: list[dict[str, Any]] = [
    {
        "patterns": ["SQL Injection", "SQLi", "blind sql"],
        "techniques": [
            {"technique_id": "T1190", "tactic": "Initial Access",
             "technique_name": "Exploit Public-Facing Application"},
        ],
    },
    {
        "patterns": ["XSS", "Cross-Site Scripting"],
        "techniques": [
            {"technique_id": "T1059.007", "tactic": "Execution",
             "technique_name": "Command and Scripting Interpreter: JavaScript"},
        ],
    },
    {
        "patterns": ["default credentials", "default password", "admin/admin"],
        "techniques": [
            {"technique_id": "T1078", "tactic": "Initial Access",
             "technique_name": "Valid Accounts"},
        ],
    },
    {
        "patterns": ["FTP anonymous", "anonymous login"],
        "techniques": [
            {"technique_id": "T1078.003", "tactic": "Initial Access",
             "technique_name": "Valid Accounts: Local Accounts"},
        ],
    },
    {
        "patterns": ["Telnet", "rsh", "rlogin"],
        "techniques": [
            {"technique_id": "T1040", "tactic": "Credential Access",
             "technique_name": "Network Sniffing"},
        ],
    },
    {
        "patterns": ["TLS 1.0", "SSLv2", "SSLv3", "weak cipher", "RC4"],
        "techniques": [
            {"technique_id": "T1040", "tactic": "Credential Access",
             "technique_name": "Network Sniffing"},
        ],
    },
    {
        "patterns": ["X-Frame-Options", "Clickjacking"],
        "techniques": [
            {"technique_id": "T1185", "tactic": "Collection",
             "technique_name": "Browser Session Hijacking"},
        ],
    },
    {
        "patterns": ["world-writable"],
        "techniques": [
            {"technique_id": "T1222", "tactic": "Defense Evasion",
             "technique_name": "File and Directory Permissions Modification"},
        ],
    },
    {
        "patterns": ["minPwdLength", "weak password policy", "lockoutThreshold"],
        "techniques": [
            {"technique_id": "T1110", "tactic": "Credential Access",
             "technique_name": "Brute Force"},
        ],
    },
    {
        "patterns": ["SPF", "DKIM", "DMARC", "spoofing"],
        "techniques": [
            {"technique_id": "T1566", "tactic": "Initial Access",
             "technique_name": "Phishing"},
        ],
    },
]


# ════════════════════════════════════════════════════════════════════
# Mapper service
# ════════════════════════════════════════════════════════════════════

class MitreMapper:
    """Mapeo de findings a tecnicas MITRE ATT&CK."""

    def __init__(self, *, enable_llm: bool = True) -> None:
        self.enable_llm = enable_llm

    def map(self, finding: ZfpFinding) -> list[dict[str, str]]:
        """Devuelve lista de tecnicas (max 3 unicas) anotadas con `source`."""
        results: list[dict[str, str]] = []

        # Capa 1: CVE
        if finding.cve_id:
            techs = CVE_TO_MITRE.get(finding.cve_id.upper())
            if techs:
                for t in techs:
                    results.append({**t, "source": "rule"})
                return self._dedupe(results)

        # Capa 2: pattern
        haystack = f"{finding.title} {finding.description}".lower()
        for entry in PATTERN_TO_MITRE:
            if any(p.lower() in haystack for p in entry["patterns"]):
                for t in entry["techniques"]:
                    results.append({**t, "source": "pattern"})
        if results:
            return self._dedupe(results)

        # Capa 3: LLM Haiku 4.5 fallback (SAN-B.MB-3.ter.3)
        if self.enable_llm:
            from backend.app.motors.m08_verification.llm_classifier import (
                classify_mitre_technique_via_llm,
            )
            llm_results = classify_mitre_technique_via_llm(finding)
            if llm_results:
                return self._dedupe(llm_results)
        return []

    @staticmethod
    def _dedupe(items: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: set[str] = set()
        out: list[dict[str, str]] = []
        for it in items:
            tid = it.get("technique_id")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            out.append(it)
        return out[:3]
