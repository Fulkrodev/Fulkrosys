"""Shared utilities used by every MCP server."""
import asyncio
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional


# §1.6: metacaracteres de shell/intérprete. Aunque los comandos se lanzan con
# create_subprocess_exec(*cmd) (sin shell), varias tools pasan un único argumento
# que el PROPIO intérprete de la herramienta evalúa como cadena de comandos
# (msfconsole -qx "...", powershell -Command "..."). Un ';' o '$(...)' en un
# parámetro interpolado (module/target/technique/query/...) inyectaría comandos
# DENTRO de esa sesión. Defensa-en-profundidad sobre el gate scope+approval.
_INJECTION_CHARS = re.compile(r"[;&|`$\n\r<>\x00]")


def check_arg_safe(value: Any) -> Optional[str]:
    """Devuelve un mensaje de error si ``value`` contiene metacaracteres de
    inyección; ``None`` si es seguro. Sólo valida str (ints/otros son seguros)."""
    if isinstance(value, str) and _INJECTION_CHARS.search(value):
        return "argumento con metacaracteres no permitidos (posible inyeccion)"
    return None


def reject_unsafe_args(*values: Any) -> Optional[dict]:
    """Valida varios args; devuelve un dict de error MCP si alguno es inseguro,
    o ``None`` si todos son seguros. Uso: ``if (e := reject_unsafe_args(a, b)): return e``."""
    for v in values:
        err = check_arg_safe(v)
        if err:
            return {"error": f"INPUT REJECTED: {err}"}
    return None


async def run_command(
    cmd: list[str],
    timeout: int = 600,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    stdin_data: Optional[str] = None,
) -> dict:
    """Execute an external command and capture stdout/stderr."""
    full_env = {**os.environ, **(env or {})}

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin_data else None,
            cwd=cwd,
            env=full_env,
        )
        stdin_bytes = stdin_data.encode() if stdin_data else None
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=stdin_bytes),
            timeout=timeout,
        )
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "command": " ".join(cmd),
            "timed_out": False,
        }
    except asyncio.TimeoutError:
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "command": " ".join(cmd),
            "timed_out": True,
        }
    except FileNotFoundError:
        return {
            "returncode": -2,
            "stdout": "",
            "stderr": f"Command not found: {cmd[0]}",
            "command": " ".join(cmd),
            "timed_out": False,
        }
    except Exception as exc:
        return {
            "returncode": -3,
            "stdout": "",
            "stderr": f"Error: {exc}",
            "command": " ".join(cmd),
            "timed_out": False,
        }


def parse_nmap_xml(xml_string: str) -> dict:
    """Parse nmap XML output into a structured dict."""
    result: dict = {"hosts": [], "scan_info": {}}
    try:
        root = ET.fromstring(xml_string)
        scaninfo = root.find("scaninfo")
        if scaninfo is not None:
            result["scan_info"] = dict(scaninfo.attrib)

        for host_el in root.findall(".//host"):
            host: dict = {
                "ip": "", "hostname": "", "state": "",
                "ports": [], "os_matches": [], "scripts": [],
            }
            for addr in host_el.findall("address"):
                if addr.get("addrtype") == "ipv4":
                    host["ip"] = addr.get("addr", "")
                elif addr.get("addrtype") == "mac":
                    host["mac"] = addr.get("addr", "")

            hostname_el = host_el.find(".//hostname")
            if hostname_el is not None:
                host["hostname"] = hostname_el.get("name", "")

            status = host_el.find("status")
            if status is not None:
                host["state"] = status.get("state", "")

            for port_el in host_el.findall(".//port"):
                port = {
                    "port": int(port_el.get("portid", 0)),
                    "protocol": port_el.get("protocol", "tcp"),
                    "state": "", "service": "", "product": "",
                    "version": "", "extrainfo": "", "scripts": [],
                }
                state_el = port_el.find("state")
                if state_el is not None:
                    port["state"] = state_el.get("state", "")
                service_el = port_el.find("service")
                if service_el is not None:
                    port["service"] = service_el.get("name", "")
                    port["product"] = service_el.get("product", "")
                    port["version"] = service_el.get("version", "")
                    port["extrainfo"] = service_el.get("extrainfo", "")
                for script_el in port_el.findall("script"):
                    port["scripts"].append({
                        "id": script_el.get("id", ""),
                        "output": script_el.get("output", "")[:2000],
                    })
                host["ports"].append(port)

            for osmatch in host_el.findall(".//osmatch"):
                host["os_matches"].append({
                    "name": osmatch.get("name", ""),
                    "accuracy": int(osmatch.get("accuracy", 0)),
                })

            hostscript = host_el.find("hostscript")
            if hostscript is not None:
                for script_el in hostscript.findall("script"):
                    host["scripts"].append({
                        "id": script_el.get("id", ""),
                        "output": script_el.get("output", "")[:2000],
                    })

            result["hosts"].append(host)
    except ET.ParseError as exc:
        result["parse_error"] = str(exc)
        result["raw_xml"] = xml_string[:5000]
    return result


def parse_jsonl(raw: str) -> list:
    """Parse JSONL output (one JSON per line)."""
    results = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def parse_csv_output(raw: str, delimiter: str = ",") -> list[dict]:
    """Parse CSV/TSV output with header row."""
    import csv
    import io
    reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)
    return [dict(row) for row in reader]


def hash_output(data: Any) -> str:
    """SHA-256 hash for traceability."""
    if isinstance(data, str):
        return hashlib.sha256(data.encode()).hexdigest()
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def extract_cves(text: str) -> list[str]:
    """Extract CVE IDs from any text."""
    return list(set(re.findall(r"CVE-\d{4}-\d{4,}", text)))


def normalize_severity(raw_severity: str) -> str:
    """Normalize severity values to: critical/high/medium/low/info."""
    s = str(raw_severity).lower().strip()
    mapping = {
        "critical": "critical", "crit": "critical", "4": "critical", "muy_alta": "critical",
        "high": "high", "3": "high", "alta": "high", "alto": "high", "importante": "high",
        "medium": "medium", "med": "medium", "moderate": "medium",
        "2": "medium", "media": "medium", "medio": "medium",
        "low": "low", "1": "low", "baja": "low", "bajo": "low",
        "info": "info", "informational": "info", "0": "info", "none": "info",
    }
    return mapping.get(s, "info")
