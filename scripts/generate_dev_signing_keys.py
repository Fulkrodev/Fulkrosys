"""Genera las claves de firma Ed25519 persistentes del entorno de desarrollo de FULKRO.

Sin estas claves `backend/app/startup_checks.py` aborta el arranque, y el
middleware de Next no puede verificar los JWT que firma el backend (el backend
genera un par efímero en cada arranque y el login entra en bucle de redirección
a /login).

Claves que gestiona (PEM Ed25519):
- FULKRO_AUTH_PRIVATE_KEY    · firma de la cookie de sesión (fulkro_session)
- FULKRO_ML_PRIVATE_KEY      · magic links + intents de firma
- FULKRO_BACKUP_SIGNING_KEY  · firma de backups (M25)
- FULKRO_AUTH_PUBLIC_KEY     · derivada de FULKRO_AUTH_PRIVATE_KEY, la consume
                               el middleware del frontend (frontend/middleware.ts)

Uso:
    python scripts/generate_dev_signing_keys.py                  # idempotente
    python scripts/generate_dev_signing_keys.py --force          # rota LAS TRES privadas
    python scripts/generate_dev_signing_keys.py --env-file .env.demo --no-frontend-env

Idempotencia: sin --force no se toca ninguna clave que ya exista; la pública se
sigue derivando de la privada presente. Con --force se regeneran las tres
privadas, incluida AUTH, lo que **invalida las sesiones vivas** (el script lo
avisa por pantalla cuando ocurre).

ADR-021 v6: producción NUNCA usa este script · las claves van por Vault/SOPS con
rotación por proyecto (MB-12 atom 12.5). Esto es sólo infraestructura de
desarrollo; los ficheros de entorno que escribe están en `.gitignore`.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
except ImportError:
    print("ERROR: falta el paquete cryptography · activa el venv (source .venv/bin/activate)")
    sys.exit(1)


# Claves privadas del backend distintas de AUTH (AUTH se trata aparte porque de
# ella se deriva la pública que necesita el frontend).
BACKEND_PRIVATE_KEYS = (
    "FULKRO_ML_PRIVATE_KEY",
    "FULKRO_BACKUP_SIGNING_KEY",
)

AUTH_PRIVATE_KEY_VAR = "FULKRO_AUTH_PRIVATE_KEY"
AUTH_PUBLIC_KEY_VAR = "FULKRO_AUTH_PUBLIC_KEY"


def generate_ed25519_pem_pair() -> tuple[str, str]:
    """Genera un par Ed25519 en formato PEM (privada PKCS8, pública SubjectPublicKeyInfo)."""
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
    """Deriva la pública PEM a partir de una privada PEM ya existente (mismo par)."""
    private = serialization.load_pem_private_key(
        private_pem.replace("\\n", "\n").encode(), password=None
    )
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError(f"{AUTH_PRIVATE_KEY_VAR} no es una clave Ed25519")
    return private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii").strip()


def parse_env_file(path: Path) -> dict[str, str]:
    """Lee un .env preservando valores multilínea entrecomillados (como uvicorn --env-file)."""
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
        # Valor multilínea entrecomillado · acumular hasta cerrar la comilla
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
    """Crea o actualiza una variable preservando el resto del fichero.

    Devuelve True si la variable ya existía (se ha sustituido). Los PEM
    multilínea se escriben entrecomillados.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")
    content = path.read_text()
    lines = content.splitlines()

    if "\n" in value or " " in value or "=" in value:
        new_entry = f'{key}="{value}"'
    else:
        new_entry = f"{key}={value}"

    new_lines: list[str] = []
    i = 0
    found = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith(f"{key}="):
            if not found:
                new_lines.append(new_entry)
                found = True
            # Saltar las líneas de continuación si el valor previo era multilínea
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


def restrict_permissions(path: Path) -> None:
    """0600 en los ficheros que contienen claves privadas (best effort)."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera/sincroniza las claves Ed25519 de desarrollo de FULKRO.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenera LAS TRES privadas aunque ya existan (invalida las sesiones vivas)",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Fichero de entorno del backend donde escribir las claves (por defecto: .env)",
    )
    parser.add_argument(
        "--backend-env",
        default=None,
        help="Alias histórico de --env-file (se mantiene por compatibilidad)",
    )
    parser.add_argument(
        "--frontend-env",
        default="frontend/.env",
        help="Fichero de entorno del frontend para la pública (por defecto: frontend/.env)",
    )
    parser.add_argument(
        "--frontend-env-local",
        default="frontend/.env.local",
        help="Fichero .env.local del frontend; Next le da MÁS precedencia que a .env",
    )
    parser.add_argument(
        "--no-frontend-env",
        action="store_true",
        help="No escribir ficheros del frontend (el demo pasa la pública por variables del contenedor)",
    )
    parser.add_argument("--quiet", action="store_true", help="Sólo avisos y errores")
    args = parser.parse_args()

    if (
        args.env_file
        and args.backend_env
        and Path(args.env_file) != Path(args.backend_env)
    ):
        print("ERROR: --env-file y --backend-env apuntan a ficheros distintos · usa sólo uno")
        return 2

    backend_env = Path(args.env_file or args.backend_env or ".env")
    frontend_env = Path(args.frontend_env)
    frontend_env_local = Path(args.frontend_env_local)

    def say(msg: str = "") -> None:
        if not args.quiet:
            print(msg)

    say("=== Claves de firma de desarrollo FULKRO ===")
    say(f"Entorno backend:  {backend_env.absolute()}")
    if args.no_frontend_env:
        say("Entorno frontend: (omitido por --no-frontend-env)")
    else:
        say(f"Entorno frontend: {frontend_env.absolute()}")
    say()

    existing_backend = parse_env_file(backend_env)

    # 1. Privadas del backend distintas de AUTH (ML + BACKUP)
    for key_var in BACKEND_PRIVATE_KEYS:
        has = bool(existing_backend.get(key_var, "").strip())
        if has and not args.force:
            say(f"  = {key_var} ya presente · se conserva (--force la regenera)")
            continue
        private_pem, _ = generate_ed25519_pem_pair()
        upsert_env_var(backend_env, key_var, private_pem)
        say(f"  + {key_var} {'regenerada' if has else 'generada'} (PEM Ed25519)")

    # 2. AUTH: la única cuya rotación invalida sesiones vivas.
    #    Antes esta rama ignoraba --force y sólo actuaba si la clave faltaba.
    auth_existing = existing_backend.get(AUTH_PRIVATE_KEY_VAR, "").strip()
    auth_rotated = False
    if not auth_existing:
        backend_auth_private, _ = generate_ed25519_pem_pair()
        upsert_env_var(backend_env, AUTH_PRIVATE_KEY_VAR, backend_auth_private)
        say(f"  + {AUTH_PRIVATE_KEY_VAR} ausente · generada (PEM Ed25519)")
    elif args.force:
        backend_auth_private, _ = generate_ed25519_pem_pair()
        upsert_env_var(backend_env, AUTH_PRIVATE_KEY_VAR, backend_auth_private)
        auth_rotated = True
        say(f"  + {AUTH_PRIVATE_KEY_VAR} ROTADA por --force (PEM Ed25519)")
    else:
        backend_auth_private = auth_existing
        say(f"  = {AUTH_PRIVATE_KEY_VAR} ya presente · se conserva (--force la rota)")

    restrict_permissions(backend_env)

    # 3. Pública derivada de la privada AUTH que acabe de quedar en el fichero.
    try:
        derived_public = derive_public_pem_from_private(backend_auth_private)
    except Exception as exc:  # clave corrupta o de otro algoritmo
        print(f"ERROR: no se pudo derivar la pública desde {AUTH_PRIVATE_KEY_VAR}: {exc}")
        return 1

    # La pública también en el fichero del backend: así un despliegue con un
    # único fichero de entorno (el demo usa .env.demo) puede pasársela al
    # contenedor del frontend sin volver a derivarla. El backend la ignora
    # (backend/app/config.py declara extra="ignore").
    upsert_env_var(backend_env, AUTH_PUBLIC_KEY_VAR, derived_public)
    say(f"  + {AUTH_PUBLIC_KEY_VAR} escrita en {backend_env} (derivada de la privada)")

    if not args.no_frontend_env:
        upsert_env_var(frontend_env, AUTH_PUBLIC_KEY_VAR, derived_public)
        say(f"  + {AUTH_PUBLIC_KEY_VAR} sincronizada en {frontend_env}")

        # Next.js da MÁS precedencia a .env.local que a .env. Si existe uno
        # viejo (lo escribe scripts/dev_derive_pubkey.py) con otra clave, gana
        # él y vuelve el bucle de redirección a /login. Lo sincronizamos si
        # existe; no lo creamos si no existe, para no dejar ficheros de más.
        if frontend_env_local.exists():
            previous = parse_env_file(frontend_env_local).get(AUTH_PUBLIC_KEY_VAR, "").strip()
            if previous == derived_public:
                say(f"  = {frontend_env_local} ya tenía la misma pública")
            else:
                upsert_env_var(frontend_env_local, AUTH_PUBLIC_KEY_VAR, derived_public)
                print(
                    f"  ! {frontend_env_local} tenía OTRA {AUTH_PUBLIC_KEY_VAR} y Next le da "
                    f"más precedencia que a {frontend_env}: se ha actualizado."
                )
        else:
            say(
                f"  = {frontend_env_local} no existe · no se crea. Si luego ejecutas "
                "scripts/dev_derive_pubkey.py, ese fichero pasará a mandar: vuelve a "
                "ejecutar este script."
            )

    if auth_rotated:
        print()
        print("AVISO: se ha rotado FULKRO_AUTH_PRIVATE_KEY.")
        print("  · Todas las sesiones vivas quedan invalidadas (la cookie fulkro_session")
        print("    firmada con la clave anterior ya no verifica).")
        print("  · Hay que reiniciar backend Y frontend para que ambos carguen el par nuevo.")
        print("  · Los magic links y los intents de firma emitidos antes también caducan")
        print("    (FULKRO_ML_PRIVATE_KEY se regenera igualmente con --force).")

    say()
    say("=== Listo ===")
    say("Backend:  uvicorn backend.app.main:app --port 8000 --env-file " + str(backend_env))
    say("Frontend: cd frontend && npx next dev --port 3000")
    say()
    say("SEGURIDAD: estos ficheros están en .gitignore · nunca se commitean · en")
    say("producción las claves van por Vault/SOPS (ADR-021 v6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
