"""Corpus ingester v2 — current schema (``content``, ``source_id``).

Replaces ``scripts/corpus_ingest.py`` which wrote to the legacy ``contenido``
column and never populated ``knowledge_sources``.

v2:
- Creates one ``knowledge_sources`` row per file using ``SOURCE_MAP``.
- Inserts ``knowledge_documents`` with ``source_id`` (no more orphans).
- Inserts ``knowledge_chunks`` with ``content`` + ``embedding`` (1024 dims) +
  auto-detected ``measure_code`` / ``article_ref``.
- Updates ``knowledge_documents.chunk_count``.
- Idempotent: ``ON CONFLICT (code) DO NOTHING`` on ``knowledge_sources``,
  skips files whose ``content_hash`` is already present.

Run:
    PYTHONPATH=. python scripts/corpus_ingest_v2.py
    PYTHONPATH=. python scripts/corpus_ingest_v2.py --stats
    PYTHONPATH=. python scripts/corpus_ingest_v2.py --reset-orphans
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import psycopg2
from bs4 import BeautifulSoup

# FastEmbed is pulled from the app singleton to keep the retrieval embedding
# space consistent with what already sits in the HNSW index.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.core.ai.embeddings import get_default_embedding_provider


CACHE_ROOT = Path.home() / ".fulkro" / "corpus_cache"
DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200
EMBEDDING_DIM = 1024

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("corpus_v2")


# ---------------------------------------------------------------------------
# Source mapping: relative_path_prefix → (code, title, publisher)
# ---------------------------------------------------------------------------
SOURCE_MAP: dict[str, tuple[str, str, str]] = {
    # BOE legal
    "auto/boe/its_auditoria":        ("ITS_AUDITORIA",        "ITS Auditoría ENS",                         "BOE"),
    "auto/boe/its_conformidad":      ("ITS_CONFORMIDAD",      "ITS Conformidad ENS",                       "BOE"),
    "auto/boe/its_estado_seguridad": ("ITS_ESTADO_SEGURIDAD", "ITS Estado de Seguridad",                   "BOE"),
    "auto/boe/its_incidentes":       ("ITS_INCIDENTES",       "ITS Notificación de Incidentes",            "BOE"),
    "auto/boe/ley_39_2015":          ("LEY_39_2015",          "Ley 39/2015 Procedimiento Administrativo",  "BOE"),
    "auto/boe/ley_40_2015":          ("LEY_40_2015",          "Ley 40/2015 Régimen Jurídico Sector Público", "BOE"),
    "auto/boe/lopdgdd":              ("LOPDGDD",              "LO 3/2018 Protección de Datos",             "BOE"),
    "auto/boe/rd_311_2022":          ("RD_311_2022",          "RD 311/2022 ENS (consolidado)",             "BOE"),
    # CCN-STIC
    "manual/ccn/stic_serie_800/ccn_stic_800_glosario":         ("CCN_STIC_800", "CCN-STIC 800 Glosario ENS",                "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_801_responsabilidades":("CCN_STIC_801", "CCN-STIC 801 Responsabilidades y Funciones","CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_802_auditoria":        ("CCN_STIC_802", "CCN-STIC 802 Auditoría del ENS",           "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_803_valoracion":       ("CCN_STIC_803", "CCN-STIC 803 Valoración de Sistemas",      "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_804_medidas":          ("CCN_STIC_804", "CCN-STIC 804 Guía de Implantación ENS",    "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_805_politica":         ("CCN_STIC_805", "CCN-STIC 805 Política de Seguridad",       "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_806_plan_adecuacion":  ("CCN_STIC_806", "CCN-STIC 806 Plan de Adecuación",          "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_807_criptologia":      ("CCN_STIC_807", "CCN-STIC 807 Criptología",                 "CCN-CERT"),
    "manual/ccn/stic_serie_800/ccn_stic_808_verificacion":     ("CCN_STIC_808", "CCN-STIC 808 Verificación del Cumplimiento", "CCN-CERT"),
    # MAGERIT
    "auto/magerit/magerit_v3_libro1_metodo":    ("MAGERIT_V3_LIB1", "MAGERIT v3 Libro 1 — Método",     "Min. de Hacienda"),
    "auto/magerit/magerit_v3_libro2_catalogo":  ("MAGERIT_V3_LIB2", "MAGERIT v3 Libro 2 — Catálogo",   "Min. de Hacienda"),
    "auto/magerit/magerit_v3_libro3_tecnicas":  ("MAGERIT_V3_LIB3", "MAGERIT v3 Libro 3 — Técnicas",   "Min. de Hacienda"),
    # CCN Portal
    "auto/ccn_portal/ens_certificadoras":     ("ENS_CERTIFICADORAS",     "Entidades Certificadoras ENS", "CCN-CERT"),
    "auto/ccn_portal/ens_distintivos":        ("ENS_DISTINTIVOS",        "Distintivos ENS",              "CCN-CERT"),
    "auto/ccn_portal/ens_faq":                ("ENS_FAQ",                "FAQ ENS",                      "CCN-CERT"),
    "auto/ccn_portal/ens_proceso_adecuacion": ("ENS_PROCESO_ADECUACION", "Proceso de Adecuación ENS",    "CCN-CERT"),
    # AEPD
    "auto/aepd/edpb_directrices_brechas_es": ("AEPD_EDPB_BRECHAS",     "EDPB Directrices Brechas de Seguridad", "EDPB"),
    "auto/aepd/guia_brechas_seguridad":      ("AEPD_GUIA_BRECHAS",     "AEPD Guía Brechas de Seguridad",        "AEPD"),
    "auto/aepd/guia_riesgos_eipd":           ("AEPD_GUIA_RIESGOS_EIPD","AEPD Guía Gestión de Riesgos EIPD",     "AEPD"),
    "manual/aepd/guia_eipd":                 ("AEPD_GUIA_EIPD",        "AEPD Guía EIPD",                        "AEPD"),
    # EU
    "manual/eur_lex/rgpd_2016_679":    ("RGPD",  "Reglamento (UE) 2016/679 GDPR",           "EUR-Lex"),
    "manual/eur_lex/nis2_2022_2555":   ("NIS2",  "Directiva (UE) 2022/2555 NIS2",           "EUR-Lex"),
    "manual/eur_lex/dora_2022_2554":   ("DORA",  "Reglamento (UE) 2022/2554 DORA",          "EUR-Lex"),
    "manual/eur_lex/eidas_910_2014":   ("EIDAS", "Reglamento (UE) 910/2014 eIDAS",          "EUR-Lex"),
    # ISO
    "auto/iso_27001/iso27001_es_parte1":          ("ISO_27001_P1", "ISO 27001 Parte 1",         "ISO"),
    "auto/iso_27001/iso27001_es_parte2_mapping":  ("ISO_27001_P2", "ISO 27001 Parte 2 Mapping", "ISO"),
    # MITRE / NIST / OWASP / Casos
    "auto/mitre/mitre_attack_enterprise":       ("MITRE_ATT_CK",   "MITRE ATT&CK Enterprise",      "MITRE"),
    "auto/nist/nist_csf_2.0":                   ("NIST_CSF_2",     "NIST CSF 2.0",                 "NIST"),
    "auto/nist/nist_sp_800_53r5":               ("NIST_SP_800_53", "NIST SP 800-53r5",             "NIST"),
    "auto/owasp/owasp_top10_2021":              ("OWASP_TOP10",    "OWASP Top 10 2021",            "OWASP"),
    "auto/owasp/owasp_api_top10_2023":          ("OWASP_API_TOP10","OWASP API Top 10 2023",        "OWASP"),
    "auto/magerit_casos/jaymon_soluciones_rapidas": ("MAGERIT_CASOS_JAYMON", "MAGERIT Casos Prácticos", "Jaymon"),
}


MEASURE_CODE_RE = re.compile(
    r"\b(org\.\d+|op\.(?:pl|acc|exp|ext|nub|cont|mon)\.\d+|mp\.(?:if|per|eq|com|si|sw|info|s)\.\d+)\b",
    re.IGNORECASE,
)
ARTICLE_RE = re.compile(r"art[íi]culo\s*(\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            txt = "\n\n".join(pages)
        if len(txt.strip()) > 200:
            return txt
    except Exception as exc:
        log.warning("pdfplumber failed on %s: %s", path.name, exc)
    try:
        r = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode == 0 and len(r.stdout.strip()) > 200:
            return r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    if ext in (".html", ".htm"):
        return _extract_html(path)
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


# ---------------------------------------------------------------------------
# Cleaning + chunking
# ---------------------------------------------------------------------------

_WATERMARKS = [
    r"Centro Criptológico Nacional\s+SIN CLASIFICAR",
    r"\bSIN CLASIFICAR\b",
    r"\[Escriba aqu[íi]\]",
]


def _clean(text: str) -> str:
    for pat in _WATERMARKS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{3,}", "  ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text.strip():
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for para in paragraphs:
        if len(cur) + len(para) + 2 > size and cur:
            chunks.append(cur.strip())
            cur = cur[-overlap:] if overlap and len(cur) > overlap else ""
        if len(para) > size:
            for sent in re.split(r"(?<=[.!?])\s+", para):
                if len(cur) + len(sent) + 1 > size and cur:
                    chunks.append(cur.strip())
                    cur = cur[-overlap:] if overlap and len(cur) > overlap else ""
                cur = (cur + " " + sent).strip() if cur else sent
        else:
            cur = (cur + "\n\n" + para) if cur else para
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def _detect_measure(chunk: str) -> str | None:
    m = MEASURE_CODE_RE.search(chunk)
    return m.group(1).lower() if m else None


def _detect_article(chunk: str) -> str | None:
    m = ARTICLE_RE.search(chunk)
    return f"Art.{m.group(1)}" if m else None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _connect():
    return psycopg2.connect(DB_URL)


def _upsert_source(cur, code: str, title: str, publisher: str, url: str) -> str:
    cur.execute(
        """
        INSERT INTO knowledge_sources (code, title, publisher, source_url, language)
        VALUES (%s, %s, %s, %s, 'es')
        ON CONFLICT (code) DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        (code, title, publisher, url),
    )
    return cur.fetchone()[0]


def _insert_document(cur, source_id: str, title: str, content_hash: str,
                     mime_type: str, path: str) -> str:
    doc_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO knowledge_documents
            (id, source_id, title, titulo, fuente, content_hash, hash_sha256,
             mime_type, contenido_path, chunk_count, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
        """,
        (
            doc_id, source_id, title, title, path, content_hash, content_hash,
            mime_type, path, json.dumps({"ingested_at": datetime.now(timezone.utc).isoformat()}),
        ),
    )
    return doc_id


def _insert_chunks(cur, doc_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
    for idx, (text, vec) in enumerate(zip(chunks, embeddings)):
        heading = text[:80].split("\n")[0].strip()
        measure = _detect_measure(text)
        article = _detect_article(text)
        cur.execute(
            """
            INSERT INTO knowledge_chunks
                (id, document_id, content, seccion, heading_path,
                 measure_code, article_ref, chunk_index, token_count,
                 embedding, metadata_extra)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
            """,
            (
                str(uuid.uuid4()), doc_id, text, heading[:250], heading[:510],
                measure, article, idx, len(text.split()),
                "[" + ",".join(f"{x:.7f}" for x in vec) + "]",
                json.dumps({"chunk_index": idx}),
            ),
        )
    cur.execute(
        "UPDATE knowledge_documents SET chunk_count = %s, updated_at = now() WHERE id = %s",
        (len(chunks), doc_id),
    )


def _reset_orphans(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM knowledge_chunks
            WHERE document_id IN (
                SELECT id FROM knowledge_documents WHERE source_id IS NULL
            )
            """
        )
        deleted_chunks = cur.rowcount
        cur.execute("DELETE FROM knowledge_documents WHERE source_id IS NULL")
        deleted_docs = cur.rowcount
    conn.commit()
    log.info("Reset orphans: %s chunks, %s docs removed", deleted_chunks, deleted_docs)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _scan_cache() -> list[dict]:
    files: list[dict] = []
    for sub in ("auto", "manual"):
        base = CACHE_ROOT / sub
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".pdf", ".html", ".htm", ".md", ".txt"):
                rel = path.relative_to(CACHE_ROOT)
                stem_key = str(rel.with_suffix(""))
                if stem_key not in SOURCE_MAP:
                    log.warning("No SOURCE_MAP entry for %s — skipping", stem_key)
                    continue
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                files.append({
                    "path": path,
                    "stem_key": stem_key,
                    "sha256": sha,
                })
    return files


def _stats(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM knowledge_sources")
        sources = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM knowledge_documents")
        docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        chunks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL")
        with_emb = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(DISTINCT measure_code) FROM knowledge_chunks WHERE measure_code IS NOT NULL"
        )
        measures_covered = cur.fetchone()[0]
    print(f"knowledge_sources:   {sources}")
    print(f"knowledge_documents: {docs}")
    print(f"knowledge_chunks:    {chunks} ({with_emb} with embedding)")
    print(f"distinct measure_codes in chunks: {measures_covered}")


def main() -> int:
    conn = _connect()
    conn.autocommit = False

    if "--stats" in sys.argv:
        _stats(conn)
        conn.close()
        return 0

    if "--reset-orphans" in sys.argv:
        _reset_orphans(conn)
        _stats(conn)
        conn.close()
        return 0

    with conn.cursor() as cur:
        cur.execute("SELECT hash_sha256 FROM knowledge_documents WHERE hash_sha256 IS NOT NULL AND source_id IS NOT NULL")
        existing_hashes = {row[0] for row in cur.fetchall()}

    files = _scan_cache()
    pending = [f for f in files if f["sha256"] not in existing_hashes]
    log.info("Cache files: %s total · %s pending ingest", len(files), len(pending))

    max_files = None
    for arg in sys.argv[1:]:
        if arg.startswith("--max-files="):
            max_files = int(arg.split("=", 1)[1])
    if max_files is not None:
        pending = pending[:max_files]
        log.info("Limiting to first %s pending (--max-files)", max_files)

    if not pending:
        _stats(conn)
        conn.close()
        return 0

    log.info("Loading embedding provider...")
    emb = get_default_embedding_provider()
    log.info("Provider ready: %s (dim=%s)", emb.model_name, emb.dimensions)

    total_new_chunks = 0
    for i, finfo in enumerate(pending, 1):
        path: Path = finfo["path"]
        stem_key: str = finfo["stem_key"]
        code, title, publisher = SOURCE_MAP[stem_key]
        log.info("[%s/%s] %s — %s (%s)", i, len(pending), stem_key, code, path.suffix)

        try:
            text = _extract(path)
        except Exception as exc:
            log.error("  EXTRACT FAIL: %s", exc)
            continue
        text = _clean(text)
        if len(text) < 200:
            log.warning("  SKIPPED: insufficient text (%s chars)", len(text))
            continue

        chunks = _chunk(text)
        if not chunks:
            log.warning("  SKIPPED: no chunks")
            continue

        log.info("  Extracted %s chars → %s chunks. Embedding (batch=32)...", len(text), len(chunks))
        vecs: list[list[float]] = []
        BATCH = 32
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i:i + BATCH]
            try:
                partial = emb.embed_documents(batch)
            except Exception as exc:
                log.error("  EMBEDDING FAIL at offset %s: %s", i, exc)
                partial = []
                break
            vecs.extend(partial)
            if (i // BATCH) % 4 == 0 and i > 0:
                log.info("    ...embedded %s/%s chunks", len(vecs), len(chunks))
        if len(vecs) != len(chunks) or (vecs and len(vecs[0]) != EMBEDDING_DIM):
            log.error("  EMBEDDING MISMATCH: got %s vecs dim=%s",
                      len(vecs), len(vecs[0]) if vecs else 0)
            continue

        mime = {"pdf": "application/pdf", "htm": "text/html", "html": "text/html",
                "md": "text/markdown", "txt": "text/plain"}.get(path.suffix.lstrip(".").lower(), "text/plain")

        try:
            with conn.cursor() as cur:
                source_id = _upsert_source(cur, code, title, publisher, str(path))
                doc_id = _insert_document(
                    cur, source_id, title, finfo["sha256"], mime, str(path)
                )
                _insert_chunks(cur, doc_id, chunks, vecs)
            conn.commit()
            total_new_chunks += len(chunks)
            log.info("  OK: %s chunks inserted", len(chunks))
        except Exception as exc:
            conn.rollback()
            log.error("  DB FAIL: %s", exc)

    log.info("=== DONE === new chunks: %s", total_new_chunks)
    _stats(conn)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
