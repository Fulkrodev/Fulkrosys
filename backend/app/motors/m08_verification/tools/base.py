"""M8 v5.1 — Base comun para los runners de herramientas.

Cada runner sigue el contrato:

    class XxxRunner:
        TOOL = "nuclei" / "nmap" / etc.
        @staticmethod
        def is_available() -> bool       # shutil.which(binary) is not None
        @classmethod
        def parse_output(raw: bytes) -> list[FindingCandidate]   # parser puro
        @classmethod
        async def run(targets, ...) -> RunnerResult              # subprocess

Asi:
- ``parse_output`` es testeable con fixtures sin tool instalada.
- ``run`` se mockea en unit tests; el demo y los tests de integracion
  reales lo invocan cuando la tool esta disponible.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import signal
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, TypedDict


# ────────────────────────────────────────────────────────────────────
# Tipos comunes
# ────────────────────────────────────────────────────────────────────

class FindingCandidate(TypedDict, total=False):
    """Schema normalizado que produce todo runner antes del ZFP.

    Campos required: title, severity, affected_host, tool.
    Resto opcionales (None si no aplica).
    """
    title: str
    description: str
    severity: str               # critical | high | medium | low | info
    cve_id: str | None
    cvss_score: float | None
    cvss_vector: str | None
    cwe_id: str | None
    affected_host: str
    affected_port: int | None
    affected_service: str | None
    affected_service_version: str | None
    affected_url: str | None
    affected_os: str | None
    raw_output_excerpt: str     # primeros ~500 chars del raw output
    tool: str
    tool_metadata: dict[str, Any]


@dataclass
class RunnerResult:
    """Resultado de invocar una tool sobre un scope."""
    tool: str
    targets: list[str]
    started_at: datetime
    finished_at: datetime
    return_code: int
    raw_output: bytes
    raw_output_hash: str        # SHA-256 hex
    raw_output_path: str | None # MinIO key (si subido)
    findings: list[FindingCandidate] = field(default_factory=list)
    error: str | None = None
    timed_out: bool = False
    process_killed: bool = False  # True si lo paro el kill switch

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()


# ────────────────────────────────────────────────────────────────────
# Excepciones
# ────────────────────────────────────────────────────────────────────

class RunnerError(Exception):
    """Error generico de un runner de tool."""


class RunnerNotInstalled(RunnerError):
    """El binario de la tool no esta en PATH."""


class RunnerInvocationError(RunnerError):
    """La tool se ejecuto pero devolvio un error o output invalido."""


class RunnerTimeoutError(RunnerError):
    """La tool excedio su timeout."""


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def hash_output(data: bytes) -> str:
    """SHA-256 hex del raw output."""
    return hashlib.sha256(data).hexdigest()


def excerpt(data: bytes | str, max_chars: int = 500) -> str:
    """Primeros max_chars del raw output (decodificando si es bytes)."""
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="replace")
    else:
        text = data
    return text[:max_chars]


def is_binary_available(binary: str) -> bool:
    """``shutil.which(binary) is not None``."""
    return shutil.which(binary) is not None


async def run_subprocess(
    cmd: list[str],
    *,
    timeout_seconds: int,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    new_process_group: bool = True,
) -> tuple[int, bytes, bytes, bool]:
    """Ejecuta un subprocess capturando stdout+stderr.

    Si ``new_process_group=True`` (default), arranca con ``preexec_fn=
    os.setsid`` para que el kill switch pueda matar el grupo entero
    via ``os.killpg(SIGTERM)``.

    Returns: (return_code, stdout, stderr, timed_out).
    """
    full_env = {**os.environ, **(env or {})} if env else None

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=full_env,
        cwd=str(cwd) if cwd else None,
        preexec_fn=(os.setsid if new_process_group else None),
    )
    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        timed_out = True
        # Mata el grupo entero si estaba en setsid
        try:
            if new_process_group and proc.pid:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=3.0,
            )
        except asyncio.TimeoutError:
            try:
                if new_process_group and proc.pid:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = b"", b""
    return proc.returncode or 0, stdout, stderr, timed_out


# ────────────────────────────────────────────────────────────────────
# Severity normalization
# ────────────────────────────────────────────────────────────────────

SEVERITY_ALIAS = {
    "info": "info", "informational": "info", "low": "low",
    "medium": "medium", "moderate": "medium", "high": "high",
    "critical": "critical", "crit": "critical",
}


def normalize_severity(raw: str) -> str:
    """Devuelve una severity en {critical, high, medium, low, info}."""
    if not raw:
        return "info"
    return SEVERITY_ALIAS.get(raw.strip().lower(), "info")


# ────────────────────────────────────────────────────────────────────
# Base class abstracta (no obligatoria — los runners pueden no heredar)
# ────────────────────────────────────────────────────────────────────

class BaseRunner:
    """Helpers comunes; los runners pueden heredar opcionalmente."""

    TOOL: ClassVar[str] = "unknown"
    BINARY: ClassVar[str] = "unknown"
    DEFAULT_TIMEOUT_SECONDS: ClassVar[int] = 600

    @classmethod
    def is_available(cls) -> bool:
        return is_binary_available(cls.BINARY)

    @classmethod
    def ensure_available(cls) -> None:
        if not cls.is_available():
            raise RunnerNotInstalled(
                f"{cls.TOOL}: binario '{cls.BINARY}' no encontrado en PATH. "
                f"Instale el paquete correspondiente o use el container "
                f"fulkro-scanner."
            )

    @classmethod
    def make_result(
        cls,
        targets: list[str],
        started_at: datetime,
        return_code: int,
        raw_output: bytes,
        findings: list[FindingCandidate] | None = None,
        error: str | None = None,
        timed_out: bool = False,
        process_killed: bool = False,
    ) -> RunnerResult:
        return RunnerResult(
            tool=cls.TOOL,
            targets=targets,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            return_code=return_code,
            raw_output=raw_output,
            raw_output_hash=hash_output(raw_output),
            raw_output_path=None,
            findings=findings or [],
            error=error,
            timed_out=timed_out,
            process_killed=process_killed,
        )

    @classmethod
    def from_mcp_response(
        cls,
        mcp_resp: dict,
        targets: list[str],
        started_at: datetime,
    ) -> RunnerResult:
        """Adapter MCP response → RunnerResult (SAN-B.MB-7.bis).

        Pattern uniforme para los 8 runners wire-uped vía
        ``try_invoke_mcp_or_none``. MCP findings vienen pre-normalizadas
        via ``shared.output_normalizer.normalize_finding`` con shape
        compatible FindingCandidate (mismas keys core).
        """
        return runner_result_from_mcp(mcp_resp, cls.TOOL, targets, started_at)


def runner_result_from_mcp(
    mcp_resp: dict,
    tool: str,
    targets: list[str],
    started_at: datetime,
) -> RunnerResult:
    """Module-level helper para clases que NO heredan BaseRunner
    (DnsChecker, AdPasswordChecker · SAN-B.MB-7.bis)."""
    data = (mcp_resp or {}).get("data") or {}
    findings = data.get("findings") or []
    command_str = data.get("command", "")
    raw_output = command_str.encode("utf-8")
    return RunnerResult(
        tool=tool,
        targets=targets or [data.get("target", "unknown")],
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        return_code=0,
        raw_output=raw_output,
        raw_output_hash=hash_output(raw_output),
        raw_output_path=None,
        findings=findings,
        error=None,
        timed_out=False,
    )
