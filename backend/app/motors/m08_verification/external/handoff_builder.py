"""M8 v5.1 - Handoff builder (spec §6.1).

Genera los 7 documentos del engagement entregables al pentester externo:

1. 01_Scope.md               - alcance formal y ROE
2. 02_Inventario.md          - inventario tecnico con versiones
3. 03_Mapa_Red.md            - diagrama logico de la red
4. 04_Vulnerabilidades_previas.md  - findings internos ya detectados
5. 05_Objetivos_criticos.md  - activos prioritarios y datos sensibles
6. 06_Autorizacion.md        - autorizacion firmada por el cliente
7. 07_NDA.md                 - acuerdo de confidencialidad estandar

Todos se renderizan como entregables Markdown (por su caracter tecnico
compacto). Si el caller pasa ``render_as_pdf=True``, cada MD se
convierte a PDF via LibreOffice igual que M6 Document Factory.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client, Project
from backend.app.motors.m08_verification.models import (
    ExternalPentesterHandoff, VerificationFinding, VerificationRun,
)


ROOT = Path(__file__).resolve().parents[5]
HANDOFF_DIR = ROOT / "var" / "verification_handoffs"


HANDOFF_DOCUMENTS = [
    "01_Scope.md",
    "02_Inventario.md",
    "03_Mapa_Red.md",
    "04_Vulnerabilidades_previas.md",
    "05_Objetivos_criticos.md",
    "06_Autorizacion.md",
    "07_NDA.md",
]


# ────────────────────────────────────────────────────────────────────
# Builders por documento
# ────────────────────────────────────────────────────────────────────

def _scope_doc(run: VerificationRun, client: Client, project: Project) -> str:
    scope = run.scope_jsonb or {}
    targets = scope.get("targets") or []
    web_apps = scope.get("web_apps") or []
    exclusions = scope.get("exclusions") or []
    window = scope.get("scan_window") or "L-V 09:00-18:00 CET"
    return f"""# 01 · Alcance y Reglas de Compromiso (ROE)

**Cliente:** {client.nombre} (NIF {client.cif})
**Proyecto:** {project.nombre}
**Categoria ENS:** {run.category}
**Engagement id:** {run.id}

## 1. Objetivos en alcance

{_md_list(targets)}

## 2. Aplicaciones web en alcance

{_md_list(web_apps) if web_apps else "_No hay aplicaciones web._"}

## 3. Exclusiones expresas

{_md_list(exclusions) if exclusions else "_Sin exclusiones._"}

## 4. Reglas de compromiso

- **Denegacion de servicio:** prohibida bajo cualquier modalidad.
- **Ataques destructivos o corrupcion de datos:** prohibidos.
- **Ingenieria social a personal del cliente:** no autorizada salvo fases
  concretas previamente acordadas por escrito con el RSEG.
- **Acceso a datos personales:** sin extraccion ni retencion posterior.
- **Ventana autorizada:** {window}.
- **Canal de coordinacion diaria:** email al consultor + RSEG del cliente.

## 5. Contactos de emergencia

- Consultor: Marcos Mata Garcia (marcos@ejemplo.es)
- RSEG del cliente: {getattr(client, 'contacto_email', '') or '(por definir)'}

## 6. Entregables esperados del pentester

- Informe PDF con los findings agrupados por severidad (CVSS v3.1).
- Fichero estructurado JSON/XLSX con los campos: title, severity, cve_id,
  affected_host, affected_port, affected_service, description,
  remediation.
- Hash SHA-256 del informe PDF entregado.
- Declaracion de no haber introducido backdoors, accesos persistentes ni
  modificaciones en el entorno.
"""


def _inventory_doc(run: VerificationRun, inventory: list[dict]) -> str:
    scope = run.scope_jsonb or {}
    targets = scope.get("targets") or []
    lines = []
    for t in targets:
        lines.append(f"- `{t}`")
    detail = "\n".join(
        f"| `{it.get('host', '?')}` | {it.get('os', '-')} | "
        f"{it.get('services', '-')} | {it.get('version', '-')} |"
        for it in inventory
    ) or "| — | — | — | — |"
    return f"""# 02 · Inventario tecnico

## 2.1 Hosts y servicios

| Host | SO | Servicios | Versiones |
|---|---|---|---|
{detail}

## 2.2 Resumen de objetivos

{chr(10).join(lines) if lines else "(vacio)"}

_Fuente: modulo M22 (Discovery) + M3 (DdA)._
"""


def _network_doc(run: VerificationRun) -> str:
    diagram = (run.scope_jsonb or {}).get("network_diagram") or (
        "graph LR\n    Internet --> FW[Firewall]\n"
        "    FW --> DMZ[DMZ] --> APP[Servidor aplicacion]\n"
        "    FW --> LAN[Red interna]"
    )
    return f"""# 03 · Mapa logico de red

```mermaid
{diagram}
```

## Notas

- El diagrama refleja los segmentos logicos visibles desde el alcance.
- No se documentan rutas de backoffice fuera del alcance.
- Firewall / balanceadores / WAF se indican cuando afectan al test.
"""


def _previous_findings_doc(findings: list[VerificationFinding]) -> str:
    if not findings:
        return "# 04 · Vulnerabilidades ya detectadas\n\n_No hay hallazgos internos previos._\n"
    rows = []
    for f in findings:
        rows.append(
            f"| {f.severity} | {f.title[:80]} | `{f.affected_host}"
            f"{':' + str(f.affected_port) if f.affected_port else ''}` | "
            f"{f.cve_id or '—'} | {f.status} |"
        )
    return f"""# 04 · Vulnerabilidades ya detectadas por la verificacion interna

| Severidad | Titulo | Host | CVE | Estado |
|---|---|---|---|---|
{chr(10).join(rows)}

_El pentester externo debe confirmar si estos findings siguen presentes
y puede complementarlos con hallazgos nuevos._
"""


def _critical_assets_doc(
    run: VerificationRun, client: Client, project: Project,
) -> str:
    scope = run.scope_jsonb or {}
    critical = scope.get("critical_assets") or [
        "Servicio core expuesto al ciudadano",
        "Base de datos principal con datos personales",
        "Directorio activo / LDAP",
    ]
    data_types = scope.get("sensitive_data") or [
        "Datos personales (RGPD)",
        "Datos de salud (categoria especial)"
        if "sanitario" in (getattr(client, "sector", "") or "").lower()
        else "Datos economico-financieros",
    ]
    return f"""# 05 · Objetivos criticos y datos sensibles

## 5.1 Activos prioritarios

{_md_list(critical)}

## 5.2 Datos sensibles manejados por el sistema

{_md_list(data_types)}

## 5.3 Impacto esperado si se comprometen

Una intrusion exitosa sobre los activos listados supondria:

- Afectacion a la categoria ENS declarada ({run.category}).
- Notificacion obligatoria a AEPD / CCN-CERT dentro del plazo legal.
- Perdida reputacional ante los ciudadanos usuarios del servicio.
"""


def _authorization_doc(
    run: VerificationRun, client: Client, project: Project,
) -> str:
    return f"""# 06 · Autorizacion formal de pentest

**Cliente:** {client.nombre} (NIF {client.cif})
**Representante legal:** {getattr(client, 'representante_legal', '(por definir)')}

El abajo firmante, en nombre y representacion de **{client.nombre}**,
AUTORIZA al pentester externo designado la ejecucion de pruebas de
intrusion controladas sobre el sistema definido en el documento 01_Scope,
conforme a las reglas de compromiso alli establecidas.

- La autorizacion tiene vigencia durante la ventana indicada y no
  podra emplearse fuera de dicha ventana.
- La autorizacion no cubre accesos a sistemas fuera del alcance
  declarado.
- El cliente se reserva el derecho a interrumpir el ejercicio en
  cualquier momento si detecta impacto operativo.

**Firma digital (magic link):** ({run.authorization_signed_at or 'pendiente'})
**Hash del documento firmado:** (_se completa al firmar_)

Identificador interno: {run.id}
"""


def _nda_doc(client: Client) -> str:
    return f"""# 07 · Acuerdo de confidencialidad (NDA)

Entre **{client.nombre}** y el pentester externo designado se formaliza
el presente acuerdo de confidencialidad con las siguientes clausulas:

1. **Objeto.** Toda la informacion tecnica, organizativa, comercial o
   personal a la que el pentester acceda durante el engagement queda
   sujeta a secreto profesional.
2. **Vigencia.** La obligacion de confidencialidad se extiende por cinco
   (5) anos desde la finalizacion del engagement.
3. **No retencion.** El pentester no podra retener copias de datos,
   configuraciones ni artefactos recolectados mas alla de lo
   estrictamente necesario para la emision del informe.
4. **Destruccion.** Entregado el informe y aceptada su integracion,
   el pentester destruira todos los materiales de trabajo en un plazo
   maximo de 30 dias, emitiendo certificado de destruccion.
5. **No divulgacion.** El pentester no podra divulgar, total o
   parcialmente, los hallazgos a terceros sin consentimiento escrito
   del cliente.
6. **Legislacion aplicable.** Ley espanola. Fuero: juzgados y
   tribunales de la capital del cliente.

Firma del pentester: (adjuntar DNI + firma manuscrita o certificado)
Firma del representante legal del cliente: (adjuntar certificado)
"""


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- {it}" for it in items) or "_(vacio)_"


# ────────────────────────────────────────────────────────────────────
# API publica
# ────────────────────────────────────────────────────────────────────

async def build_handoff_package(
    db: AsyncSession,
    run_id: uuid.UUID,
    *,
    inventory: list[dict] | None = None,
) -> ExternalPentesterHandoff:
    """Construye el paquete de 7 documentos + crea el registro handoff.

    Persiste un ``ExternalPentesterHandoff`` con ``package_documents``
    rellenado (lista de paths + hashes) y devuelve el objeto. El caller
    decide si emite tambien el magic link del portal.
    """
    run = await db.get(VerificationRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} no existe")
    project = await db.get(Project, run.project_id)
    client = await db.get(Client, project.client_id) if project else None

    # Findings previos para incluir en 04_Vulnerabilidades_previas
    from sqlalchemy import select
    prev_stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == run.project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.status.in_(("open", "needs_review")),
    )
    prev = (await db.execute(prev_stmt)).scalars().all()

    out_dir = HANDOFF_DIR / str(run.project_id) / str(run.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "01_Scope.md": lambda: _scope_doc(run, client, project),
        "02_Inventario.md": lambda: _inventory_doc(run, inventory or []),
        "03_Mapa_Red.md": lambda: _network_doc(run),
        "04_Vulnerabilidades_previas.md": lambda: _previous_findings_doc(list(prev)),
        "05_Objetivos_criticos.md": lambda: _critical_assets_doc(run, client, project),
        "06_Autorizacion.md": lambda: _authorization_doc(run, client, project),
        "07_NDA.md": lambda: _nda_doc(client),
    }

    package: list[dict] = []
    generated_at = datetime.now(timezone.utc).isoformat()
    for name in HANDOFF_DOCUMENTS:
        content = builders[name]()
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        package.append({
            "name": name.replace(".md", ""),
            "path": str(path.relative_to(ROOT)),
            "generated_at": generated_at,
            "hash_sha256": digest,
        })

    handoff = ExternalPentesterHandoff(
        project_id=run.project_id,
        run_id=run.id,
        package_documents=package,
        status="draft",
    )
    db.add(handoff)
    await db.flush()
    return handoff
