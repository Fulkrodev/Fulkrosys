#!/usr/bin/env python3
"""
rename_sgsi_ids.py — Renumeración masiva de IDs SGSI conforme a Corrección 1 v2.1.

Ejecutar ANTES de iniciar la construcción de FULKRO.
Lee los ficheros F1/F2 originales y aplica las sustituciones de IDs.

Uso:
    python scripts/rename_sgsi_ids.py fulkro_dev/ --dry-run   # preview
    python scripts/rename_sgsi_ids.py fulkro_dev/              # apply
"""
import re
import sys
from pathlib import Path

# === MAPPING TABLES (Corrección 1, §1.2 y §2.2) ===

POLICY_MAP = {
    "E-101": "ABSORB_INTO_E100",  # Se absorbe en E-100 §7
    "E-102": "E-101",
    "E-103": "E-108",
    "E-104": "E-109",
    "E-105": "E-107",
    "E-106": "E-103",
    "E-107": "E-112",
    "E-108": "E-104",
}

PROCEDURE_MAP = {
    "E-200": "E-AR-001",
    "E-203": "E-221",
    # E-204 sin cambio
    "E-205": "E-231",
    "E-206": "E-203",
    "E-207": "E-PF-001",
    "E-210": "E-207",
    # E-217 sin cambio
    "E-218": "E-205",
    "E-219": "E-IT-001",
    "E-228": "E-204-A",
    "E-234": "E-218",
}

FULL_MAP = {**POLICY_MAP, **PROCEDURE_MAP}

# Files that need renumbering (only the original F1/F2)
TARGET_FILES = [
    "F1_1_POLITICAS_CRITICAS_E100_E104 (1).md",
    "F1_2_POLITICAS_CRITICAS_E105_E108 (1).md",
    "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
    "F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md",
]


def remap_id(old_id: str) -> str | None:
    """Return new ID for old_id, or None if no mapping exists."""
    return FULL_MAP.get(old_id)


def apply_renumbering(text: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Apply all renumbering substitutions to text.
    Returns (new_text, list_of_(old, new) replacements made).

    Strategy: use word-boundary matching to replace E-XXX references.
    Process in two passes to avoid cascading substitutions:
    1. Replace all old IDs with temporary placeholders
    2. Replace placeholders with final IDs
    """
    changes = []
    result = text

    # Build placeholder map to avoid cascading
    placeholder_map = {}
    for old_id, new_id in FULL_MAP.items():
        placeholder = f"__RENAME_{old_id.replace('-', '_')}__"
        placeholder_map[old_id] = (placeholder, new_id)

    # Pass 1: Replace old IDs with placeholders
    for old_id, (placeholder, _) in placeholder_map.items():
        # Match E-XXX at word boundaries, including in Jinja2 templates
        # Pattern handles: E-XXX, "E-XXX", E-XXX., E-XXX,, etc.
        pattern = re.compile(r'\b' + re.escape(old_id) + r'\b')
        if pattern.search(result):
            count = len(pattern.findall(result))
            result = pattern.sub(placeholder, result)
            changes.append((old_id, FULL_MAP[old_id], count))

    # Also handle {{ proyecto.codigo_documento_base }}-XXX patterns
    for old_id, (placeholder, _) in placeholder_map.items():
        num = old_id.split("-")[1] if "-" in old_id else ""
        if num and num.isdigit():
            jinja_pattern = re.compile(
                r'(\{\{\s*proyecto\.codigo_documento_base\s*\}\})-' + re.escape(num) + r'\b'
            )
            if jinja_pattern.search(result):
                new_id = FULL_MAP[old_id]
                new_num = new_id.split("-", 1)[1] if "-" in new_id else new_id
                jinja_placeholder = f"__JINJA_RENAME_{num}__"
                result = jinja_pattern.sub(r'\1-' + jinja_placeholder, result)
                # Will be resolved in pass 2

    # Pass 2: Replace placeholders with final IDs
    for old_id, (placeholder, new_id) in placeholder_map.items():
        result = result.replace(placeholder, new_id)

    # Resolve Jinja placeholders
    for old_id in FULL_MAP:
        num = old_id.split("-")[1] if "-" in old_id else ""
        if num and num.isdigit():
            new_id = FULL_MAP[old_id]
            new_num = new_id.split("-", 1)[1] if "-" in new_id else new_id
            jinja_placeholder = f"__JINJA_RENAME_{num}__"
            result = result.replace(jinja_placeholder, new_num)

    return result, changes


def process_file(filepath: Path, dry_run: bool = True) -> list[tuple[str, str, int]]:
    """Process a single file. Returns list of (old_id, new_id, count)."""
    content = filepath.read_text(encoding="utf-8")
    new_content, changes = apply_renumbering(content)

    if not dry_run and changes and new_content != content:
        filepath.write_text(new_content, encoding="utf-8")

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    target_dir = Path(args[0]) if args else Path(".")

    total_changes = 0
    total_files = 0

    for filename in TARGET_FILES:
        filepath = target_dir / filename
        if not filepath.exists():
            print(f"  SKIP: {filename} (not found)")
            continue

        changes = process_file(filepath, dry_run=dry_run)
        if changes:
            total_files += 1
            prefix = "[DRY RUN] " if dry_run else "[APPLIED] "
            print(f"\n{prefix}{filename}")
            for old_id, new_id, count in changes:
                print(f"  {old_id} -> {new_id}  ({count} occurrences)")
                total_changes += count

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Total: {total_changes} substitutions across {total_files} files.")

    if dry_run:
        print("\nRun without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
