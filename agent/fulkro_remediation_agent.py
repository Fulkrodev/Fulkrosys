#!/usr/bin/env python3
"""FULKRO · Agente de remediación on-prem (ADR-055 Fase 3).

Se despliega DENTRO de la infraestructura del cliente. BLINDADO por diseño:

  - Sin puertos entrantes: el agente hace PULL (cero superficie de ataque inbound).
  - Solo ejecuta playbooks de una ALLOWLIST horneada (dato ≠ instrucción · sin shell
    arbitrario · sin eval).
  - Cada comando DEBE llevar firma Ed25519 válida del servidor (clave pública
    fijada en el enrollment). Comando forjado/manipulado → rechazado.
  - Cada resultado se firma con la clave del agente (integridad del report).
  - DRY-RUN por defecto: NO toca el sistema salvo que se pase --apply.
  - Cada playbook es idempotente, hace snapshot previo y sabe revertir.

Dependencias: solo stdlib + `cryptography`. HTTP con urllib (sin httpx).

Uso:
  # 1. Enrolar (token de un solo uso que te da Marcos desde el panel admin):
  python3 fulkro_remediation_agent.py enroll --server https://fulkro.es \\
      --token <ENROLLMENT_TOKEN>
  # 2. Ejecutar el bucle (dry-run por defecto · --apply para aplicar de verdad):
  python3 fulkro_remediation_agent.py run --server https://fulkro.es [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

import playbooks  # módulo hermano · registro de playbooks SAFE

STATE_DIR = Path(os.environ.get("FULKRO_AGENT_STATE", "/var/lib/fulkro-agent"))
STATE_FILE = STATE_DIR / "agent_state.json"
AGENT_VERSION = "1.0.0"

# Allowlist horneada (DEBE coincidir con provider='host' del catálogo del servidor).
PLAYBOOK_ALLOWLIST = frozenset(playbooks.REGISTRY.keys())


# ── cripto (espejo de backend/.../agent_protocol.py · canónico + Ed25519) ────


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def sign_payload(private_raw: bytes, payload: dict[str, Any]) -> str:
    sk = Ed25519PrivateKey.from_private_bytes(private_raw)
    return sk.sign(canonical_bytes(payload)).hex()


def verify_payload(public_raw: bytes, payload: dict[str, Any], sig_hex: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_raw).verify(
            bytes.fromhex(sig_hex), canonical_bytes(payload),
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


# ── estado local ────────────────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # §1.7: el directorio contiene la clave privada del agente. Restringir
        # antes de escribir (mkdir hereda el umask → puede quedar 0o755 world-read
        # durante la ventana de enrolamiento).
        STATE_DIR.chmod(0o700)
    except OSError:
        pass
    STATE_FILE.write_text(json.dumps(state, indent=2))
    try:
        STATE_FILE.chmod(0o600)  # clave privada del agente · solo root
    except OSError:
        pass


# ── HTTP ──────────────────────────────────────────────────────────────────────


def _post(url: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


# ── enrollment ──────────────────────────────────────────────────────────────


def cmd_enroll(args: argparse.Namespace) -> int:
    priv = Ed25519PrivateKey.generate()
    priv_raw = priv.private_bytes_raw()
    pub_raw = priv.public_key().public_bytes_raw()

    resp = _post(
        f"{args.server}/api/v1/agent/remediation/enroll",
        {
            "token": args.token,
            "agent_pubkey_hex": pub_raw.hex(),
            "agent_version": AGENT_VERSION,
        },
    )
    state = {
        "agent_id": resp["agent_id"],
        "agent_token": resp["agent_token"],
        "server_pubkey_hex": resp["server_pubkey_hex"],
        "agent_private_hex": priv_raw.hex(),
        "server": args.server,
        "capabilities": resp.get("capabilities", []),
    }
    save_state(state)
    print(f"Enrolado OK · agent_id={resp['agent_id']}")
    print(f"Playbooks soportados: {resp.get('capabilities')}")
    return 0


# ── bucle de ejecución ────────────────────────────────────────────────────────


def _execute_command(cmd: dict, state: dict, apply: bool) -> dict:
    """Valida (allowlist + firma del servidor) y ejecuta el playbook. Devuelve result."""
    payload = cmd["payload"]
    playbook_id = payload.get("playbook_id")

    # GUARD 1 · allowlist (anti-injection · dato ≠ instrucción).
    if playbook_id not in PLAYBOOK_ALLOWLIST:
        return {"outcome": "failed", "error": f"playbook no permitido: {playbook_id}"}

    # GUARD 2 · firma del servidor (clave pública fijada en el enrollment).
    server_pub = bytes.fromhex(state["server_pubkey_hex"])
    if not verify_payload(server_pub, payload, cmd["server_signature"]):
        return {"outcome": "failed", "error": "firma del servidor inválida · rechazado"}

    playbook = playbooks.REGISTRY[playbook_id]
    params = payload.get("params") or {}
    try:
        # Ciclo seguro: preflight → snapshot → (apply) → verify → rollback.
        before = playbook["read_state"](params)
        if before.get("compliant") is True:
            return {"outcome": "skipped_compliant", "state_before": before}
        if not apply:
            return {"outcome": "succeeded", "dry_run": True, "state_before": before}
        snapshot = playbook.get("snapshot", playbook["read_state"])(params)
        playbook["apply"](params)
        after = playbook["read_state"](params)
        if after.get("compliant") is True:
            return {"outcome": "succeeded", "state_before": before, "state_after": after}
        # Verify falló → rollback.
        playbook["rollback"](params, snapshot)
        return {"outcome": "rolled_back", "reason": "verify falló tras aplicar"}
    except Exception as exc:  # noqa: BLE001 · cualquier fallo → report, no crash
        return {"outcome": "failed", "error": str(exc)}


def cmd_run(args: argparse.Namespace) -> int:
    state = load_state()
    if "agent_token" not in state:
        print("No enrolado. Ejecuta primero: enroll", file=sys.stderr)
        return 2
    server = args.server or state.get("server")
    token = state["agent_token"]
    priv_raw = bytes.fromhex(state["agent_private_hex"])

    print(f"Agente en marcha · apply={args.apply} · poll cada {args.interval}s")
    # §1.7: backoff exponencial ante errores de red (evita polling agresivo /
    # thundering herd si el servidor está caído). Se resetea al primer éxito.
    backoff = 0.0
    while True:
        try:
            resp = _get(f"{server}/api/v1/agent/remediation/commands", token)
            for cmd in resp.get("commands", []):
                result = _execute_command(cmd, state, args.apply)
                report_payload = {"command_id": cmd["command_id"], "result": result}
                sig = sign_payload(priv_raw, report_payload)
                _post(
                    f"{server}/api/v1/agent/remediation/commands/"
                    f"{cmd['command_id']}/report",
                    {"result": result, "report_signature": sig},
                    token=token,
                )
                print(f"  comando {cmd['command_id'][:8]} → {result['outcome']}")
            backoff = 0.0  # éxito → reset
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code}: {exc.reason}", file=sys.stderr)
            if exc.code == 401:
                print("Agente revocado o token inválido · saliendo.", file=sys.stderr)
                return 3
            backoff = min(backoff * 2 + 1.0, 300.0)
        except Exception as exc:  # noqa: BLE001
            print(f"error de red: {exc}", file=sys.stderr)
            backoff = min(backoff * 2 + 1.0, 300.0)
        if args.once:
            return 0
        # jitter para desincronizar agentes ante recuperación del servidor.
        time.sleep(args.interval + backoff + random.uniform(0.0, 1.0))


def main() -> int:
    p = argparse.ArgumentParser(description="FULKRO agente de remediación on-prem")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enroll", help="canjea el token de enrollment")
    e.add_argument("--server", required=True)
    e.add_argument("--token", required=True)
    e.set_defaults(func=cmd_enroll)

    r = sub.add_parser("run", help="bucle de pull/ejecución/report")
    r.add_argument("--server", default=None)
    r.add_argument("--apply", action="store_true", help="aplica de verdad (def: dry-run)")
    r.add_argument("--interval", type=int, default=60)
    r.add_argument("--once", action="store_true", help="una sola pasada y sale")
    r.set_defaults(func=cmd_run)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
