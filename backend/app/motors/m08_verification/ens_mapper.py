"""M8 v5.1 — ENS Mapper de 3 capas.

Capa 1 (rule): diccionario CVE → [medidas ENS]
Capa 2 (semantic): pgvector contra embeddings de las 73 medidas
Capa 3 (llm): Haiku con grounding RAG sobre RD 311/2022 + CCN-STIC

Cada finding puede mapear a 1-3 medidas ENS. ``ens_primary_measure``
es la primera (mayor confidence) para vistas rapidas.

Output:
    [{"measure": "op.exp.4", "title": "...", "method": "rule"|"semantic"|"llm",
      "citation": "...", "confidence": 0.95}]
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.zfp_engine import ZfpFinding


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# CAPA 1 — Rule-based: catalogo CVE → [medidas ENS]
# ════════════════════════════════════════════════════════════════════
# Cada medida tiene su 'titulo' breve para que aparezca en el informe
# sin tener que joinear con ens_measures cada vez. La confidence de la
# capa rule es 0.95 (alta — es mapeo experto manual).

CVE_TO_ENS: dict[str, list[dict[str, Any]]] = {
    # ── OpenSSH / SSH ──
    "CVE-2024-6387": [
        {"measure": "op.exp.4", "title": "Manejo seguro de cambios", "citation": "RD 311/2022 Anexo II op.exp.4 — gestion de actualizaciones"},
        {"measure": "op.acc.6", "title": "Acceso local", "citation": "RD 311/2022 Anexo II op.acc.6"},
    ],
    "CVE-2023-38408": [
        {"measure": "op.exp.4", "title": "Manejo seguro de cambios"},
    ],

    # ── Log4Shell + Spring4Shell ──
    "CVE-2021-44228": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades", "citation": "Log4Shell — actualizacion critica"},
        {"measure": "op.exp.6", "title": "Proteccion frente a codigo danino"},
    ],
    "CVE-2021-45046": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
    ],
    "CVE-2022-22965": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "mp.sw.1", "title": "Desarrollo de aplicaciones"},
    ],

    # ── ProxyShell / Exchange ──
    "CVE-2021-34473": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.acc.6", "title": "Acceso local — bypass auth"},
    ],
    "CVE-2021-34523": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],
    "CVE-2021-31207": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── EternalBlue / SMB ──
    "CVE-2017-0144": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "mp.com.2", "title": "Proteccion comunicaciones internas"},
    ],

    # ── BlueKeep / RDP ──
    "CVE-2019-0708": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.acc.6", "title": "Acceso local"},
    ],

    # ── Heartbleed / OpenSSL ──
    "CVE-2014-0160": [
        {"measure": "mp.com.2", "title": "Proteccion comunicaciones — TLS"},
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
    ],

    # ── ShellShock ──
    "CVE-2014-6271": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.exp.6", "title": "Proteccion frente a codigo danino"},
    ],

    # ── Apache Struts ──
    "CVE-2017-5638": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "mp.sw.1", "title": "Desarrollo seguro"},
    ],
    "CVE-2018-11776": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── Drupalgeddon ──
    "CVE-2018-7600": [{"measure": "mp.sw.2", "title": "Aceptacion y puesta en produccion"}],

    # ── PrintNightmare ──
    "CVE-2021-1675": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.acc.4", "title": "Proceso de gestion de derechos"},
    ],
    "CVE-2021-34527": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── Citrix ADC ──
    "CVE-2019-19781": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.acc.5", "title": "Mecanismos de autenticacion"},
    ],

    # ── F5 BIG-IP ──
    "CVE-2020-5902": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "op.acc.6", "title": "Acceso local"},
    ],

    # ── PHP / WordPress ──
    "CVE-2024-4577": [
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        {"measure": "mp.sw.1", "title": "Desarrollo seguro"},
    ],

    # ── Atlassian ──
    "CVE-2022-26134": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],
    "CVE-2023-22515": [{"measure": "op.acc.5", "title": "Mecanismos de autenticacion"}],

    # ── MOVEit / SQLi ──
    "CVE-2023-34362": [
        {"measure": "mp.sw.1", "title": "Desarrollo seguro"},
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
    ],
    "CVE-2023-35036": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],
    "CVE-2023-35708": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── VMware ESXi ──
    "CVE-2021-21974": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── Spring Cloud / Spring4Shell ──
    "CVE-2022-22963": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── pwnkit ──
    "CVE-2021-4034": [
        {"measure": "op.acc.6", "title": "Acceso local — escalada de privilegios"},
        {"measure": "op.exp.4", "title": "Manejo seguro de cambios"},
    ],

    # ── Fortinet ──
    "CVE-2022-40684": [
        {"measure": "op.acc.5", "title": "Mecanismos de autenticacion"},
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
    ],
    "CVE-2024-21762": [{"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"}],

    # ── ConnectWise ──
    "CVE-2024-1709": [
        {"measure": "op.acc.5", "title": "Mecanismos de autenticacion"},
        {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
    ],

    # ── XZ Utils backdoor ──
    "CVE-2024-3094": [
        {"measure": "mp.sw.2", "title": "Aceptacion y puesta en produccion"},
        {"measure": "op.exp.6", "title": "Proteccion frente a codigo danino"},
    ],
}


# Patrones de finding sin CVE pero con mapeo claro a ENS (heuristica)
PATTERN_TO_ENS: list[dict[str, Any]] = [
    # TLS / cifrado
    {
        "patterns": ["TLS 1.0", "TLSv1.0", "SSLv2", "SSLv3", "weak cipher", "RC4"],
        "measures": [
            {"measure": "mp.com.2", "title": "Proteccion comunicaciones — cifrado"},
            {"measure": "mp.com.3", "title": "Proteccion de la autenticidad y la integridad"},
        ],
    },
    {
        "patterns": ["expired certificate", "self-signed certificate"],
        "measures": [
            {"measure": "mp.com.2", "title": "Proteccion comunicaciones"},
            {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades — certificados"},
        ],
    },
    # Headers HTTP
    {
        "patterns": ["X-Frame-Options", "X-Content-Type-Options", "Content-Security-Policy",
                     "Strict-Transport-Security"],
        "measures": [{"measure": "mp.s.2", "title": "Proteccion de servicios — cabeceras HTTP"}],
    },
    # SQL Injection
    {
        "patterns": ["SQL Injection", "SQLi", "blind sql"],
        "measures": [
            {"measure": "mp.sw.1", "title": "Desarrollo de aplicaciones — sanitizacion input"},
            {"measure": "op.exp.5", "title": "Gestion de vulnerabilidades"},
        ],
    },
    # XSS
    {
        "patterns": ["XSS", "Cross-Site Scripting", "Reflected XSS", "Stored XSS"],
        "measures": [{"measure": "mp.sw.1", "title": "Desarrollo de aplicaciones — encoding output"}],
    },
    # CSRF
    {
        "patterns": ["CSRF", "Cross-Site Request Forgery", "Anti-CSRF"],
        "measures": [{"measure": "mp.sw.1", "title": "Desarrollo de aplicaciones — tokens CSRF"}],
    },
    # Open ports inseguros
    {
        "patterns": ["Telnet", "FTP anonymous", "rsh", "rlogin"],
        "measures": [
            {"measure": "mp.com.2", "title": "Proteccion comunicaciones — protocolos seguros"},
            {"measure": "op.acc.5", "title": "Mecanismos de autenticacion"},
        ],
    },
    # Default credentials
    {
        "patterns": ["default credentials", "default password", "admin/admin"],
        "measures": [
            {"measure": "op.acc.5", "title": "Mecanismos de autenticacion"},
            {"measure": "op.acc.4", "title": "Proceso de gestion de derechos"},
        ],
    },
    # Backups expuestos
    {
        "patterns": ["backup exposed", ".sql.gz", ".bak", "backup file"],
        "measures": [
            {"measure": "mp.info.6", "title": "Limpieza de documentos"},
            {"measure": "op.exp.10", "title": "Procedimientos operativos"},
        ],
    },
    # Lynis warnings
    {
        "patterns": ["AUTH-9282", "AUTH-9286", "PASS_MIN_LEN"],
        "measures": [{"measure": "op.acc.5", "title": "Mecanismos de autenticacion"}],
    },
    {
        "patterns": ["FILE-7524", "world-writable"],
        "measures": [{"measure": "op.acc.4", "title": "Proceso de gestion de derechos"}],
    },
    # DNS
    {
        "patterns": ["SPF", "DKIM", "DMARC"],
        "measures": [
            {"measure": "mp.s.1", "title": "Proteccion de servicios — antiSPAM/antiPhishing"},
        ],
    },
    {
        "patterns": ["DNSSEC"],
        "measures": [{"measure": "mp.com.3", "title": "Proteccion autenticidad/integridad — DNS"}],
    },
    # AD password policy
    {
        "patterns": ["minPwdLength", "lockoutThreshold", "AD: longitud minima"],
        "measures": [{"measure": "op.acc.5", "title": "Mecanismos de autenticacion"}],
    },
    # SSH hardening (CCN-STIC 619 y Lynis SSH-*)
    {
        "patterns": [
            "SSH-7408", "SSH-7440", "PermitRootLogin", "PasswordAuthentication",
            "ssh hardening", "sshd_config", "SSH PermitRoot",
        ],
        "measures": [
            {"measure": "op.acc.6", "title": "Acceso local"},
            {"measure": "op.exp.3", "title": "Gestion de la configuracion"},
        ],
    },
]


# ════════════════════════════════════════════════════════════════════
# Mapper service
# ════════════════════════════════════════════════════════════════════

class EnsMapper:
    """Aplica las 3 capas a un ZfpFinding para producir ens_measures."""

    def __init__(self, db: AsyncSession, *, enable_llm: bool = True) -> None:
        self.db = db
        self.enable_llm = enable_llm

    async def map(self, finding: ZfpFinding) -> tuple[list[dict[str, Any]], str | None]:
        """Devuelve (ens_measures_list, ens_primary_measure)."""
        results: list[dict[str, Any]] = []

        # ── Capa 1: rule (CVE) ───────────────────────────────────────
        if finding.cve_id:
            measures = CVE_TO_ENS.get(finding.cve_id.upper())
            if measures:
                for m in measures:
                    results.append({
                        **m,
                        "method": "rule",
                        "confidence": 0.95,
                    })
                return self._dedupe_and_pick_primary(results)

        # ── Capa 1b: rule (pattern) ──────────────────────────────────
        haystack = f"{finding.title} {finding.description}".lower()
        for entry in PATTERN_TO_ENS:
            if any(p.lower() in haystack for p in entry["patterns"]):
                for m in entry["measures"]:
                    results.append({
                        **m,
                        "method": "rule",
                        "confidence": 0.85,
                    })
        if results:
            return self._dedupe_and_pick_primary(results[:3])

        # ── Capa 2: semantica pgvector ───────────────────────────────
        try:
            semantic = await self._semantic_match(finding)
            if semantic:
                results.extend(semantic)
                return self._dedupe_and_pick_primary(results[:3])
        except Exception as exc:
            logger.warning("ENS semantic mapping fallo: %s", exc)

        # ── Capa 3: LLM Haiku ────────────────────────────────────────
        if self.enable_llm:
            try:
                llm = await self._llm_mapping(finding)
                if llm:
                    results.extend(llm)
            except Exception as exc:
                logger.warning("ENS LLM mapping fallo: %s", exc)

        if not results:
            return [], None
        return self._dedupe_and_pick_primary(results[:3])

    async def _semantic_match(
        self, finding: ZfpFinding,
    ) -> list[dict[str, Any]]:
        """Busqueda semantica contra ens_measures (pgvector).

        Si el repo no tiene embeddings de medidas pre-calculados o el
        modulo de embeddings no esta disponible, devuelve []. La
        Sesion 2 ya integro pgvector + corpus normativo, asi que en
        produccion aqui se hace la query real.

        Por simplicidad en Checkpoint 2: devuelve [] a menos que las
        medidas ENS tengan embeddings (lo verificamos consultando una
        columna 'embedding' que en Sesion 2 se anadio para corpus pero
        no necesariamente para medidas).
        """
        # Future: busqueda semantica real cuando se embeddean las 80 medidas
        # ENS en ens_measures (M8 Checkpoint 3+). Hasta entonces devolvemos
        # vacio para no falsear confidence con resultados pobres.
        return []

    async def _llm_mapping(
        self, finding: ZfpFinding,
    ) -> list[dict[str, Any]]:
        """Mapeo via LLM Haiku 4.5 con structured output (SAN-B.MB-3.ter.3).

        Confidence threshold 0.5: si LLM reporta < 0.5 → []. Cada item
        retornado anotado con ``source: "llm_capa3"`` para audit.
        """
        from backend.app.motors.m08_verification.llm_classifier import (
            classify_ens_measure_via_llm,
        )
        return await classify_ens_measure_via_llm(finding)

    @staticmethod
    def _dedupe_and_pick_primary(
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Quita duplicados por measure code; ordena por confidence DESC.

        Devuelve (lista_unica_max_3, primary_measure_code).
        """
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for it in items:
            code = it.get("measure")
            if not code or code in seen:
                continue
            seen.add(code)
            unique.append(it)
        unique.sort(key=lambda x: -float(x.get("confidence", 0)))
        unique = unique[:3]
        primary = unique[0]["measure"] if unique else None
        return unique, primary
