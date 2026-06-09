"""Dev helper: derive Ed25519 public PEM from FULKRO_AUTH_PRIVATE_KEY in .env and
write frontend/.env.local so the Next middleware verifies the SAME keypair the
backend signs with (resuelve OPS-052 72ª · ephemeral-key login loop).

NO toca secretos en prod. Solo dev local.
"""
from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    vals = dotenv_values(ROOT / ".env")
    priv = vals.get("FULKRO_AUTH_PRIVATE_KEY")
    if not priv:
        raise SystemExit("NO FULKRO_AUTH_PRIVATE_KEY in .env")
    priv_pem = priv.replace("\\n", "\n").strip()
    key = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    pub_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
        .strip()
    )
    out = ROOT / "frontend" / ".env.local"
    out.write_text(
        "FULKRO_BACKEND_URL=http://localhost:8000\n"
        f'FULKRO_AUTH_PUBLIC_KEY="{pub_pem}"\n'
    )
    print(f"key type: {type(key).__name__}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
