"""Generate Ed25519 signing keys persistentes para FULKRO dev environment.

Resuelve Bug #1 (smoke automated atom 5.11):
- Backend startup_checks requiere 3 env vars Ed25519 ausentes en .env
- Sin keys persistentes, backend genera ephemeral · frontend middleware
  no puede verificar JWTs (mismatch) · login E2E falla

Keys generadas (PEM Ed25519, formato matching FULKRO_AUTH_PRIVATE_KEY existing):
- FULKRO_ML_PRIVATE_KEY (magic links + signing intents)
- FULKRO_BACKUP_SIGNING_KEY (M25 backup builder)
- FULKRO_AUTH_PUBLIC_KEY (frontend middleware JWT verification)
  → derivada de FULKRO_AUTH_PRIVATE_KEY existing en backend .env

Usage:
    cd /home/usuario/fulkro
    python scripts/generate_dev_signing_keys.py        # idempotent · skip si keys present
    python scripts/generate_dev_signing_keys.py --force  # regenera (INVALIDA firmas existing)

ADR-021 v6: production NEVER usa este script · keys via Vault/SOPS + per-project
rotation (MB-12 atom 12.5). Este script es solo dev infra · `.env` está
en `.gitignore` (NO commit secrets).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    print("ERROR: cryptography package not installed · source .venv/bin/activate primero")
    sys.exit(1)


# Backend .env keys (private)
BACKEND_PRIVATE_KEYS = (
    "FULKRO_ML_PRIVATE_KEY",
    "FULKRO_BACKUP_SIGNING_KEY",
)

# Backend has FULKRO_AUTH_PRIVATE_KEY existing · frontend needs matching public
AUTH_PRIVATE_KEY_VAR = "FULKRO_AUTH_PRIVATE_KEY"
AUTH_PUBLIC_KEY_VAR = "FULKRO_AUTH_PUBLIC_KEY"


def generate_ed25519_pem_pair() -> tuple[str, str]:
    """Genera Ed25519 keypair en formato PEM (matching FULKRO_AUTH_PRIVATE_KEY existing)."""
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii").strip()

    public_pem = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii").strip()

    return private_pem, public_pem


def derive_public_pem_from_private(private_pem: str) -> str:
    """Deriva public PEM desde private PEM existing (matching pair)."""
    private = serialization.load_pem_private_key(private_pem.encode(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError("Existing private key NO es Ed25519")
    return private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii").strip()


def parse_env_file(path: Path) -> dict[str, str]:
    """Parser .env preservando multi-line quoted values (matches uvicorn --env-file behavior)."""
    if not path.exists():
        return {}

    env: dict[str, str] = {}
    content = path.read_text()
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if "=" not in raw:
            i += 1
            continue
        key, _, value = raw.partition("=")
        key = key.strip()
        value = value.lstrip()
        # Multi-line quoted value · accumulate hasta cerrar quote
        if value.startswith('"') and not (
            value.endswith('"') and len(value) > 1 and value[-2] != "\\"
        ):
            collected = [value[1:]]
            i += 1
            while i < len(lines):
                line = lines[i]
                if line.rstrip().endswith('"'):
                    collected.append(line.rstrip()[:-1])
                    break
                collected.append(line)
                i += 1
            env[key] = "\n".join(collected)
        else:
            env[key] = value.strip().strip('"').strip("'")
        i += 1
    return env


def upsert_env_var(path: Path, key: str, value: str) -> bool:
    """Append or update single env var preservando rest of file. PEM multi-line wrapped en quotes."""
    if not path.exists():
        path.write_text("")
    content = path.read_text()
    lines = content.splitlines()

    # Build new entry (quote if multi-line o tiene chars especiales)
    if "\n" in value or " " in value or "=" in value:
        new_entry = f'{key}="{value}"'
    else:
        new_entry = f"{key}={value}"

    # Find existing entry · collapse multi-line if any
    new_lines = []
    i = 0
    found = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith(f"{key}="):
            if not found:
                new_lines.append(new_entry)
                found = True
            # Skip continuation lines si multi-line existing
            value_part = line.partition("=")[2].lstrip()
            if value_part.startswith('"') and not value_part.rstrip().endswith('"'):
                i += 1
                while i < len(lines) and not lines[i].rstrip().endswith('"'):
                    i += 1
            i += 1
            continue
        new_lines.append(line)
        i += 1

    if not found:
        new_lines.append(new_entry)

    path.write_text("\n".join(new_lines) + "\n")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Regenera keys incluso si presentes")
    parser.add_argument("--backend-env", default=".env", help="Path backend .env")
    parser.add_argument("--frontend-env", default="frontend/.env", help="Path frontend .env")
    args = parser.parse_args()

    backend_env = Path(args.backend_env)
    frontend_env = Path(args.frontend_env)

    print("=== FULKRO dev signing keys generation ===")
    print(f"Backend env: {backend_env.absolute()}")
    print(f"Frontend env: {frontend_env.absolute()}")
    print()

    existing_backend = parse_env_file(backend_env)
    existing_frontend = parse_env_file(frontend_env)

    # 1. Backend private keys (ML + BACKUP)
    for key_var in BACKEND_PRIVATE_KEYS:
        has = bool(existing_backend.get(key_var, "").strip())
        if has and not args.force:
            print(f"  ✓ {key_var} already present · skip (--force regenera)")
            continue
        private_pem, _ = generate_ed25519_pem_pair()
        upsert_env_var(backend_env, key_var, private_pem)
        print(f"  ✓ Generated {key_var} (PEM Ed25519)")

    # 2. Sync FULKRO_AUTH_PUBLIC_KEY frontend desde backend private existing
    backend_auth_private = existing_backend.get(AUTH_PRIVATE_KEY_VAR, "")
    if not backend_auth_private:
        print(f"  ⚠ {AUTH_PRIVATE_KEY_VAR} ausente backend .env · generando NEW pair")
        backend_auth_private, _ = generate_ed25519_pem_pair()
        upsert_env_var(backend_env, AUTH_PRIVATE_KEY_VAR, backend_auth_private)
        print(f"  ✓ Generated {AUTH_PRIVATE_KEY_VAR} backend (PEM Ed25519)")

    derived_public = derive_public_pem_from_private(backend_auth_private)
    existing_frontend_public = existing_frontend.get(AUTH_PUBLIC_KEY_VAR, "")
    if existing_frontend_public.strip() == derived_public.strip() and not args.force:
        print(f"  ✓ {AUTH_PUBLIC_KEY_VAR} frontend matches backend · skip")
    else:
        upsert_env_var(frontend_env, AUTH_PUBLIC_KEY_VAR, derived_public)
        print(f"  ✓ Synced {AUTH_PUBLIC_KEY_VAR} frontend ← derived backend private")

    print()
    print("=== Done ===")
    print("Restart backend: uvicorn backend.app.main:app --port 8000 --env-file .env")
    print("Restart frontend: cd frontend && npx next dev --port 3000")
    print()
    print("SECURITY: .env files in .gitignore · NUNCA commit · production via Vault/SOPS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
