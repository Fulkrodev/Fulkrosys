#!/usr/bin/env python
"""E-2 · Generador de 'hechos vivos' de plataforma para los copilotos.

Deriva DETERMINÍSTICAMENTE desde las fuentes canónicas del código (nav real de
los portales + WorkflowPhase + AGENT_REGISTRY + fulkro_identity) un módulo
``backend/app/agents/system_knowledge_generated.py`` que se ANEXA al
conocimiento curado de ``system_knowledge.py``.

Así el conocimiento del copiloto se AUTO-ACTUALIZA cuando cambia el sistema:
añades una sección al portal, una fase o un agente → regeneras → el copiloto lo
conoce. El test ``test_system_knowledge_coherence.py`` falla en CI si este
módulo no está al día (gate anti-drift).

Uso:
  python backend/scripts/generate_system_knowledge.py            # escribe
  python backend/scripts/generate_system_knowledge.py --check     # CI: falla si difiere
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# repo root = .../fulkro-portales (este fichero: backend/scripts/...)
ROOT = Path(__file__).resolve().parents[2]
CLIENT_SIDEBAR = ROOT / "frontend/components/layout/ClientSidebar.tsx"
ADMIN_SIDEBAR = ROOT / "frontend/components/layout/Sidebar.tsx"
PROJECT_TABS = ROOT / "frontend/components/project/ProjectTabs.tsx"
ADMIN_PAGES_DIR = ROOT / "frontend/app/(admin)/admin"
OUT = ROOT / "backend/app/agents/system_knowledge_generated.py"

PLATFORM_TAG = "[Fulkro Plataforma]"


def _parse_nav_labels(
    path: Path, href_prefix: str | None = None
) -> list[tuple[str, str]]:
    """Extrae (label, href) de un sidebar TSX con hrefs literales.

    Ignora líneas comentadas (//) y secciones ``label: null``. Empareja
    ``label`` con el ``href`` siguiente; un nuevo ``label`` sobreescribe el
    pendiente (los headers de sección quedan descartados sin href).
    """
    out: list[tuple[str, str]] = []
    last_label: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("//"):
            continue
        m_label = re.search(r'label:\s*"([^"]+)"', line)
        m_href = re.search(r'href:\s*"([^"]+)"', line)
        if m_label and m_href:
            href = m_href.group(1)
            if href_prefix is None or href.startswith(href_prefix):
                out.append((m_label.group(1), href))
            last_label = None
            continue
        if m_label:
            last_label = m_label.group(1)
        elif m_href and last_label is not None:
            href = m_href.group(1)
            if href_prefix is None or href.startswith(href_prefix):
                out.append((last_label, href))
            last_label = None
    return out


def _admin_nav_labels(path: Path) -> list[str]:
    """Labels de ``TOP_NAV`` admin (href = ROUTES.x, no literal). Ignora
    comentados y para al cerrar el array."""
    out: list[str] = []
    in_topnav = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if "TOP_NAV" in line and "=" in line:
            in_topnav = True
            continue
        if in_topnav and line.startswith("]"):
            break
        if not in_topnav or line.startswith("//"):
            continue
        m = re.search(r'label:\s*"([^"]+)"', line)
        if m:
            out.append(m.group(1))
    return out


def _parse_project_tabs(path: Path) -> list[tuple[str, str]]:
    """(label, href-relativo) de MAIN_TABS + SUB_TABS de ProjectTabs.tsx.

    Estos son los tabs project-scoped (dentro de /admin/projects/[id]/...). Las
    entradas son single-line ``{ href: "/x", label: "Y", icon: ... }``. Ignora
    comentadas y PROFILE_TABS (atajos con query-param a páginas existentes).
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for block_name in ("MAIN_TABS", "SUB_TABS"):
        m = re.search(rf"const {block_name}[^=]*=\s*\[(.*?)\];", text, re.S)
        if not m:
            continue
        for line in m.group(1).splitlines():
            s = line.strip()
            if s.startswith("//"):
                continue
            mh = re.search(r'href:\s*"([^"]+)"', s)
            ml = re.search(r'label:\s*"([^"]+)"', s)
            if mh and ml and mh.group(1) not in seen:
                seen.add(mh.group(1))
                out.append((ml.group(1), mh.group(1)))
    return out


def _enumerate_admin_routes(pages_dir: Path) -> list[str]:
    """Todas las rutas admin del filesystem (page.tsx), incl. el SELECTOR de
    proyectos (/admin/projects) y el portal de COMPLIANCE (/admin/compliance/*).

    Excluye SOLO el árbol project-scoped /admin/projects/[id]/* (cubierto por
    _parse_project_tabs con etiquetas friendly). Quita los route-groups (x).
    Determinista (ordenado) → drift-gated por el test de coherencia.
    """
    if not pages_dir.exists():
        return []
    routes: set[str] = set()
    for page in pages_dir.rglob("page.tsx"):
        rel = page.parent.relative_to(pages_dir).as_posix()
        parts = [] if rel in ("", ".") else [
            p for p in rel.split("/") if not (p.startswith("(") and p.endswith(")"))
        ]
        # Excluye el workspace project-scoped (lo cubren las pestañas de proyecto).
        if len(parts) >= 2 and parts[0] == "projects" and parts[1] == "[id]":
            continue
        routes.add("/admin" + ("/" + "/".join(parts) if parts else ""))
    return sorted(routes)


def build_cliente_facts() -> str:
    from backend.app.core.workflow_phase import WorkflowPhase

    nav = _parse_nav_labels(CLIENT_SIDEBAR, href_prefix="/client-portal")
    phases = [p.value for p in WorkflowPhase.ordered()]
    nav_lines = "\n".join(f"- {label} ({href})" for label, href in nav)
    return (
        f"\nMENÚ REAL DEL PORTAL CLIENTE (auto-generado del código · {PLATFORM_TAG}):\n"
        f"{nav_lines}\n\n"
        f"FASES DEL PROYECTO (orden real): {', '.join(phases)}.\n"
    )


def build_admin_facts() -> str:
    from backend.app import fulkro_identity as fi
    from backend.app.agents.registry import AGENT_REGISTRY
    from backend.app.core.workflow_phase import WorkflowPhase

    nav = _admin_nav_labels(ADMIN_SIDEBAR)
    phases = [p.value for p in WorkflowPhase.ordered()]
    active = [
        (aid, meta.get("name", ""), meta.get("motor", ""))
        for aid, meta in sorted(AGENT_REGISTRY.items())
        if isinstance(meta, dict) and meta.get("status") == "activo"
    ]
    agent_lines = "\n".join(
        f"- A{aid} {name}" + (f" (motor {motor})" if motor else "")
        for aid, name, motor in active
    )
    # Pestañas project-scoped (dentro de /admin/projects/[id]/...) con label real.
    tabs = _parse_project_tabs(PROJECT_TABS)
    tab_lines = "\n".join(
        f"- {label} (/admin/projects/[id]{href})" for label, href in tabs
    )
    # Mapa COMPLETO de rutas admin del filesystem (selector de proyectos +
    # portal compliance + todas las top-level y sub-páginas).
    routes = _enumerate_admin_routes(ADMIN_PAGES_DIR)
    routes_lines = "\n".join(f"- {r}" for r in routes)
    return (
        "\nMENÚ GLOBAL DEL PANEL ADMIN (barra lateral · auto-generado del código):\n"
        f"{', '.join(nav)}.\n\n"
        "MENÚ DEL PROYECTO (project-scoped · pestañas dentro de "
        f"/admin/projects/[id]/... · {len(tabs)} pestañas):\n{tab_lines}\n\n"
        "MAPA COMPLETO DE PÁGINAS DEL PANEL ADMIN (todas las rutas reales · "
        "incluye el selector /admin/projects y el portal /admin/compliance · "
        f"{len(routes)} rutas):\n{routes_lines}\n\n"
        f"FASES DEL CICLO (orden real): {', '.join(phases)}.\n\n"
        f"AGENTES LLM ACTIVOS ({len(active)}):\n{agent_lines}\n\n"
        f"CONTACTO FULKRO: {fi.FULKRO_PHONE} · {fi.FULKRO_WEB} · {fi.FULKRO_EMAIL}.\n"
    )


def render_module() -> str:
    cli = build_cliente_facts()
    adm = build_admin_facts()
    return (
        '"""AUTO-GENERATED — DO NOT EDIT.\n\n'
        "Generado por backend/scripts/generate_system_knowledge.py desde las\n"
        "fuentes canónicas (nav portales + WorkflowPhase + AGENT_REGISTRY +\n"
        "fulkro_identity). Para actualizar: python backend/scripts/generate_system_knowledge.py.\n"
        "El test test_system_knowledge_coherence.py falla si no está al día.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        f"LIVE_PLATFORM_FACTS_CLIENTE = {cli!r}\n\n"
        f"LIVE_PLATFORM_FACTS_ADMIN = {adm!r}\n"
    )


def main(argv: list[str]) -> int:
    content = render_module()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current.strip() != content.strip():
            print(
                "DRIFT: system_knowledge_generated.py desactualizado. "
                "Ejecuta: python backend/scripts/generate_system_knowledge.py"
            )
            return 1
        print("system_knowledge_generated.py al día.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"escrito {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
