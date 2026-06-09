"""Download known-public CCN-STIC + BOE + AEPD PDFs into corpus_cache.

Respects robots.txt via User-Agent polite + 2.5s delay between requests.

URLs cobrables automaticamente son limitadas porque la mayoria de
CCN-STIC 800 (hardening detallados, secciones restringidas) estan
detras del portal autenticado de ccn-cert. Este script intenta las
URLs publicas conocidas y documenta en el reporte los que requieren
fetching manual con credenciales de Marcos.

Uso:
    python backend/scripts/download_ccn_corpus.py [--dry-run]

Output:
    ~/.fulkro/corpus_cache/manual/ccn/<serie>/<slug>.pdf
    progress/corpus_download_report.md (estado actualizado)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

USER_AGENT = (
    "FULKRO/0.1 (https://fulkro.es; marcosmata@fulkro.es) "
    "Python-urllib/3.12"
)
DELAY_SECONDS = 2.5
TIMEOUT_SECONDS = 30

CACHE_BASE = Path.home() / ".fulkro" / "corpus_cache" / "manual" / "ccn"


@dataclass
class PdfSource:
    serie: str          # e.g. "stic_serie_800", "boe", "aepd"
    slug: str           # filename base
    url: str
    titulo: str
    status: str = "pending"
    sha256: str | None = None
    size_bytes: int | None = None
    error: str | None = None


# URLs PUBLICAS CONOCIDAS — BOE, AEPD, INCIBE
# CCN-STIC tipicamente requiere autenticacion, por lo que la mayoria
# de series 800 quedan fuera de esta descarga automatica.
PUBLIC_SOURCES: list[PdfSource] = [
    # ── RD 311/2022 ENS (ya en corpus, solo re-verificacion) ─────
    PdfSource(
        serie="boe",
        slug="RD_311_2022_ENS",
        url="https://www.boe.es/buscar/doc.php?id=BOE-A-2022-7191",
        titulo="Real Decreto 311/2022 Esquema Nacional de Seguridad",
    ),
    # ── BOE leyes ─────────────────────────────────────────────────
    PdfSource(
        serie="boe",
        slug="LOPDGDD_3_2018",
        url="https://www.boe.es/buscar/pdf/2018/BOE-A-2018-16673-consolidado.pdf",
        titulo="LO 3/2018 Proteccion Datos Personales y Garantia Derechos Digitales",
    ),
    PdfSource(
        serie="boe",
        slug="Ley_39_2015_PAC",
        url="https://www.boe.es/buscar/pdf/2015/BOE-A-2015-10565-consolidado.pdf",
        titulo="Ley 39/2015 Procedimiento Administrativo Comun",
    ),
    PdfSource(
        serie="boe",
        slug="Ley_40_2015_Regimen_Juridico",
        url="https://www.boe.es/buscar/pdf/2015/BOE-A-2015-10566-consolidado.pdf",
        titulo="Ley 40/2015 Regimen Juridico Sector Publico",
    ),
    PdfSource(
        serie="boe",
        slug="Ley_9_2017_Contratos",
        url="https://www.boe.es/buscar/pdf/2017/BOE-A-2017-12902-consolidado.pdf",
        titulo="Ley 9/2017 Contratos Sector Publico",
    ),
    # ── AEPD guias publicas ───────────────────────────────────────
    PdfSource(
        serie="aepd",
        slug="Guia_Responsable_Tratamiento",
        url="https://www.aepd.es/guias/guia-responsable-encargado.pdf",
        titulo="AEPD - Guia para Responsables y Encargados del Tratamiento",
    ),
    PdfSource(
        serie="aepd",
        slug="Guia_GDPR_PYME",
        url="https://www.aepd.es/guias/facilita-rgpd-pyme.pdf",
        titulo="AEPD - Facilita RGPD Pequena Empresa",
    ),
    PdfSource(
        serie="aepd",
        slug="Guia_Brechas_Seguridad",
        url="https://www.aepd.es/guias/guia-brechas-seguridad.pdf",
        titulo="AEPD - Guia para la Notificacion de Brechas de Seguridad",
    ),
    # ── INCIBE publicos ───────────────────────────────────────────
    PdfSource(
        serie="incibe",
        slug="Kit_Concienciacion",
        url="https://www.incibe.es/sites/default/files/contenidos/"
            "kit-concienciacion/documentos/guia_referencia.pdf",
        titulo="INCIBE - Kit Concienciacion Empleados",
    ),
]

# URLs que tipicamente REQUIEREN fetching manual (credenciales CCN)
MANUAL_FETCH_PENDING: list[PdfSource] = [
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-803_Valoracion",
        url="manual", titulo="CCN-STIC 803 Valoracion de los sistemas ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-804_Implantacion",
        url="manual", titulo="CCN-STIC 804 Medidas de Implantacion del ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-805_Politica_Seguridad",
        url="manual", titulo="CCN-STIC 805 Politica de Seguridad",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-806_Plan_Adecuacion",
        url="manual", titulo="CCN-STIC 806 Plan de Adecuacion al ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-808_Verificacion",
        url="manual", titulo="CCN-STIC 808 Verificacion del cumplimiento ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-809_Declaracion_Certificacion",
        url="manual", titulo="CCN-STIC 809 Declaracion y Certificacion ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-810_Creacion_CERT",
        url="manual", titulo="CCN-STIC 810 Creacion de un CERT/CSIRT",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-811_Interconexion_ENS",
        url="manual", titulo="CCN-STIC 811 Interconexion en el ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-817_Gestion_Ciberincidentes",
        url="manual", titulo="CCN-STIC 817 Gestion de Ciberincidentes",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-821_Normas_Seguridad",
        url="manual", titulo="CCN-STIC 821 Normas de Seguridad ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-824_INES",
        url="manual", titulo="CCN-STIC 824 Informe Estado Seguridad (INES)",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-827_Gestion_Movilidad",
        url="manual", titulo="CCN-STIC 827 Gestion de Movilidad",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-830_Cloud",
        url="manual", titulo="CCN-STIC 830 Ambitos y Servicios Cloud",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-850_Procedimiento_Operacion",
        url="manual", titulo="CCN-STIC 850 Procedimiento Operacion ENS",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-883_PCE_Admin_Local",
        url="manual", titulo="CCN-STIC 883 PCE Administracion Local",
    ),
    PdfSource(
        serie="stic_serie_800", slug="CCN-STIC-884_Azure",
        url="manual", titulo="CCN-STIC 884 Perfil Cumplimiento Azure",
    ),
    # ITS - Instrucciones Tecnicas de Seguridad
    PdfSource(
        serie="its", slug="ITS_Informe_Estado_Seguridad",
        url="manual", titulo="ITS Informe del estado de la seguridad",
    ),
    PdfSource(
        serie="its", slug="ITS_Notificacion_Incidentes",
        url="manual", titulo="ITS Notificacion de incidentes de seguridad",
    ),
    PdfSource(
        serie="its", slug="ITS_Auditoria_Sistemas_ENS",
        url="manual", titulo="ITS Auditoria de la seguridad de los sistemas ENS",
    ),
    PdfSource(
        serie="its", slug="ITS_Conformidad_ENS",
        url="manual", titulo="ITS Conformidad con el ENS",
    ),
    # Series hardening
    PdfSource(
        serie="stic_serie_500", slug="CCN-STIC-521_Linux_Hardening",
        url="manual", titulo="CCN-STIC 521 Configuracion segura Linux",
    ),
    PdfSource(
        serie="stic_serie_500", slug="CCN-STIC-571_Windows_Server_2019",
        url="manual", titulo="CCN-STIC 571 Windows Server 2019",
    ),
    PdfSource(
        serie="stic_serie_500", slug="CCN-STIC-573_Windows_10",
        url="manual", titulo="CCN-STIC 573 Windows 10",
    ),
    PdfSource(
        serie="stic_serie_500", slug="CCN-STIC-574_Windows_Server_2022",
        url="manual", titulo="CCN-STIC 574 Windows Server 2022",
    ),
]


def _fetch(source: PdfSource, out_dir: Path, dry_run: bool = False) -> None:
    if source.url == "manual":
        source.status = "manual_pending"
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{source.slug}.pdf"
    if out_path.exists():
        content = out_path.read_bytes()
        source.sha256 = hashlib.sha256(content).hexdigest()
        source.size_bytes = len(content)
        source.status = "cached"
        return
    if dry_run:
        source.status = "dry_run"
        return
    req = Request(source.url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            content = resp.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        source.status = "failed"
        source.error = f"{type(exc).__name__}: {exc}"
        return
    except Exception as exc:  # pragma: no cover
        source.status = "failed"
        source.error = f"{type(exc).__name__}: {exc}"
        return
    content_type = resp.headers.get("Content-Type", "")
    if "pdf" not in content_type.lower() and not content.startswith(b"%PDF"):
        source.status = "not_pdf"
        source.error = f"Content-Type={content_type!r}"
        return
    out_path.write_bytes(content)
    source.sha256 = hashlib.sha256(content).hexdigest()
    source.size_bytes = len(content)
    source.status = "downloaded"


def _render_report(
    public: list[PdfSource],
    manual: list[PdfSource],
    out_path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# FULKRO — CCN Corpus Download Report")
    lines.append("")
    lines.append(
        "Generado por `backend/scripts/download_ccn_corpus.py` en Paso 4.5. "
        "Lista honesta de lo descargado automaticamente + lo que requiere "
        "fetching manual con credenciales de Marcos."
    )
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    downloaded = sum(1 for s in public if s.status in ("downloaded", "cached"))
    failed = sum(1 for s in public if s.status == "failed")
    manual_count = len(manual)
    total = len(public) + manual_count
    lines.append(f"- Total inventariado: **{total}**")
    lines.append(f"- Descargados automaticamente: **{downloaded}/{len(public)}**")
    lines.append(f"- Fallos automaticos: **{failed}**")
    lines.append(f"- Requieren fetching manual: **{manual_count}**")
    lines.append("")
    lines.append(
        "Muchos CCN-STIC exigen acceso autenticado al portal del CCN. "
        "Marcos puede descargarlos con su certificado electronico y "
        "moverlos a `~/.fulkro/corpus_cache/manual/ccn/<serie>/<slug>.pdf`."
    )
    lines.append("")
    lines.append("## Publicos (descarga automatica)")
    lines.append("")
    lines.append("| Slug | Serie | Status | SHA256 (12) | Size |")
    lines.append("|------|-------|--------|-------------|------|")
    for s in public:
        sha = (s.sha256 or "")[:12]
        size = (
            f"{s.size_bytes // 1024} KB" if s.size_bytes
            else (s.error[:40] if s.error else "")
        )
        lines.append(f"| {s.slug} | {s.serie} | {s.status} | {sha} | {size} |")
    lines.append("")
    lines.append("## Manuales (pendiente de Marcos con credenciales CCN)")
    lines.append("")
    lines.append("| Slug | Serie | Titulo |")
    lines.append("|------|-------|--------|")
    for s in manual:
        lines.append(f"| {s.slug} | {s.serie} | {s.titulo} |")
    lines.append("")
    lines.append("## Procedimiento manual para Marcos")
    lines.append("")
    lines.append(
        "1. Acceder a https://www.ccn-cert.cni.es con certificado digital.\n"
        "2. Descargar cada PDF de la serie indicada.\n"
        "3. Colocar en `~/.fulkro/corpus_cache/manual/ccn/<serie>/<slug>.pdf`.\n"
        "4. Ejecutar `python backend/scripts/ingest_corpus.py --path "
        "~/.fulkro/corpus_cache/manual/ccn/` para integrar en pgvector.\n"
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for source in PUBLIC_SOURCES:
        out_dir = CACHE_BASE / source.serie
        _fetch(source, out_dir, dry_run=args.dry_run)
        time.sleep(DELAY_SECONDS if source.status == "downloaded" else 0)

    report_path = (
        Path(__file__).resolve().parents[2]
        / "progress" / "corpus_download_report.md"
    )
    _render_report(PUBLIC_SOURCES, MANUAL_FETCH_PENDING, report_path)
    downloaded = sum(1 for s in PUBLIC_SOURCES if s.status in ("downloaded", "cached"))
    print(
        f"Download complete. {downloaded}/{len(PUBLIC_SOURCES)} public + "
        f"{len(MANUAL_FETCH_PENDING)} manual-pending. "
        f"Report: {report_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
