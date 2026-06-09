#!/usr/bin/env python3
"""
FULKRO Fase C — Corpus ingester.

Reads all files from ~/.fulkro/corpus_cache/{auto,manual}/,
extracts text, chunks, generates embeddings, inserts into PostgreSQL.

Usage:
    python scripts/corpus_ingest.py                # full ingestion
    python scripts/corpus_ingest.py --dry-run      # scan files only
    python scripts/corpus_ingest.py --stats        # show DB stats

Requirements:
    pip install pdfplumber beautifulsoup4 sentence-transformers psycopg2-binary
    apt install tesseract-ocr tesseract-ocr-spa  (for OCR fallback)
"""
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import psycopg2
from bs4 import BeautifulSoup

# === CONFIG ===
CACHE_ROOT = Path.home() / ".fulkro" / "corpus_cache"
LOG_PATH = CACHE_ROOT / "ingest.log"
MODEL_CACHE = Path.home() / ".fulkro" / "models"
DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://fulkro:changeme@localhost:5433/fulkro",
)
CHUNK_SIZE = 1500       # chars per chunk
CHUNK_OVERLAP = 200     # overlap between chunks
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("corpus_ingest")


# === WATERMARK CLEANING ===

CCN_WATERMARK_PATTERNS = [
    r"Centro Criptológico Nacional\s+SIN CLASIFICAR",
    r"SIN CLASIFICAR",
    r"\[Escriba aquí\]",
    r"\[Escriba aqui\]",
]


def clean_ccn_watermarks(text: str) -> str:
    """Remove known CCN-CERT watermarks from extracted PDF text.

    Targets literal watermarks only (SIN CLASIFICAR, [Escriba aquí]).
    Does NOT attempt to fix OCR artifacts (spaced letters, interleaved numbers).
    OCR artifacts are a separate problem requiring dedicated heuristic analysis.
    """
    cleaned = text
    for pattern in CCN_WATERMARK_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    # Normalize excessive whitespace left by removals
    cleaned = re.sub(r"\s{3,}", "  ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# === TEXT EXTRACTION ===

def extract_pdf(path: Path) -> tuple[str, str, float]:
    """Extract text from PDF. Returns (text, method, quality 0-1)."""
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages.append(t)
            text = "\n\n".join(pages)
    except Exception as e:
        log.warning(f"pdfplumber failed for {path.name}: {e}")

    # Check if extraction got meaningful text
    if len(text.strip()) > 200:
        return text, "pdfplumber", 0.9

    # Fallback: OCR with Tesseract
    log.info(f"  OCR fallback for {path.name} (pdfplumber got {len(text)} chars)")
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0 and len(result.stdout.strip()) > 200:
            return result.stdout, "pdftotext", 0.7
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Last resort: Tesseract OCR (very slow)
    try:
        result = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", "spa", "--psm", "3"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0 and len(result.stdout.strip()) > 100:
            return result.stdout, "tesseract_ocr", 0.5
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Return whatever pdfplumber got even if minimal
    if text.strip():
        return text, "pdfplumber_partial", 0.3
    return "", "failed", 0.0


def extract_html(path: Path) -> tuple[str, str, float]:
    """Extract text from HTML."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        # Remove scripts, styles, nav
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return text, "beautifulsoup", 0.85
    except Exception as e:
        log.warning(f"HTML extract failed for {path.name}: {e}")
    return "", "failed", 0.0


def extract_markdown(path: Path) -> tuple[str, str, float]:
    """Extract text from Markdown."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text, "raw_markdown", 0.95
    except Exception as e:
        log.warning(f"MD extract failed for {path.name}: {e}")
    return "", "failed", 0.0


def extract_text(path: Path) -> tuple[str, str, float]:
    """Route to the correct extractor based on file extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext in (".html", ".htm"):
        return extract_html(path)
    elif ext in (".md", ".txt"):
        return extract_markdown(path)
    else:
        log.warning(f"Unknown file type: {path.name}")
        return "", "unsupported", 0.0


# === CHUNKING ===

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks respecting paragraph boundaries."""
    if not text.strip():
        return []

    # Split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph would exceed chunk_size
        if len(current_chunk) + len(para) + 2 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from end of current chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:]
                else:
                    current_chunk = ""

            # Handle paragraphs larger than chunk_size
            if len(para) > chunk_size:
                # Split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = current_chunk[-overlap:] if overlap > 0 and len(current_chunk) > overlap else ""
                    current_chunk += " " + sent if current_chunk else sent
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# === EMBEDDING ===

_model = None

def get_embedding_model():
    """Load sentence-transformers model (cached)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        MODEL_CACHE.mkdir(parents=True, exist_ok=True)
        log.info(f"Loading embedding model {EMBEDDING_MODEL} (first time may download ~2GB)...")
        _model = SentenceTransformer(EMBEDDING_MODEL, cache_folder=str(MODEL_CACHE))
        log.info(f"Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


def generate_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    model = get_embedding_model()
    # Prefix for e5 models: "query: " or "passage: "
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, batch_size=batch_size, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


# === DATABASE ===

def get_db_conn():
    """Get a psycopg2 connection."""
    return psycopg2.connect(DB_URL)


def insert_document(conn, doc_id: str, title: str, source_url: str,
                    file_path: str, sha256: str, extraction_method: str,
                    extraction_quality: float, language: str = "es") -> str:
    """Insert a knowledge_document and return its UUID."""
    uid = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO knowledge_documents
                (id, fuente, titulo, version, hash_sha256, contenido_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (uid, source_url, title, "1.0", sha256, file_path, datetime.now(timezone.utc)))
    conn.commit()
    return uid


def insert_chunks(conn, doc_uuid: str, chunks: list[str], embeddings: list[list[float]]):
    """Insert chunks with embeddings into knowledge_chunks."""
    with conn.cursor() as cur:
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            # Section detection: first line or first 80 chars
            section = chunk_text[:80].split("\n")[0].strip()
            cur.execute("""
                INSERT INTO knowledge_chunks
                    (id, document_id, seccion, contenido, embedding, metadata_extra, created_at)
                VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
            """, (
                chunk_id, doc_uuid, section, chunk_text,
                str(embedding), json.dumps({"chunk_index": i}),
                datetime.now(timezone.utc),
            ))
    conn.commit()


def get_ingested_hashes(conn) -> set[str]:
    """Get SHA-256 hashes of already-ingested documents."""
    with conn.cursor() as cur:
        cur.execute("SELECT hash_sha256 FROM knowledge_documents WHERE hash_sha256 IS NOT NULL")
        return {row[0] for row in cur.fetchall()}


# === MAIN INGESTION ===

def scan_corpus_files() -> list[dict]:
    """Scan cache directories for files to ingest."""
    files = []
    for subdir in ["auto", "manual"]:
        base = CACHE_ROOT / subdir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".pdf", ".html", ".htm", ".md", ".txt"):
                # Skip metadata files
                if path.name in ("manifest.json", "failed.json", "ingest.log"):
                    continue
                rel = path.relative_to(CACHE_ROOT)
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
                files.append({
                    "path": path,
                    "relative": str(rel),
                    "name": path.stem,
                    "ext": path.suffix.lower(),
                    "size": path.stat().st_size,
                    "sha256": sha,
                    "source": subdir,
                })
    return files


def ingest_file(conn, finfo: dict, dry_run: bool = False) -> dict:
    """Ingest a single file: extract, chunk, embed, insert."""
    path = finfo["path"]
    result = {"file": finfo["relative"], "status": "pending"}

    # Extract text
    text, method, quality = extract_text(path)
    result["extraction_method"] = method
    result["extraction_quality"] = quality
    result["text_length"] = len(text)

    if not text.strip():
        result["status"] = "failed"
        result["error"] = "No text extracted"
        return result

    # Clean CCN watermarks before chunking
    text = clean_ccn_watermarks(text)

    # Chunk
    chunks = chunk_text(text)
    result["chunks"] = len(chunks)

    if not chunks:
        result["status"] = "failed"
        result["error"] = "No chunks generated"
        return result

    if dry_run:
        result["status"] = "dry_run"
        return result

    # Generate embeddings
    embeddings = generate_embeddings(chunks)
    result["embeddings"] = len(embeddings)

    # Build title from filename
    title = path.stem.replace("_", " ").replace("-", " ").title()

    # Insert document
    doc_uuid = insert_document(
        conn,
        doc_id=finfo["name"],
        title=title,
        source_url=finfo["relative"],
        file_path=str(path),
        sha256=finfo["sha256"],
        extraction_method=method,
        extraction_quality=quality,
    )
    result["doc_uuid"] = doc_uuid

    # Insert chunks with embeddings
    insert_chunks(conn, doc_uuid, chunks, embeddings)
    result["status"] = "ingested"

    return result


def show_stats(conn):
    """Show current DB stats."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM knowledge_documents")
        docs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM knowledge_chunks")
        chunks = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM knowledge_chunks WHERE embedding IS NOT NULL")
        with_emb = cur.fetchone()[0]
    print(f"Documents: {docs}")
    print(f"Chunks: {chunks}")
    print(f"Chunks with embeddings: {with_emb}")


def main():
    dry_run = "--dry-run" in sys.argv
    stats_only = "--stats" in sys.argv

    conn = get_db_conn()

    if stats_only:
        show_stats(conn)
        conn.close()
        return 0

    # Scan files
    files = scan_corpus_files()
    log.info(f"Found {len(files)} corpus files to process")

    # Check already ingested
    existing_hashes = get_ingested_hashes(conn)
    new_files = [f for f in files if f["sha256"] not in existing_hashes]
    log.info(f"Already ingested: {len(files) - len(new_files)}, new: {len(new_files)}")

    if not new_files:
        log.info("Nothing new to ingest")
        show_stats(conn)
        conn.close()
        return 0

    if not dry_run:
        # Load model upfront (will download ~2GB first time)
        get_embedding_model()

    results = []
    start_time = time.time()

    for i, finfo in enumerate(new_files, 1):
        log.info(f"[{i}/{len(new_files)}] {finfo['relative']} ({finfo['size']:,} bytes)")
        try:
            result = ingest_file(conn, finfo, dry_run=dry_run)
            log.info(f"  -> {result['status']}: {result.get('chunks', 0)} chunks, "
                     f"method={result.get('extraction_method')}, "
                     f"quality={result.get('extraction_quality', 0):.1f}")
        except Exception as e:
            log.error(f"  -> FAILED: {type(e).__name__}: {e}")
            result = {"file": finfo["relative"], "status": "error", "error": str(e)}
        results.append(result)

    elapsed = time.time() - start_time

    # Summary
    ok = sum(1 for r in results if r["status"] == "ingested")
    failed = sum(1 for r in results if r["status"] in ("failed", "error"))
    total_chunks = sum(r.get("chunks", 0) for r in results)

    log.info(f"\n=== INGESTION COMPLETE ===")
    log.info(f"Time: {elapsed:.0f}s")
    log.info(f"Ingested: {ok}/{len(new_files)} files")
    log.info(f"Failed: {failed}")
    log.info(f"Total chunks: {total_chunks}")

    if not dry_run:
        show_stats(conn)

    if failed:
        log.warning("Failed files:")
        for r in results:
            if r["status"] in ("failed", "error"):
                log.warning(f"  {r['file']}: {r.get('error', 'unknown')}")

    conn.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
