"""Playbooks SAFE del agente de remediación · ADR-055 Fase 3.

Cada playbook es un dict con funciones puras de I/O controlado:
  read_state(params) -> dict   (DEBE incluir 'compliant': bool · solo lectura)
  snapshot(params)   -> dict   (estado a guardar para revertir · opcional)
  apply(params)      -> None    (idempotente · subprocess con LISTA de args · NO shell)
  rollback(params, snapshot) -> None

REGISTRO horneado: el agente SOLO ejecuta lo que está aquí (allowlist). NUNCA shell
arbitrario, NUNCA eval, NUNCA descarga de código. Añadir un playbook = añadirlo aquí
y al catálogo del servidor (provider='host').
"""
from __future__ import annotations

import re
import subprocess  # noqa: S404 · usado SOLO con listas de args (sin shell)
from pathlib import Path
from typing import Any

SSHD_CONFIG = "/etc/ssh/sshd_config"


def _run(args: list[str]) -> str:
    """Ejecuta un comando como lista de args (NUNCA shell=True). Devuelve stdout."""
    proc = subprocess.run(  # noqa: S603 · args validados · sin shell
        args, capture_output=True, text=True, check=True, timeout=120,
    )
    return proc.stdout


# ── harden_sshd_root_login (SAFE_AUTO) ──────────────────────────────────────


def _sshd_read(_params: dict[str, Any]) -> dict[str, Any]:
    text = Path(SSHD_CONFIG).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?mi)^\s*PermitRootLogin\s+(\S+)", text)
    value = m.group(1).lower() if m else "prohibit-password"
    return {"compliant": value == "no", "permit_root_login": value}


def _sshd_snapshot(_params: dict[str, Any]) -> dict[str, Any]:
    return {"sshd_config": Path(SSHD_CONFIG).read_text(encoding="utf-8")}


def _sshd_apply(_params: dict[str, Any]) -> None:
    path = Path(SSHD_CONFIG)
    text = path.read_text(encoding="utf-8")
    if re.search(r"(?mi)^\s*PermitRootLogin\s+\S+", text):
        text = re.sub(
            r"(?mi)^\s*PermitRootLogin\s+\S+", "PermitRootLogin no", text,
        )
    else:
        text += "\nPermitRootLogin no\n"
    path.write_text(text, encoding="utf-8")
    _run(["sshd", "-t"])  # valida sintaxis ANTES de recargar (fail-safe)
    _run(["systemctl", "reload", "sshd"])


def _sshd_rollback(_params: dict[str, Any], snapshot: dict[str, Any]) -> None:
    Path(SSHD_CONFIG).write_text(snapshot["sshd_config"], encoding="utf-8")
    _run(["sshd", "-t"])
    _run(["systemctl", "reload", "sshd"])


# ── enable_host_firewall_rule (SAFE_AUTO) ───────────────────────────────────


def _fw_read(params: dict[str, Any]) -> dict[str, Any]:
    port = str(params.get("port", ""))
    status = _run(["ufw", "status"])
    # ufw status lista "443/tcp  DENY  ..." (con sufijo de protocolo) o "443 DENY".
    # El regex anterior (^{port}\s+DENY) sólo casaba el puerto desnudo a principio
    # de línea → falso negativo con "443/tcp DENY" → la regla parecía no aplicada.
    denied = bool(
        re.search(rf"(?m)(?:^|\s){re.escape(port)}(?:/\w+)?\s+DENY", status)
    )
    return {"compliant": denied, "port": port}


def _fw_apply(params: dict[str, Any]) -> None:
    port = str(int(params["port"]))  # int() valida que es numérico (anti-inyección)
    _run(["ufw", "deny", port])


def _fw_rollback(params: dict[str, Any], _snapshot: dict[str, Any]) -> None:
    port = str(int(params["port"]))
    _run(["ufw", "delete", "deny", port])


# ── apply_package_security_update (GUARDED · requiere autorización) ──────────


def _pkg_read(params: dict[str, Any]) -> dict[str, Any]:
    pkg = str(params.get("package", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9+._-]*", pkg):
        raise ValueError(f"nombre de paquete inválido: {pkg!r}")
    try:
        out = _run(["dpkg-query", "-W", "-f=${Version}", pkg])
        version = out.strip()
    except subprocess.CalledProcessError:
        version = None
    # No podemos saber "parcheado" sin metadatos de seguridad → compliant=False
    # para permitir la actualización cuando se solicite explícitamente (GUARDED).
    return {"compliant": False, "package": pkg, "version": version}


def _pkg_apply(params: dict[str, Any]) -> None:
    pkg = str(params["package"])
    if not re.fullmatch(r"[a-z0-9][a-z0-9+._-]*", pkg):
        raise ValueError(f"nombre de paquete inválido: {pkg!r}")
    _run(["apt-get", "update", "-q"])
    _run(["apt-get", "install", "--only-upgrade", "-y", pkg])


def _pkg_rollback(params: dict[str, Any], snapshot: dict[str, Any]) -> None:
    prev = (snapshot or {}).get("version")
    pkg = str(params["package"])
    if prev:
        # Reinstala la versión previa exacta (best-effort · puede no estar en cache).
        _run(["apt-get", "install", "-y", "--allow-downgrades", f"{pkg}={prev}"])


REGISTRY: dict[str, dict[str, Any]] = {
    "harden_sshd_root_login": {
        "read_state": _sshd_read,
        "snapshot": _sshd_snapshot,
        "apply": _sshd_apply,
        "rollback": _sshd_rollback,
    },
    "enable_host_firewall_rule": {
        "read_state": _fw_read,
        "apply": _fw_apply,
        "rollback": _fw_rollback,
    },
    "apply_package_security_update": {
        "read_state": _pkg_read,
        "snapshot": _pkg_read,
        "apply": _pkg_apply,
        "rollback": _pkg_rollback,
    },
}
