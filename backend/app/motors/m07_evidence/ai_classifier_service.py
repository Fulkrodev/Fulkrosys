"""AI Classifier Service · CLUSTER 4 Phase 4B cliente uploads classification.

Sesión 3B-2B.8 CLUSTER 4 Phase 4B · pure functional classifier R1 deterministic.
Enhanced keyword matching + ENS measure_code mapping + tags extraction + confidence
scoring.

LLM-based augment DEFERRED Future-1.E.classifier-llm-augment (post-piloto
demand-driven · LLM cost concern + R1 trazabilidad ENAC).

Filosofía cliente-mínimo:
- Server pre-computes suggestion (cliente NO opera classifier logic)
- Cliente CONFIRMS suggestion (binary accept/reject)
- Admin VALIDATES final authoritative
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ClassificationSuggestion:
    """Canonical classifier suggestion result (deterministic R1)."""

    filename: str
    suggested_clasificacion: str
    suggested_tipo_documento: str
    suggested_measure_codes: list[str] = field(default_factory=list)
    suggested_tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    rule_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "suggested_clasificacion": self.suggested_clasificacion,
            "suggested_tipo_documento": self.suggested_tipo_documento,
            "suggested_measure_codes": list(self.suggested_measure_codes),
            "suggested_tags": list(self.suggested_tags),
            "confidence": self.confidence,
            "matched_keywords": list(self.matched_keywords),
            "rule_id": self.rule_id,
        }


# ════════════════════════════════════════════════════════════════════
# CLASSIFIER_RULES extended (reuse M24 IDMS + measure_code mapping)
# Format: (rule_id, keywords, clasificacion, tipo_documento, measure_codes, tags)
# ════════════════════════════════════════════════════════════════════

CLASSIFIER_RULES: list[tuple[str, tuple[str, ...], str, str, list[str], list[str]]] = [
    # Contracts
    (
        "rule_contrato",
        ("contrato", "propuesta", "nda", "sla"),
        "contrato", "contrato",
        ["org.4"], ["legal", "contrato"],
    ),
    # Actas
    (
        "rule_acta",
        ("acta", "categori"),
        "registro", "acta",
        ["org.4"], ["acta", "decision"],
    ),
    # MAGERIT
    (
        "rule_magerit",
        ("riesgo", "magerit", "amenaza"),
        "informe", "informe_riesgos",
        ["op.pl.1"], ["magerit", "riesgo"],
    ),
    # DdA
    (
        "rule_dda",
        ("dda", "aplicabilid"),
        "registro", "dda",
        ["org.4"], ["dda", "compliance"],
    ),
    # Plan adecuación
    (
        "rule_plan_adec",
        ("plan_adecuacion", "plan adecuac", "plan de adecuacion"),
        "informe", "plan_adecuacion",
        ["op.pl.2"], ["plan", "adecuacion"],
    ),
    # Políticas
    (
        "rule_politica",
        ("politic",),
        "politica", "politica",
        ["org.4"], ["politica"],
    ),
    # Procedimientos
    (
        "rule_procedimiento",
        ("procedimiento",),
        "procedimiento", "procedimiento",
        ["org.4"], ["procedimiento"],
    ),
    # MFA / autenticación
    (
        "rule_mfa",
        ("mfa", "multi-factor", "autenticacion", "2fa"),
        "evidencia", "log",
        ["op.acc.5", "op.acc.6"], ["mfa", "autenticacion"],
    ),
    # Antivirus
    (
        "rule_antivirus",
        ("antivirus", "clamav", "malware"),
        "evidencia", "log",
        ["mp.s.4"], ["antivirus", "malware"],
    ),
    # Backup / restore
    (
        "rule_backup",
        ("backup", "respaldo", "restore", "copia"),
        "evidencia", "registro",
        ["mp.info.6"], ["backup", "continuidad"],
    ),
    # Logs / registros
    (
        "rule_log",
        ("registro_acceso", "log", "syslog", "audit_log"),
        "registro", "log",
        ["op.mon.1", "op.acc.5"], ["log", "monitorizacion"],
    ),
    # Continuidad / DRP / BIA
    (
        "rule_continuidad",
        ("continuidad", "drp", "bia", "rto", "rpo"),
        "informe", "informe_continuidad",
        ["op.cont.2"], ["continuidad", "drp", "bia"],
    ),
    # Formación
    (
        "rule_formacion",
        ("formacion", "curso", "training", "concienciacion"),
        "registro", "formacion",
        ["mp.per.3"], ["formacion"],
    ),
    # Proveedores
    (
        "rule_proveedor",
        ("proveedor", "vendor", "subcontratista"),
        "registro", "proveedor",
        ["mp.s.7"], ["proveedor", "tercero"],
    ),
    # Pentest / auditoría
    (
        "rule_pentest",
        ("pentest", "auditoria", "informe_seguridad", "e-7"),
        "informe", "informe_pentest",
        ["op.exp.10"], ["pentest", "auditoria"],
    ),
    # Acceso / permisos
    (
        "rule_acceso",
        ("acceso", "permiso", "rol", "rbac"),
        "registro", "log",
        ["op.acc.4", "op.acc.5"], ["accesos"],
    ),
    # Configuración base / hardening
    (
        "rule_hardening",
        ("hardening", "configuracion", "cis", "benchmark"),
        "evidencia", "config",
        ["op.exp.2"], ["hardening", "configuracion"],
    ),
    # Cifrado / SSL / TLS
    (
        "rule_cifrado",
        ("cifrado", "ssl", "tls", "https"),
        "evidencia", "config",
        ["mp.com.4"], ["cifrado", "comunicaciones"],
    ),
]


def _compute_confidence(matched_kw_count: int) -> float:
    """Deterministic confidence formula (R1).

    0 matches → 0.0 (unknown)
    1 match → 0.30
    2 matches → 0.65
    3+ matches → 1.00
    """
    if matched_kw_count <= 0:
        return 0.0
    if matched_kw_count >= 3:
        return 1.0
    return 0.30 + 0.35 * (matched_kw_count - 1)


def suggest_classification(
    filename: str,
    content_preview: Optional[str] = None,
    project_categoria: Optional[str] = None,
) -> ClassificationSuggestion:
    """Pure functional classifier · R1 deterministic.

    Args:
      filename: cliente file name (cross-matched lowercase)
      content_preview: optional first ~1000 chars (mejora rule match)
      project_categoria: BASICA/MEDIA/ALTA (context awareness · NO scoring)

    Returns ClassificationSuggestion · siempre returns objeto (NO None).
    Cuando NO rule match · confidence=0.0 + fallback "otro" clasificacion
    + filename como tag.
    """
    if not filename or not filename.strip():
        return ClassificationSuggestion(
            filename="",
            suggested_clasificacion="otro",
            suggested_tipo_documento="otro",
            confidence=0.0,
        )

    haystack_parts = [filename.lower()]
    if content_preview:
        haystack_parts.append(content_preview.lower())
    haystack = " ".join(haystack_parts)

    best_rule: Optional[tuple] = None
    best_matched_count = 0
    best_matched_keywords: list[str] = []

    for rule in CLASSIFIER_RULES:
        rule_id, keywords, _, _, _, _ = rule
        matched = [kw for kw in keywords if kw in haystack]
        if matched and len(matched) > best_matched_count:
            best_rule = rule
            best_matched_count = len(matched)
            best_matched_keywords = matched

    if best_rule is None:
        # Fallback · no rule matched
        return ClassificationSuggestion(
            filename=filename,
            suggested_clasificacion="otro",
            suggested_tipo_documento="otro",
            suggested_measure_codes=[],
            suggested_tags=[],
            confidence=0.0,
            matched_keywords=[],
            rule_id=None,
        )

    rule_id, _, clasificacion, tipo, measure_codes, tags = best_rule
    confidence = _compute_confidence(best_matched_count)

    return ClassificationSuggestion(
        filename=filename,
        suggested_clasificacion=clasificacion,
        suggested_tipo_documento=tipo,
        suggested_measure_codes=list(measure_codes),
        suggested_tags=list(tags),
        confidence=confidence,
        matched_keywords=best_matched_keywords,
        rule_id=rule_id,
    )
