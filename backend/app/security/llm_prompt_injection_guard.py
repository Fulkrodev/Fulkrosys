"""LLM prompt-injection guard · Ejecutable 3 Phase 5.2 Sesión 5 base.

Pure functional sanitization + jailbreak detection layer · pre-LLM call.

Phase 5.0 audit-first reveal: ZERO sanitization/jailbreak guards en
m11_copiloto pre-Ejecutable 3 (greenfield critical gap per Sesión 5 base
audit baseline). Pattern P-CL2-1 audit-first reveal infrastructure ratio
disparó implementación turbo.

Doctrinas:
- Pure functional · NO HTTP/ORM/side-effects (testeable + reusable
  cross-consumer m11_copiloto + A14 RAG + A21 detector + A20 narrative)
- Defense-in-depth: sanitization NO único guard · LLM system-prompt
  boundaries + per-context policies + audit_log emit defensive logging
- R30 admin tutor friendly · sanitization NUNCA bloquea Marcos legítimo
  · solo flagged user-facing input (cliente portal · auditor portal)
- OPS-049 honest defer · false-positive count tracked · refinement
  empirical post-piloto (Future-S5.X.llm-pi-policy-tuning)

Categorías detection (8 critical patterns):
1. role_manipulation · "system:" · "assistant:" · injected role markers
2. ignore_previous · "ignore previous" · "disregard above" · jailbreak common
3. system_extraction · "what are your instructions" · "show system prompt"
4. context_bleed · cross-project mentions ("client X" cuando current = Y)
5. base64_obfuscation · base64-encoded payload chunks
6. multilingual_evasion · español/inglés mix con jailbreak markers
7. delimiter_injection · XML/markdown delimiters tentativa override
8. excessive_length · >10k chars input (potential context pollution)

Output: SanitizationResult con sanitized_input + violations list +
should_block boolean + audit_log emit hint.

Usage pattern:
    from backend.app.security.llm_prompt_injection_guard import (
        sanitize_user_input, SanitizationResult,
    )

    result = sanitize_user_input(user_message, max_length=10_000)
    if result.should_block:
        # Audit log + return friendly error R29
        return {"error": "Tu mensaje no se pudo procesar · prueba reformular"}

    safe_message = result.sanitized_input
    # Proceed with LLM call · safe_message + context guards
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Literal


def neutralize_context_value(value: str | None, max_length: int = 120) -> str:
    """Neutraliza una variable de CONTEXTO (nombre de proyecto, título de paso,
    concepto) ANTES de interpolarla en el prompt del LLM.

    A diferencia de ``sanitize_user_input`` (detector de jailbreak para el
    mensaje libre del usuario), esto NO bloquea ni audita: solo retira el vector
    de inyección de un valor que viaja desde datos del proyecto. Elimina saltos
    de línea + caracteres de control, neutraliza comillas/backticks/delimitadores
    que permitirían escapar del ``"..."`` de la plantilla, colapsa espacios y
    trunca. Defense-in-depth (FRENTE E hardening · verificación adversarial:
    project_nombre/step_title llegaban sin escapar al prompt).
    """
    if not value:
        return ""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", value)          # control chars + \n
    cleaned = cleaned.replace('"', "'").replace("`", "'")      # comillas → simples
    cleaned = re.sub(r"[{}<>\[\]]", " ", cleaned)              # delimitadores
    cleaned = re.sub(r"\s+", " ", cleaned).strip()             # colapsa espacios
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "…"
    return cleaned


ViolationCategory = Literal[
    "role_manipulation",
    "ignore_previous",
    "system_extraction",
    "context_bleed",
    "base64_obfuscation",
    "multilingual_evasion",
    "delimiter_injection",
    "excessive_length",
]


@dataclass
class Violation:
    """Specific PI violation detected · category + matched pattern excerpt."""

    category: ViolationCategory
    pattern_excerpt: str  # First 80 chars matched · audit log friendly
    severity: Literal["info", "warning", "critical"]


@dataclass
class SanitizationResult:
    """Outcome of sanitize_user_input · JSON-serializable for audit_log."""

    sanitized_input: str
    violations: list[Violation] = field(default_factory=list)
    should_block: bool = False
    original_length: int = 0
    sanitized_length: int = 0


# ════════════════════════════════════════════════════════════════════
# Detection patterns · deterministic regex (NO LLM · R1 + R3 temp ≤ 0.2)
# ════════════════════════════════════════════════════════════════════

# 1. role_manipulation · injected role markers tentativa override
_ROLE_MANIPULATION_PATTERNS = [
    re.compile(r"\b(system|assistant|user)\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*(system|assistant|user)\s*>", re.IGNORECASE),
    re.compile(r"\[\s*(system|assistant|user)\s*\]", re.IGNORECASE),
]

# 2. ignore_previous · classic jailbreak markers
_IGNORE_PREVIOUS_PATTERNS = [
    re.compile(r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|messages?)", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|prior|above|all)", re.IGNORECASE),
    re.compile(r"forget\s+(previous|prior|above|everything)", re.IGNORECASE),
    re.compile(r"olvida\s+(las\s+)?(instrucciones?|mensajes?)\s+(anteriores?|previas?)", re.IGNORECASE),
    re.compile(r"ignora\s+(las\s+)?(instrucciones?|mensajes?)\s+(anteriores?|previas?)", re.IGNORECASE),
]

# 3. system_extraction · prompt extraction tentativa
_SYSTEM_EXTRACTION_PATTERNS = [
    # Ejecutable 8 Pasada 16 (F-PASADA9-03 · CÓDIGO mal): permitir token intermedio opcional
    # ("show ME your system prompt", "tell me your instructions") entre verbo y your/the.
    re.compile(r"(show|print|repeat|reveal|tell|display)\s+(?:me\s+)?(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"what\s+(are|is)\s+(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", re.IGNORECASE),
    re.compile(r"(muestra|imprime|repite|revela|dime)\s+(tu|el|las)\s+(prompt|instrucci[oó]n|mensaje\s+sistema)", re.IGNORECASE),
]

# 4. delimiter_injection · XML/markdown tags tentativa override
_DELIMITER_INJECTION_PATTERNS = [
    re.compile(r"</?\s*(system|instructions?|prompt|context)\s*>", re.IGNORECASE),
    re.compile(r"```\s*(system|prompt|instructions?)\s*\n", re.IGNORECASE),
    re.compile(r"---+\s*(end|begin|new)\s+(of\s+)?(system|prompt|instructions?)", re.IGNORECASE),
]

# 5. base64_obfuscation · base64-encoded suspicious payloads
# Detect long base64 strings (>40 chars) embedded in input
_BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

# Min length for "excessive_length" violation
_MAX_INPUT_LENGTH = 10_000


# ════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════


def sanitize_user_input(
    user_input: str,
    *,
    max_length: int = _MAX_INPUT_LENGTH,
    context_keywords: list[str] | None = None,
) -> SanitizationResult:
    """Sanitize user-facing input pre-LLM call · detect PI violations.

    Args:
        user_input: Raw user input string (cliente/auditor portal).
        max_length: Cap on input length (default 10_000 chars).
        context_keywords: Optional list of legitimate project context keywords
            (project name, cliente name, etc) · used to dampen
            context_bleed false positives.

    Returns:
        SanitizationResult with sanitized_input + violations + should_block.
        should_block=True si CUALQUIER critical violation detected.

    Determinism: dado mismo input → mismo output (regex-based).

    Pattern Sub-atom 5.A 3-way OR compatibility: violations list ready
    para audit_log emit con project_id + client_id propagation cross.
    """
    violations: list[Violation] = []
    sanitized = user_input
    original_length = len(user_input)

    # 8. excessive_length · check first · truncate if needed
    if original_length > max_length:
        violations.append(Violation(
            category="excessive_length",
            pattern_excerpt=f"Length {original_length} > cap {max_length}",
            severity="warning",
        ))
        sanitized = sanitized[:max_length]

    # 1. role_manipulation
    for pattern in _ROLE_MANIPULATION_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            violations.append(Violation(
                category="role_manipulation",
                pattern_excerpt=match.group(0)[:80],
                severity="critical",
            ))
            sanitized = pattern.sub("[blocked-role-marker]", sanitized)

    # 2. ignore_previous
    for pattern in _IGNORE_PREVIOUS_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            violations.append(Violation(
                category="ignore_previous",
                pattern_excerpt=match.group(0)[:80],
                severity="critical",
            ))
            sanitized = pattern.sub("[blocked-jailbreak]", sanitized)

    # 3. system_extraction
    for pattern in _SYSTEM_EXTRACTION_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            violations.append(Violation(
                category="system_extraction",
                pattern_excerpt=match.group(0)[:80],
                severity="critical",
            ))
            sanitized = pattern.sub("[blocked-extraction]", sanitized)

    # 4. delimiter_injection
    for pattern in _DELIMITER_INJECTION_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            violations.append(Violation(
                category="delimiter_injection",
                pattern_excerpt=match.group(0)[:80],
                severity="critical",
            ))
            sanitized = pattern.sub("[blocked-delimiter]", sanitized)

    # 5. base64_obfuscation · only if matches >=2 base64 chunks AND decodes
    # to plausible text (avoid false positives on legit hashes/IDs).
    base64_matches = _BASE64_PATTERN.findall(sanitized)
    suspicious_base64 = [
        m for m in base64_matches
        if _looks_like_decoded_text(m)
    ]
    if len(suspicious_base64) >= 1:
        violations.append(Violation(
            category="base64_obfuscation",
            pattern_excerpt=f"{len(suspicious_base64)} chunks (first: {suspicious_base64[0][:40]})",
            severity="warning",
        ))
        # No auto-sanitize · legitimate IDs/hashes could match · flag-only

    # 6. context_bleed · optional · only if context_keywords provided
    # Look for "client X" / "cliente Y" patterns NOT in context_keywords
    if context_keywords:
        # Ejecutable 8 Pasada 16 (F-PASADA9-03 · CÓDIGO mal): \b evita falso positivo cuando
        # "client" aparece DENTRO de otra palabra ("MyClient progress" matcheaba "Client progress"
        # y marcaba "progress" como cliente externo). Con \b solo matchea "client X" standalone.
        bleed_pattern = re.compile(
            r"\b(?:cliente|client|proyecto|project)\s+(\w+)", re.IGNORECASE
        )
        for match in bleed_pattern.finditer(sanitized):
            mentioned = match.group(1).lower()
            if not any(mentioned in kw.lower() for kw in context_keywords):
                violations.append(Violation(
                    category="context_bleed",
                    pattern_excerpt=match.group(0)[:80],
                    severity="info",
                ))
                # NO auto-sanitize · cliente may legitimately reference
                # external entity · flag-only audit_log

    # 7. multilingual_evasion · español/inglés mixto con jailbreak markers
    # (cubierto via _IGNORE_PREVIOUS_PATTERNS español + inglés ya)
    # Additional check: presence of both languages WITH jailbreak intent
    # NO additional pattern needed · existing patterns cover both langs

    # Decide block: critical violations = block
    critical_count = sum(1 for v in violations if v.severity == "critical")
    should_block = critical_count > 0

    return SanitizationResult(
        sanitized_input=sanitized,
        violations=violations,
        should_block=should_block,
        original_length=original_length,
        sanitized_length=len(sanitized),
    )


def _looks_like_decoded_text(b64_chunk: str) -> bool:
    """Heuristic: base64 decodes to printable text (likely payload).

    NO consideration of hashes/IDs · those decode to binary garbage usually.
    """
    try:
        # Pad if needed
        padding = 4 - (len(b64_chunk) % 4)
        if padding != 4:
            b64_chunk = b64_chunk + ("=" * padding)
        decoded = base64.b64decode(b64_chunk, validate=False)
        # Check >70% printable ASCII = likely text payload
        try:
            text = decoded.decode("utf-8", errors="strict")
            printable_ratio = sum(
                1 for c in text if c.isprintable() or c.isspace()
            ) / max(len(text), 1)
            return printable_ratio > 0.7 and len(text) > 10
        except UnicodeDecodeError:
            return False
    except (ValueError, base64.binascii.Error):
        return False


def format_violations_for_audit_log(
    violations: list[Violation],
) -> dict[str, list[str]]:
    """Format violations grouped by category · audit_log payload friendly.

    Returns dict mapping category → list of pattern_excerpt strings.
    Empty dict if no violations.
    """
    result: dict[str, list[str]] = {}
    for v in violations:
        result.setdefault(v.category, []).append(v.pattern_excerpt)
    return result
