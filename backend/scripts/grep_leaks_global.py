"""V-CHECK Paso 2 — grep global de leaks client-facing.

Escanea buscando FULKRO, Motor X, Agente X, M\\d+-V\\d+, Document
Factory, Copiloto, v5.1 en:

1. var/templates_docx/*.docx (los 80 templates master)
2. var/documents/**/*.docx (DOCX generados por el motor)
3. var/documents/**/*.pdf (PDFs asociados)
4. var/verification_handoffs/**/*.md (paquetes handoff de pentester)
5. Emails HTML renderizados por los purposes de M12 (renderizado con
   contexto mock para chequear output real).
6. Guias de remediacion generadas por guide_generator (deterministic).

Reporta por cada hallazgo el fichero + la frase que contiene el leak.
Sale con codigo 0 si no hay leaks, 1 si hay al menos uno.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VAR_DIR = ROOT / "var"


LEAK_PATTERNS = [
    r"\bFULKRO\b",
    r"\bMotor\s+\d+\b",
    r"\bAgente\s+\d+\b",
    r"\bM\d+-V\d+\b",
    r"\bM\d+-G\d+\b",
    r"\bDocument\s+Factory\b",
    r"\bCopiloto\b(?!\s+ENS)",
    r"\bv5\.1\b",
]


def _is_commercial_docx(path: Path) -> bool:
    """Comercial/facturacion usan el nombre de empresa FULKRO legitimamente.

    Excluye: templates C-* / P-* (contratos, propuestas) e invoices
    INV_FULKRO-* / FA-* (facturas emitidas por el consultor).
    """
    stem = path.stem
    if stem.startswith(("C-", "P-")):
        return True
    if stem.startswith(("INV_", "FA-", "FA_", "FACTURA_")):
        return True
    return False


def _scan_docx_text(path: Path) -> list[tuple[str, str]]:
    """Extrae texto visible de un DOCX y grepea."""
    try:
        from docx import Document
        d = Document(str(path))
    except Exception as exc:  # pragma: no cover
        return [(f"(cant_open:{exc})", "")]
    pieces: list[str] = []
    for p in d.paragraphs:
        if p.text:
            pieces.append(p.text)
    for tbl in d.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text:
                        pieces.append(p.text)
    for section in d.sections:
        for p in section.header.paragraphs:
            if p.text:
                pieces.append(p.text)
        for p in section.footer.paragraphs:
            if p.text:
                pieces.append(p.text)
    text = "\n".join(pieces)
    hits = []
    for pat in LEAK_PATTERNS:
        for m in re.finditer(pat, text):
            snippet = text[max(0, m.start()-30):m.end()+30].replace("\n", " ")
            hits.append((pat, snippet))
    return hits


def _scan_docx_xml(path: Path) -> list[str]:
    """Grepea en el XML crudo del DOCX (por si hay leaks en metadata)."""
    hits = []
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".xml"):
                    continue
                xml = z.read(name).decode("utf-8", errors="replace")
                for pat in LEAK_PATTERNS:
                    if re.search(pat, xml):
                        hits.append(f"{name}:{pat}")
                        break
    except Exception:  # pragma: no cover
        pass
    return hits


def _scan_pdf(path: Path) -> list[str]:
    """Extrae texto del PDF via pdftotext (si esta disponible)."""
    try:
        out = subprocess.check_output(
            ["pdftotext", "-layout", str(path), "-"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    hits = []
    for pat in LEAK_PATTERNS:
        if re.search(pat, out):
            for m in re.finditer(pat, out):
                snippet = out[max(0, m.start()-25):m.end()+25].replace("\n", " ")
                hits.append(f"{pat}: {snippet}")
    return hits


def _scan_text_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        return []
    hits = []
    for pat in LEAK_PATTERNS:
        for m in re.finditer(pat, text):
            snippet = text[max(0, m.start()-25):m.end()+25].replace("\n", " ")
            hits.append(f"{pat}: {snippet}")
    return hits


def _render_emails() -> list[tuple[str, str]]:
    """Renderiza los purposes de M12 con contexto minimo y graba HTMLs.

    Devuelve lista (path, hits_summary).
    """
    from datetime import datetime, timedelta, timezone
    try:
        from backend.app.motors.m12_magic_link.emails.renderer import (
            render_email_for_magic_link,
        )
        from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
    except Exception as exc:
        print(f"(no se pudieron importar purposes: {exc})")
        return []

    out_dir = VAR_DIR / "vcheck_email_samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    reports: list[tuple[str, str]] = []

    cliente = {
        "razon_social": "DataForma Galicia SL",
        "nombre": "DataForma Galicia SL",
        "nombre_corto": "DataForma",
        "nif": "B72634815",
        "cif": "B72634815",
    }
    proyecto = {
        "nombre": "Adecuacion ENS DataForma",
        "version_actual": "1.0",
        "categoria_ens": "MEDIO",
    }
    destinatario = {
        "nombre": "Maria Perez Nunez",
        "email": "contacto@dataforma.es",
        "cargo": "Consejera Delegada",
    }
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    link_url = "https://portal.ejemplo.es/m/abc123"

    extra_context = {
        "documento": {"codigo": "E-702", "nombre": "Informe Verificacion"},
        "medida": {"codigo": "op.exp.5", "nombre": "Gestion Vulnerabilidades"},
        "acta": {"codigo": "F-008", "fecha": "2026-04-20"},
        "requerimiento": {"titulo": "Requerimiento auditor"},
        "alcance_corto": "app.dataforma.es y srv1.dataforma.es",
        "ventana_inicio": "22:00 del 2026-04-22",
        "obligacion": {"titulo": "Remediacion CVE-2024-6387"},
        "fecha_objetivo": "2026-04-28",
        "accion_remota": "Restart apache2",
        "dossier_titulo": "Dossier ENS DataForma",
        "pentester": {"nombre": "Pentester OSCP",
                      "certificacion": "OSCP", "email": "pentester@ejemplo.es"},
        "informe": {"codigo": "E-702", "severidad_maxima": "critical"},
    }

    for purpose in MagicLinkPurpose:
        try:
            subject, html, text = render_email_for_magic_link(
                purpose=purpose,
                link_url=link_url,
                expires_at=expires,
                cliente=cliente,
                proyecto=proyecto,
                destinatario=destinatario,
                otp="123456",
                **extra_context,
            )
        except Exception as exc:
            reports.append((f"purpose={purpose.value}",
                            f"(render_error:{type(exc).__name__}:{exc})"))
            continue
        path = out_dir / f"{purpose.value}.html"
        path.write_text(html, encoding="utf-8")
        hits = _scan_text_file(path)
        # Filtrar variables CSS internas (FULKRO_NAVY no deberia aparecer
        # porque solo es un nombre de variable Python, no valor renderizado)
        relevant_hits = [h for h in hits if "FULKRO_" not in h]
        if relevant_hits:
            reports.append((str(path.relative_to(ROOT)),
                            " | ".join(relevant_hits[:3])))
    return reports


def _render_guides() -> list[tuple[str, str]]:
    """Genera guias Haiku deterministicas sobre 5 findings sinteticos."""
    try:
        from backend.app.motors.m08_verification.remediation.guide_generator import (
            generate_guide,
        )
    except Exception as exc:
        print(f"(no se pudo importar generate_guide: {exc})")
        return []
    fixtures = [
        {"title": "TLS weak cipher", "severity": "high",
         "affected_host": "app.ejemplo.es", "tool_sources": ["testssl"]},
        {"title": "OpenSSH CVE-2024-6387", "severity": "critical",
         "cve_id": "CVE-2024-6387", "affected_host": "srv.ejemplo.es",
         "tool_sources": ["nuclei"]},
        {"title": "SQL Injection in login", "severity": "high",
         "affected_host": "app.ejemplo.es",
         "affected_url": "https://app.ejemplo.es/login",
         "tool_sources": ["zap"]},
        {"title": "Hardening SSH-7408", "severity": "medium",
         "affected_host": "srv.ejemplo.es",
         "tool_sources": ["lynis"],
         "tool_metadata": {"control_id": "SSH-7408"}},
        {"title": "DMARC policy none", "severity": "medium",
         "affected_host": "ejemplo.es",
         "tool_sources": ["dns_checker"]},
    ]
    reports: list[tuple[str, str]] = []
    for i, f in enumerate(fixtures):
        guide = generate_guide(f, force_offline=True)
        text = json.dumps(guide, ensure_ascii=False)
        hits = []
        for pat in LEAK_PATTERNS:
            for m in re.finditer(pat, text):
                hits.append(f"{pat}: {text[max(0, m.start()-20):m.end()+20]}")
        if hits:
            reports.append((f"guide[{i}:{f['title']}]", " | ".join(hits[:3])))
    return reports


def main() -> int:
    print("=" * 70)
    print("V-CHECK · GREP LEAKS GLOBAL · client-facing content")
    print("=" * 70)

    total_files = 0
    leaked: list[str] = []

    # 1. Templates master (var/templates_docx)
    templates_dir = VAR_DIR / "templates_docx"
    for docx in sorted(templates_dir.glob("*.docx")):
        if _is_commercial_docx(docx):
            continue  # templates comerciales SI llevan FULKRO, legitimo
        total_files += 1
        vis = _scan_docx_text(docx)
        xml = _scan_docx_xml(docx)
        if vis or xml:
            leaked.append(
                f"  [TPL] {docx.name}: {len(vis)} vis, {len(xml)} xml"
            )
            for pat, snippet in vis[:3]:
                leaked.append(f"      vis: {pat} | {snippet!r}")
            for h in xml[:3]:
                leaked.append(f"      xml: {h}")
    print(f"\n[1] Templates master escaneados: {total_files - 0} (exc. C-/P-)")

    # 2. DOCX generados
    gen_docx_count = 0
    for docx in sorted(VAR_DIR.glob("documents/**/*.docx")):
        if _is_commercial_docx(docx):
            continue
        gen_docx_count += 1
        vis = _scan_docx_text(docx)
        xml = _scan_docx_xml(docx)
        if vis or xml:
            leaked.append(
                f"  [GEN] {docx.relative_to(ROOT)}: {len(vis)} vis, {len(xml)} xml"
            )
            for pat, snippet in vis[:3]:
                leaked.append(f"      vis: {pat} | {snippet!r}")
            for h in xml[:3]:
                leaked.append(f"      xml: {h}")
    print(f"[2] DOCX generados escaneados: {gen_docx_count}")

    # 3. PDFs generados
    pdf_count = 0
    pdf_leaks = 0
    for pdf in sorted(VAR_DIR.glob("documents/**/*.pdf")):
        pdf_count += 1
        hits = _scan_pdf(pdf)
        if hits:
            pdf_leaks += 1
            leaked.append(f"  [PDF] {pdf.relative_to(ROOT)}: {len(hits)} hits")
            for h in hits[:3]:
                leaked.append(f"      {h}")
    print(f"[3] PDFs generados escaneados: {pdf_count}")

    # 4. Handoff markdowns
    handoff_count = 0
    for md in sorted(VAR_DIR.glob("verification_handoffs/**/*.md")):
        handoff_count += 1
        hits = _scan_text_file(md)
        if hits:
            leaked.append(
                f"  [HANDOFF] {md.relative_to(ROOT)}: {len(hits)} hits"
            )
            for h in hits[:3]:
                leaked.append(f"      {h}")
    print(f"[4] Handoff MDs escaneados: {handoff_count}")

    # 5. Emails HTML renderizados
    email_reports = _render_emails()
    print(f"[5] Emails M12 renderizados y escaneados: {len(email_reports)} con leaks")
    for path, hits in email_reports:
        leaked.append(f"  [EMAIL] {path}: {hits}")

    # 6. Guias Haiku deterministicas
    guide_reports = _render_guides()
    print(f"[6] Guias Haiku generadas y escaneadas: {len(guide_reports)} con leaks")
    for path, hits in guide_reports:
        leaked.append(f"  [GUIDE] {path}: {hits}")

    print()
    print("=" * 70)
    if leaked:
        print(f"RESULTADO: {len(leaked)} leaks detectados ❌\n")
        for l in leaked[:40]:
            print(l)
        return 1
    print("RESULTADO: 0 leaks ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
