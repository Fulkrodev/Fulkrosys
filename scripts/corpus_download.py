#!/usr/bin/env python3
"""
FULKRO Fase A — Automated corpus download for public sources.

Downloads ~50-60 publicly accessible sources from the Appendix H corpus.
Sources behind authentication (CCN-STIC, etc.) are listed for manual download.

Usage:
    python scripts/corpus_download.py              # download all auto sources
    python scripts/corpus_download.py --dry-run    # list what would be downloaded

Output:
    ~/.fulkro/corpus_cache/auto/         # downloaded files
    ~/.fulkro/corpus_cache/manifest.json # inventory with hashes
    ~/.fulkro/corpus_cache/failed.json   # failures with reasons
"""
import hashlib
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

# === CONFIG ===
CACHE_ROOT = Path.home() / ".fulkro" / "corpus_cache"
AUTO_DIR = CACHE_ROOT / "auto"
MANUAL_DIR = CACHE_ROOT / "manual"
MANIFEST_PATH = CACHE_ROOT / "manifest.json"
FAILED_PATH = CACHE_ROOT / "failed.json"
LOG_PATH = CACHE_ROOT / "ingest.log"

USER_AGENT = "FULKRO/0.1 (consultoria ENS; contacto@fulkro.es)"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_RETRIES = 2


@dataclass
class Source:
    doc_id: str
    title: str
    url: str
    category: str
    subdir: str
    filename: str
    priority: str  # P0, P1, P2
    auto: bool  # True = download automatically
    notes: str = ""


# === AUTO-DOWNLOADABLE SOURCES ===
# These are on public websites that don't block bots

AUTO_SOURCES = [
    # --- BOE (legislación primaria) ---
    Source("BOE-A-2022-7191", "RD 311/2022 Esquema Nacional de Seguridad",
           "https://www.boe.es/boe/dias/2022/05/04/pdfs/BOE-A-2022-7191.pdf",
           "boe", "boe", "rd_311_2022.pdf", "P0", True),
    Source("BOE-A-2018-16673", "LOPDGDD Ley Orgánica 3/2018",
           "https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673&p=20181206&tn=1",
           "boe", "boe", "lopdgdd.html", "P0", True, "HTML consolidado"),
    Source("BOE-ITS-CONFORMIDAD", "ITS Conformidad con el ENS",
           "http://www.boe.es/diario_boe/txt.php?id=BOE-A-2016-10109",
           "boe", "boe", "its_conformidad.html", "P0", True),
    Source("BOE-ITS-ESTADO", "ITS Informe del Estado de la Seguridad",
           "http://www.boe.es/diario_boe/txt.php?id=BOE-A-2016-10108",
           "boe", "boe", "its_estado_seguridad.html", "P0", True),
    Source("BOE-ITS-AUDITORIA", "ITS Auditoría de la Seguridad",
           "http://www.boe.es/diario_boe/txt.php?id=BOE-A-2018-4573",
           "boe", "boe", "its_auditoria.html", "P0", True),
    Source("BOE-ITS-INCIDENTES", "ITS Notificación de Incidentes",
           "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2018-5370",
           "boe", "boe", "its_incidentes.html", "P0", True),
    Source("BOE-LEY-39-2015", "Ley 39/2015 Procedimiento Administrativo",
           "https://www.boe.es/buscar/act.php?id=BOE-A-2015-10565&p=20151002&tn=1",
           "boe", "boe", "ley_39_2015.html", "P1", True),
    Source("BOE-LEY-40-2015", "Ley 40/2015 Régimen Jurídico Sector Público",
           "https://www.boe.es/buscar/act.php?id=BOE-A-2015-10566&p=20151002&tn=1",
           "boe", "boe", "ley_40_2015.html", "P1", True),

    # --- EUR-Lex (normativa UE) ---
    Source("RGPD", "Reglamento (UE) 2016/679 RGPD",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32016R0679",
           "eu", "eur_lex", "rgpd_2016_679.html", "P0", True),
    Source("NIS2", "Directiva (UE) 2022/2555 NIS2",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32022L2555",
           "eu", "eur_lex", "nis2_2022_2555.html", "P0", True),
    Source("DORA", "Reglamento (UE) 2022/2554 DORA",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32022R2554",
           "eu", "eur_lex", "dora_2022_2554.html", "P0", True),
    Source("eIDAS", "Reglamento (UE) 910/2014 eIDAS",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32014R0910",
           "eu", "eur_lex", "eidas_910_2014.html", "P0", True),
    Source("AI-ACT", "Reglamento (UE) 2024/1689 AI Act",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1689",
           "eu", "eur_lex", "ai_act_2024_1689.html", "P1", True),
    Source("CRA", "Reglamento (UE) 2024/2847 Cyber Resilience Act",
           "https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R2847",
           "eu", "eur_lex", "cra_2024_2847.html", "P1", True),

    # --- MAGERIT v3 ---
    Source("MAGERIT-I", "MAGERIT v3 Libro I - Método",
           "https://administracionelectronica.gob.es/pae_Home/dam/jcr:80b16a91-75b1-432d-ab23-844a12aab5fc/MAGERIT_v_3_book_1_method_PDF_NIPO_630-14-162-0.pdf",
           "magerit", "magerit", "magerit_v3_libro1_metodo.pdf", "P0", True),
    Source("MAGERIT-II", "MAGERIT v3 Libro II - Catálogo de Elementos",
           "https://administracionelectronica.gob.es/pae_Home/dam/jcr:5fbe15c3-c797-46a6-acd8-51311f4c2d29/2012_Magerit_v3_libro2_catalogo-de-elementos_es_NIPO_630-12-171-8.pdf",
           "magerit", "magerit", "magerit_v3_libro2_catalogo.pdf", "P0", True),

    # --- AEPD ---
    Source("AEPD-BRECHAS", "Guía notificación de brechas de datos personales",
           "https://www.aepd.es/guias/guia-brechas-seguridad.pdf",
           "aepd", "aepd", "guia_brechas_seguridad.pdf", "P0", True),
    Source("AEPD-RIESGOS", "Guía gestión de riesgos y EIPD",
           "https://www.aepd.es/guias/gestion-riesgo-y-evaluacion-impacto-en-tratamientos-datos-personales.pdf",
           "aepd", "aepd", "guia_riesgos_eipd.pdf", "P1", True),
    Source("AEPD-EIPD", "Guía evaluaciones de impacto RGPD",
           "https://www.aepd.es/guias/guia-evaluaciones-de-impacto-rgpd-aepd.pdf",
           "aepd", "aepd", "guia_eipd.pdf", "P1", True),
    Source("EDPB-BRECHAS", "Directrices EDPB 01/2021 notificación brechas",
           "https://edpb.europa.eu/system/files/2022-09/edpb_guidelines_012021_pdbnotification_adopted_es.pdf",
           "aepd", "aepd", "edpb_directrices_brechas_es.pdf", "P1", True),

    # --- OWASP ---
    Source("OWASP-TOP10", "OWASP Top 10 2021",
           "https://owasp.org/www-project-top-ten/",
           "owasp", "owasp", "owasp_top10_2021.html", "P1", True),
    Source("OWASP-API", "OWASP API Security Top 10 2023",
           "https://owasp.org/API-Security/editions/2023/en/0x11-t10/",
           "owasp", "owasp", "owasp_api_top10_2023.html", "P1", True),

    # --- MITRE ---
    Source("MITRE-ATTACK", "MITRE ATT&CK Enterprise Matrix",
           "https://attack.mitre.org/matrices/enterprise/",
           "mitre", "mitre", "mitre_attack_enterprise.html", "P1", True),

    # --- NIST ---
    Source("NIST-CSF", "NIST Cybersecurity Framework 2.0",
           "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
           "nist", "nist", "nist_csf_2.0.pdf", "P1", True),
    Source("NIST-800-53", "NIST SP 800-53 Rev 5",
           "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf",
           "nist", "nist", "nist_sp_800_53r5.pdf", "P1", True),

    # --- ISO 27001 (from our own deliverables) ---
    Source("ISO27001-ES-P1", "ISO 27001:2022 Traducción (Parte 1)",
           "local://docs/spec/ISO27001_ES_PARTE1 (1).md",
           "iso_27001", "iso_27001", "iso27001_es_parte1.md", "P0", True,
           "From our own deliverables, not a download"),
    Source("ISO27001-ES-P2", "ISO 27001:2022 Mapping ENS (Parte 2)",
           "local://docs/spec/ISO27001_ES_PARTE2_MAPPING (1).md",
           "iso_27001", "iso_27001", "iso27001_es_parte2_mapping.md", "P0", True,
           "From our own deliverables, not a download"),

    # --- ENS Portal pages (HTML scrape) ---
    Source("ENS-FAQ", "FAQ oficial del ENS",
           "https://ens.ccn.cni.es/es/que-es-el-ens/faq",
           "ccn_portal", "ccn_portal", "ens_faq.html", "P0", True,
           "Public portal page"),
    Source("ENS-ADECUACION", "Proceso de adecuación ENS",
           "https://ens.ccn.cni.es/es/conformidad/proceso-de-adecuacion",
           "ccn_portal", "ccn_portal", "ens_proceso_adecuacion.html", "P0", True),
    Source("ENS-CONFORMIDAD", "Distintivos de conformidad ENS",
           "https://ens.ccn.cni.es/es/conformidad/distintivos",
           "ccn_portal", "ccn_portal", "ens_distintivos.html", "P0", True),
    Source("ENS-CERTIFICADORAS", "Entidades de certificación ENAC",
           "https://ens.ccn.cni.es/es/certificacion/entidades-de-certificacion",
           "ccn_portal", "ccn_portal", "ens_certificadoras.html", "P0", True),
]


def log(msg: str):
    """Log to both console and file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_source(client: httpx.Client, src: Source, dry_run: bool = False) -> dict:
    """Download a single source. Returns metadata dict."""
    dest_dir = AUTO_DIR / src.subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / src.filename

    result = {
        "doc_id": src.doc_id,
        "title": src.title,
        "url": src.url,
        "category": src.category,
        "priority": src.priority,
        "filename": str(dest_file.relative_to(CACHE_ROOT)),
    }

    if dry_run:
        result["status"] = "dry_run"
        log(f"[DRY RUN] Would download: {src.doc_id} -> {src.filename}")
        return result

    # Handle local files (from our own deliverables)
    if src.url.startswith("local://"):
        local_path = Path.home() / "fulkro" / src.url.replace("local://", "")
        if local_path.exists():
            import shutil
            shutil.copy2(local_path, dest_file)
            result["status"] = "fetched"
            result["size_bytes"] = dest_file.stat().st_size
            result["sha256"] = sha256_file(dest_file)
            result["content_type"] = "text/markdown"
            result["downloaded_at"] = datetime.now(timezone.utc).isoformat()
            log(f"[OK] {src.doc_id}: copied local {local_path.name} ({result['size_bytes']} bytes)")
            return result
        else:
            result["status"] = "failed"
            result["error"] = f"Local file not found: {local_path}"
            log(f"[FAIL] {src.doc_id}: {result['error']}")
            return result

    # HTTP download with retries
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"[{attempt}/{MAX_RETRIES}] Downloading {src.doc_id}: {src.url[:80]}...")
            resp = client.get(src.url, follow_redirects=True)
            result["http_status"] = resp.status_code

            if resp.status_code == 200:
                dest_file.write_bytes(resp.content)
                result["status"] = "fetched"
                result["size_bytes"] = len(resp.content)
                result["sha256"] = sha256_file(dest_file)
                result["content_type"] = resp.headers.get("content-type", "unknown")
                result["downloaded_at"] = datetime.now(timezone.utc).isoformat()
                log(f"[OK] {src.doc_id}: {result['size_bytes']} bytes, sha256={result['sha256'][:16]}...")
                return result
            elif resp.status_code in (403, 429):
                log(f"[BLOCKED] {src.doc_id}: HTTP {resp.status_code} (attempt {attempt})")
                if attempt < MAX_RETRIES:
                    time.sleep(5)
            else:
                log(f"[ERROR] {src.doc_id}: HTTP {resp.status_code}")
                if attempt < MAX_RETRIES:
                    time.sleep(2)

        except httpx.TimeoutException:
            log(f"[TIMEOUT] {src.doc_id} (attempt {attempt})")
            if attempt < MAX_RETRIES:
                time.sleep(3)
        except Exception as e:
            log(f"[ERROR] {src.doc_id}: {type(e).__name__}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2)

    result["status"] = "failed"
    result["error"] = f"Failed after {MAX_RETRIES} attempts"
    log(f"[FAIL] {src.doc_id}: {result['error']}")
    return result


def main():
    dry_run = "--dry-run" in sys.argv

    # Create directories
    for d in [CACHE_ROOT, AUTO_DIR, MANUAL_DIR, MANUAL_DIR / "ccn" / "stic_serie_800", MANUAL_DIR / "ccn" / "its"]:
        d.mkdir(parents=True, exist_ok=True)

    log(f"=== FULKRO Corpus Download {'(DRY RUN)' if dry_run else ''} ===")
    log(f"Cache root: {CACHE_ROOT}")
    log(f"Sources: {len(AUTO_SOURCES)} auto-downloadable")

    manifest = []
    failed = []

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as client:
        for i, src in enumerate(AUTO_SOURCES, 1):
            log(f"\n--- [{i}/{len(AUTO_SOURCES)}] {src.doc_id} ---")
            result = download_source(client, src, dry_run)
            if result.get("status") == "fetched" or result.get("status") == "dry_run":
                manifest.append(result)
            else:
                failed.append(result)
            # Be polite
            if not dry_run and not src.url.startswith("local://"):
                time.sleep(1)

    # Write manifest and failed
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    FAILED_PATH.write_text(json.dumps(failed, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    log(f"\n=== SUMMARY ===")
    log(f"Downloaded: {len(manifest)} sources")
    log(f"Failed: {len(failed)} sources")
    log(f"Manifest: {MANIFEST_PATH}")
    log(f"Failed: {FAILED_PATH}")

    if failed:
        log(f"\nFailed sources:")
        for f in failed:
            log(f"  {f['doc_id']}: {f.get('error', 'unknown')}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
